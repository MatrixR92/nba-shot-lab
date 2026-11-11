"""
build_database.py  -  costruisce e aggiorna i dati del sito leggendo l'API NBA (nba_api)

Posizione: dentro il repository, nella cartella scripts/. Trova da solo la cartella
principale del progetto (quella sopra scripts/), quindi funziona da Thonny
qualunque sia la cartella di lavoro.

Uso (da Thonny, tasto Run):
    build_database.py          ->  tutte le stagioni, da 1996-97 a oggi
    build_database.py 2026     ->  aggiorna una sola stagione (2026 = 2026-27)

La prima volta ci vuole tempo, ma si può interrompere (anche chiudendo Thonny)
e rilanciare: riparte da dove era arrivato. Le stagioni concluse, una volta
scaricate, non vengono più richieste. Per quella in corso vengono riscaricate
le ultime tre settimane, così le partite nuove entrano da sole.

Cosa produce (nella cartella data/ del progetto):
    players/<id>.json   tutti i tiri di un giocatore, stagione per stagione
    players.json        elenco giocatori (per la ricerca) con le stagioni giocate
    teams.json          elenco squadre
    teams/<id>.json     attacco, difesa, playoff, record e leader di ogni squadra
    team_summary.json   totali di ogni squadra (per piazzamenti e grafici)
    league.json         medie di lega per zona e per cella del campo
    meta.json           informazioni generali
La cartella cache/ contiene i dati grezzi scaricati: serve solo a te e non va
caricata su GitHub.
"""

import datetime
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from nba_api.stats.endpoints import shotchartdetail
from nba_api.stats.static import teams

# --- Impostazioni ---------------------------------------------------------------
PRIMA_STAGIONE = 1996        # 1996 = stagione 1996-97, la più vecchia disponibile
MIN_FGA = 50                 # giocatori con meno tiri in carriera vengono esclusi
GIORNI_RIFRESCO = 20         # le finestre più recenti di così vengono sempre riscaricate
PAUSA = 1.0                  # secondi di pausa tra una richiesta e l'altra

CELLA, X_MIN, Y_MIN, COLS, RIGHE = 10, -250, -50, 50, 47
CAMPI = ["x", "y", "made", "dist", "period", "type", "date",
         "opp", "action", "zone", "po", "se"]
COLONNE_API = ["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "PERIOD",
               "MINUTES_REMAINING", "SECONDS_REMAINING", "ACTION_TYPE", "SHOT_TYPE",
               "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_DISTANCE", "LOC_X", "LOC_Y",
               "SHOT_MADE_FLAG", "GAME_DATE", "HTM", "VTM"]

FAMIGLIE = ["Restricted Area", "In The Paint (Non-RA)", "Mid-Range", "Corner 3", "Above the Break 3"]
MIN_TIRI_LEADER = 10         # nella lista dei leader di squadra entra chi ha tirato almeno così

ROOT = Path(__file__).resolve().parent.parent   # cartella principale del progetto
DATA = ROOT / "data"
CACHE = ROOT / "cache"


# --- Utilità ---------------------------------------------------------------------
def nome_stagione(anno):
    return f"{anno}-{str(anno + 1)[-2:]}"


def anno_corrente(oggi):
    """La stagione inizia a ottobre: da settembre in poi vale l'anno in corso."""
    return oggi.year if oggi.month >= 9 else oggi.year - 1


def scrivi_json(percorso, dati):
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, separators=(",", ":"), ensure_ascii=False),
                        encoding="utf-8")


def stagione_completa(season):
    """Pronta solo se esistono .npz e .json e il .json è della versione con playoff e leader di squadra."""
    base = CACHE / "stagioni"
    js = base / f"{season}.json"
    if not ((base / f"{season}.npz").exists() and js.exists()):
        return False
    try:
        return json.loads(js.read_text(encoding="utf-8")).get("v") == 3
    except Exception:
        return False


def finestre(anno, oggi):
    """Mesi da ottobre dell'anno d'inizio a ottobre dell'anno dopo (copre anche la
    'bolla' del 2020 e la stagione 2020-21, che uscirono dal calendario normale)."""
    out = []
    y, m = anno, 10
    for _ in range(13):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        if datetime.date(y, m, 1) <= oggi:
            out.append((datetime.date(y, m, 1), datetime.date(ny, nm, 1) - datetime.timedelta(days=1)))
        y, m = ny, nm
    return out


def serve(tipo, ini, anno):
    """Solo le finestre in cui si gioca davvero: la regular season va da ottobre a
    maggio, i playoff da aprile a settembre. Eccezione: la 'bolla' del 2019-20
    (regular season fino ad agosto 2020, playoff fino a ottobre 2020)."""
    y, m = ini.year, ini.month
    if tipo == "Playoffs":
        return (y == anno + 1 and 4 <= m <= 9) or (anno == 2019 and y == 2020 and m == 10)
    return (y == anno and m >= 10) or (y == anno + 1 and m <= 5) or (anno == 2019 and y == 2020 and m in (7, 8))


def percorsi(season, tipo, ini):
    base = CACHE / "api" / season / f"{'po' if tipo == 'Playoffs' else 'rs'}_{ini:%Y-%m}"
    return base.with_suffix(".csv.gz"), base.with_suffix(".vuoto")


def fresca(fin, oggi):
    return fin >= oggi - datetime.timedelta(days=GIORNI_RIFRESCO)


def scarica_api(season, tipo, ini, fin):
    """Chiede all'API i tiri di TUTTA la lega tra due date (3 tentativi)."""
    for tentativo in range(3):
        try:
            r = shotchartdetail.ShotChartDetail(
                team_id=0, player_id=0, season_nullable=season,
                season_type_all_star=tipo, context_measure_simple="FGA",
                date_from_nullable=ini.strftime("%m/%d/%Y"),
                date_to_nullable=fin.strftime("%m/%d/%Y"), timeout=120)
            return r.get_data_frames()[0]
        except Exception as e:
            print(f"    tentativo {tentativo + 1} fallito: {type(e).__name__}: {str(e)[:100]}")
            time.sleep(5)
    return None


def dati_finestra(season, tipo, ini, fin, oggi):
    """Legge una finestra dalla cache o la scarica. Ritorna (tabella o None, scaricata)."""
    csv, vuoto = percorsi(season, tipo, ini)
    if not fresca(fin, oggi):
        if csv.exists():
            return pd.read_csv(csv, dtype={"GAME_ID": str}), False
        if vuoto.exists():
            return None, False
    df = scarica_api(season, tipo, ini, fin)
    if df is None:
        sys.exit("\nDownload fallito. Il lavoro fatto finora è salvato: rilancia lo script "
                 "per riprendere. Se l'errore si ripete, incollami l'output.")
    csv.parent.mkdir(parents=True, exist_ok=True)
    if len(df):
        df[COLONNE_API].to_csv(csv, index=False)
        vuoto.unlink(missing_ok=True)
    else:
        vuoto.write_text("")
        csv.unlink(missing_ok=True)
    time.sleep(PAUSA)
    return (df[COLONNE_API] if len(df) else None), True


def aggrega_squadre(reg, sigla):
    """Per ogni squadra: i tiri che ha preso (attacco, 'o') e quelli che ha concesso agli
    avversari (difesa, 'd'). Solo regular season, già aggregati per cella del campo,
    così i file restano leggeri.
    Totali: [tentati, segnati, da 3 tentati, da 3 segnati, somma distanze]."""
    inv = {v: k for k, v in sigla.items()}
    r = reg.copy()
    r["DTID"] = r["OPP"].map(inv)
    r["CX"] = ((r["LOC_X"] - X_MIN) // CELLA).astype(int)
    r["CY"] = ((r["LOC_Y"] - Y_MIN) // CELLA).astype(int)
    partite = {int(t): int(n) for t, n in r.groupby("TEAM_ID")["GAME_ID"].nunique().items()}
    out = {}
    for lato, chiave in (("o", "TEAM_ID"), ("d", "DTID")):
        for tid, g in r.dropna(subset=[chiave]).groupby(chiave):
            tid = int(tid)
            t3 = g["TYPE"] == 3
            tot = [int(len(g)), int(g["SHOT_MADE_FLAG"].sum()), int(t3.sum()),
                   int(g["SHOT_MADE_FLAG"][t3].sum()), int(g["SHOT_DISTANCE"].sum())]
            dentro = g[(g["CX"] >= 0) & (g["CX"] < COLS) & (g["CY"] >= 0) & (g["CY"] < RIGHE)]
            celle = [[int(a), int(b), int(len(x)), int(x["SHOT_MADE_FLAG"].sum())]
                     for (a, b), x in dentro.groupby(["CX", "CY"])]
            zone = {k: [int(len(x)), int(x["SHOT_MADE_FLAG"].sum()), int(x["LOC_X"].sum()), int(x["LOC_Y"].sum())]
                    for k, x in g.groupby("ZONE")}
            e = out.setdefault(str(tid), {"g": partite.get(tid, 0)})
            e[lato] = {"t": tot, "cells": celle, "zones": zone}
    return out


def famiglia(zona):
    """'Left Corner 3|Left Side(L)' -> 'Corner 3'; i tiri da metà campo non contano."""
    base = str(zona).split("|")[0]
    if "Corner" in base:
        return "Corner 3"
    return base if base in FAMIGLIE else None


def famiglie(zone):
    """Somma le zone fini nelle 5 famiglie: {famiglia: [tentati, segnati]}."""
    out = {}
    for k, (n, m, *_) in zone.items():
        f = famiglia(k)
        if f:
            a = out.setdefault(f, [0, 0])
            a[0] += n
            a[1] += m
    return out


def leader_squadre(df):
    """Per ogni squadra i giocatori che hanno tirato con quella maglia (anche se poi scambiati):
    [id, tentati, segnati, da 3 tentati, da 3 segnati, poi (tentati, segnati) per ognuna
    delle 5 famiglie di zone]."""
    out = {}
    if not len(df):
        return out
    d = df.copy()
    d["FAM"] = d["ZONE"].map(famiglia)
    for (tid, pid), g in d.groupby(["TEAM_ID", "PLAYER_ID"]):
        if len(g) < MIN_TIRI_LEADER:
            continue
        t3 = g["TYPE"] == 3
        riga = [int(pid), int(len(g)), int(g["SHOT_MADE_FLAG"].sum()), int(t3.sum()),
                int(g["SHOT_MADE_FLAG"][t3].sum())]
        for f in FAMIGLIE:
            x = g[g["FAM"] == f]
            riga += [int(len(x)), int(x["SHOT_MADE_FLAG"].sum())]
        out.setdefault(str(int(tid)), []).append(riga)
    for righe in out.values():
        righe.sort(key=lambda r: -r[1])
    return out


def squadre_stagione(df, sigla):
    """Dati di squadra della stagione: regular season + playoff (chiave 'p')."""
    reg = df[df["PO"] == 0]
    po = df[df["PO"] == 1]
    out = aggrega_squadre(reg, sigla)
    for tid, righe in leader_squadre(reg).items():
        out.setdefault(tid, {"g": 0})["l"] = righe
    if len(po):
        lp = leader_squadre(po)
        for tid, e in aggrega_squadre(po, sigla).items():
            e["l"] = lp.get(tid, [])
            out.setdefault(tid, {"g": 0})["p"] = e
    return out


# --- Passo 1: una stagione alla volta -----------------------------------------------
def salva_stagione(season, pezzi, C):
    df = pd.concat(pezzi, ignore_index=True)
    df = df.drop_duplicates(["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID"])
    # Alcune righe dell'API (soprattutto nelle stagioni vecchie) hanno valori mancanti:
    # le scartiamo, dicendo quante sono, invece di far fermare lo script.
    essenziali = ["PLAYER_ID", "TEAM_ID", "PERIOD", "SHOT_DISTANCE", "LOC_X", "LOC_Y",
                  "SHOT_MADE_FLAG", "GAME_DATE"]
    for c in essenziali + ["MINUTES_REMAINING", "SECONDS_REMAINING"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[["MINUTES_REMAINING", "SECONDS_REMAINING"]] = df[["MINUTES_REMAINING", "SECONDS_REMAINING"]].fillna(0)
    mancanti = df[essenziali].isna().sum()
    if mancanti.sum():
        prima = len(df)
        df = df.dropna(subset=essenziali)
        dettaglio = ", ".join(f"{c}={int(n)}" for c, n in mancanti.items() if n)
        print(f"  scartate {prima - len(df)} righe su {prima} con valori mancanti ({dettaglio})")
    df["GAME_DATE"] = df["GAME_DATE"].astype(int)
    df = df.sort_values(["GAME_DATE", "GAME_ID", "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING"],
                        ascending=[True, True, True, False, False])
    # Sigla di ogni squadra in quella stagione: è la sigla presente in tutte le sue
    # partite (gli avversari cambiano, lei no). Funziona anche con i nomi storici.
    sigla = {t: pd.concat([g["HTM"], g["VTM"]]).value_counts().index[0]
             for t, g in df.groupby("TEAM_ID")}
    df["OPP"] = df["VTM"].where(df["TEAM_ID"].map(sigla) == df["HTM"], df["HTM"])
    df["ZONE"] = df["SHOT_ZONE_BASIC"].astype(str) + "|" + df["SHOT_ZONE_AREA"].astype(str)
    df["TYPE"] = np.where(df["SHOT_TYPE"].astype(str).str.startswith("3"), 3, 2)

    def cod(serie, nome):
        d = C[nome]
        return serie.astype(str).map(lambda v: d.setdefault(v, len(d))).to_numpy()

    arr = {"pid": df["PLAYER_ID"], "tid": df["TEAM_ID"], "x": df["LOC_X"], "y": df["LOC_Y"],
           "made": df["SHOT_MADE_FLAG"], "dist": df["SHOT_DISTANCE"], "period": df["PERIOD"],
           "type": df["TYPE"], "date": df["GAME_DATE"], "opp": cod(df["OPP"], "opp"),
           "action": cod(df["ACTION_TYPE"], "action"), "zone": cod(df["ZONE"], "zone"),
           "po": df["PO"]}
    cartella = CACHE / "stagioni"
    cartella.mkdir(parents=True, exist_ok=True)
    g = df.groupby("PLAYER_ID")
    stats = {int(p): [int(len(x)), int(x["SHOT_MADE_FLAG"].sum()), int(x["TEAM_ID"].value_counts().index[0])]
             for p, x in g}
    nomi = {int(p): str(x["PLAYER_NAME"].iloc[-1]) for p, x in g}

    reg = df[df["PO"] == 0]
    zone = {k: [int(len(x)), int(x["SHOT_MADE_FLAG"].sum())] for k, x in reg.groupby("ZONE")}
    cx = ((reg["LOC_X"] - X_MIN) // CELLA).astype(int)
    cy = ((reg["LOC_Y"] - Y_MIN) // CELLA).astype(int)
    ok = (cx >= 0) & (cx < COLS) & (cy >= 0) & (cy < RIGHE)
    celle = pd.DataFrame({"cx": cx[ok], "cy": cy[ok], "m": reg.loc[ok, "SHOT_MADE_FLAG"]})
    griglia = {f"{a},{b}": [int(len(x)), int(x["m"].sum())] for (a, b), x in celle.groupby(["cx", "cy"])}

    scrivi_json(cartella / f"{season}.json",
                {"v": 3, "stats": stats, "nomi": nomi, "lega": {"zones": zone, "grid": griglia},
                 "squadre": squadre_stagione(df, sigla)})
    np.savez_compressed(cartella / f"{season}.npz",
                        **{k: np.asarray(v).astype(np.int32) for k, v in arr.items()})

    return len(df), len(stats)


# --- Vittorie e sconfitte (una richiesta per tipo di stagione) -----------------------
def record_stagione(season, oggi):
    """Scarica il bilancio vittorie/sconfitte di ogni squadra (regular season e playoff).
    Se qualcosa va storto non ferma lo script: il sito mostra solo meno informazioni.
    Restituisce False se la richiesta è fallita."""
    f = CACHE / "record" / f"{season}.json"
    corrente = season == nome_stagione(anno_corrente(oggi))
    if f.exists() and not corrente:
        return True
    try:
        from nba_api.stats.endpoints import leaguegamelog
        out = {}
        for chiave, tipo in (("rs", "Regular Season"), ("po", "Playoffs")):
            df = leaguegamelog.LeagueGameLog(
                season=season, season_type_all_star=tipo,
                player_or_team_abbreviation="T", timeout=90).get_data_frames()[0]
            time.sleep(PAUSA)
            out[chiave] = {str(int(t)): [int((g["WL"] == "W").sum()), int((g["WL"] == "L").sum())]
                           for t, g in df.groupby("TEAM_ID")} if len(df) else {}
        if not out["rs"]:
            raise ValueError("nessuna partita di regular season")
        scrivi_json(f, out)
        return True
    except Exception as e:
        print(f"  {season}: vittorie/sconfitte non scaricate ({type(e).__name__}: {str(e)[:100]})")
        return False


# --- Passo 2: unisce tutte le stagioni in un file per giocatore --------------------
def assembla(seasons, C):
    colonne = ["pid", "tid", "x", "y", "made", "dist", "period", "type", "date", "opp", "action", "zone", "po"]
    parti = {c: [] for c in colonne}
    se, nomi, stats, lega, sq, riepilogo = [], {}, {}, {}, {}, {}
    for i, s in enumerate(seasons):
        z = np.load(CACHE / "stagioni" / f"{s}.npz")
        for c in colonne:
            parti[c].append(z[c])
        se.append(np.full(len(z["pid"]), i, dtype=np.int32))
        j = json.loads((CACHE / "stagioni" / f"{s}.json").read_text(encoding="utf-8"))
        nomi.update({int(k): v for k, v in j["nomi"].items()})
        for k, v in j["stats"].items():
            stats.setdefault(int(k), {})[s] = {"fga": v[0], "fgm": v[1], "tid": v[2]}
        lega[s] = j["lega"]
        fr = CACHE / "record" / f"{s}.json"
        rec = json.loads(fr.read_text(encoding="utf-8")) if fr.exists() else {"rs": {}, "po": {}}
        for tid, e in j.get("squadre", {}).items():
            voce = {"g": e["g"], "o": e.get("o"), "d": e.get("d"), "l": e.get("l", [])}
            if rec["rs"].get(tid):
                voce["r"] = rec["rs"][tid]
            riep = {"g": e["g"], "o": (e.get("o") or {}).get("t"), "d": (e.get("d") or {}).get("t"),
                    "z": {lato: famiglie(e[lato]["zones"]) for lato in ("o", "d") if e.get(lato)}}
            if voce.get("r"):
                riep["r"] = voce["r"]
            if e.get("p"):
                p = e["p"]
                voce["p"] = {"g": p["g"], "o": p.get("o"), "d": p.get("d"), "l": p.get("l", [])}
                rp = {"g": p["g"], "o": (p.get("o") or {}).get("t"), "d": (p.get("d") or {}).get("t"),
                      "z": {lato: famiglie(p[lato]["zones"]) for lato in ("o", "d") if p.get(lato)}}
                if rec["po"].get(tid):
                    voce["p"]["r"] = rp["r"] = rec["po"][tid]
                riep["p"] = rp
            sq.setdefault(tid, {})[s] = voce
            riepilogo.setdefault(s, {})[tid] = riep
    A = {c: np.concatenate(v) for c, v in parti.items()}
    A["se"] = np.concatenate(se)
    del parti
    ordine = np.argsort(A["pid"], kind="stable")   # stabile: l'ordine cronologico resta
    A = {c: v[ordine] for c, v in A.items()}
    pids, inizi = np.unique(A["pid"], return_index=True)
    fini = list(inizi[1:]) + [len(A["pid"])]
    inv = {n: {v: k for k, v in C[n].items()} for n in C}

    cartella = DATA / "players"
    cartella.mkdir(parents=True, exist_ok=True)
    for f in cartella.glob("*.json"):
        f.unlink()

    inclusi = []
    for p, a, b in zip(pids, inizi, fini):
        if b - a < MIN_FGA:
            continue
        sl = {c: v[a:b] for c, v in A.items()}
        so, sinv = np.unique(sl["se"], return_inverse=True)
        lk, cols = {}, {}
        for n in ("opp", "action", "zone"):
            u, ui = np.unique(sl[n], return_inverse=True)
            lk[n] = [inv[n][int(c)] for c in u]
            cols[n] = ui
        M = np.column_stack([sl["x"], sl["y"], sl["made"], sl["dist"], sl["period"], sl["type"],
                             sl["date"], cols["opp"], cols["action"], cols["zone"], sl["po"], sinv])
        scrivi_json(cartella / f"{int(p)}.json", {
            "player": {"id": int(p), "name": nomi[int(p)]},
            "fields": CAMPI,
            "seasons": [seasons[int(i)] for i in so],
            "lookups": lk,
            "shots": M.tolist()})
        inclusi.append(int(p))

    cart_sq = DATA / "teams"
    cart_sq.mkdir(parents=True, exist_ok=True)
    for f in cart_sq.glob("*.json"):
        f.unlink()
    for tid, stag in sq.items():
        scrivi_json(cart_sq / f"{tid}.json", {"team": int(tid), "cell": CELLA, "seasons": stag})
    scrivi_json(DATA / "team_summary.json", {"seasons": riepilogo})

    scrivi_json(DATA / "players.json",
                sorted(({"id": p, "name": nomi[p], "s": stats[p]} for p in inclusi), key=lambda e: e["name"]))
    scrivi_json(DATA / "league.json", {"cell": CELLA, "xmin": X_MIN, "ymin": Y_MIN,
                                       "cols": COLS, "rows": RIGHE, "seasons": lega})
    scrivi_json(DATA / "teams.json", [{"id": t["id"], "name": t["full_name"], "abbr": t["abbreviation"]}
                                      for t in teams.get_teams()])
    scrivi_json(DATA / "meta.json", {"format": 3, "seasons": seasons, "min_fga": MIN_FGA,
                                     "shot_fields": CAMPI, "generated": datetime.date.today().isoformat(),
                                     "source": "NBA Stats API via nba_api"})
    return len(inclusi)


def main():
    oggi = datetime.date.today()
    anni = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(PRIMA_STAGIONE, anno_corrente(oggi) + 1))
    print(f"Cartella del progetto: {ROOT}")
    CACHE.mkdir(exist_ok=True)

    percorso_codici = CACHE / "codici.json"
    C = json.loads(percorso_codici.read_text(encoding="utf-8")) if percorso_codici.exists() \
        else {"opp": {}, "action": {}, "zone": {}}

    for anno in anni:
        season = nome_stagione(anno)
        lavoro = [(t, i, f) for i, f in finestre(anno, oggi) for t in ("Regular Season", "Playoffs")
                  if serve(t, i, anno)]
        mancano = [x for x in lavoro
                   if fresca(x[2], oggi) or not any(p.exists() for p in percorsi(season, x[0], x[1]))]
        if not mancano and stagione_completa(season):
            print(f"{season}: già aggiornata")
            continue
        print(f"\n{season}: {len(mancano)} richieste da fare")
        pezzi = []
        for t, i, f in lavoro:
            df, nuova = dati_finestra(season, t, i, f, oggi)
            if nuova:
                print(f"  {i:%Y-%m} {t}: {0 if df is None else len(df)} tiri")
            if df is not None and len(df):
                df = df.copy()
                df["PO"] = int(t == "Playoffs")
                pezzi.append(df)
        if not pezzi:
            print("  nessun tiro per questa stagione")
            continue
        n, g = salva_stagione(season, pezzi, C)
        percorso_codici.write_text(json.dumps(C), encoding="utf-8")
        print(f"  salvata: {n} tiri, {g} giocatori")

    seasons = sorted(p.stem for p in (CACHE / "stagioni").glob("*.npz"))
    if not seasons:
        sys.exit("Nessuna stagione disponibile.")
    print("\nVittorie e sconfitte...")
    falliti = 0
    for s in seasons:
        falliti = 0 if record_stagione(s, oggi) else falliti + 1
        if falliti >= 2:
            print("  salto il resto: riprova al prossimo lancio (il resto del sito funziona lo stesso)")
            break
    print(f"\nAssemblo i file dei giocatori ({len(seasons)} stagioni)...")
    n = assembla(seasons, C)
    peso = sum(f.stat().st_size for f in DATA.rglob("*.json")) / 1024 / 1024
    print(f"\nFatto! {n} giocatori, {peso:.0f} MB in totale in {DATA}")


if __name__ == "__main__":
    main()
