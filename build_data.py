"""
build_data.py  -  prepara i dati per il sito NBA Shot Chart

Parte dal dataset pubblico su GitHub (shufinskiy/nba_data) e produce:

  data/meta.json                     informazioni generali (stagioni, griglia...)
  data/players.json                  elenco giocatori con stagioni e squadra
  data/teams.json                    elenco squadre (id, nome, sigla)
  data/league.json                   medie di lega per zona e per cella del campo
  data/shots/<stagione>/<id>.json    i tiri di un giocatore in una stagione

Uso:   python3 build_data.py

La prima volta scarica i file (qualche MB a stagione) e li tiene in cache/,
così le volte successive è molto più veloce.
"""

import datetime
import io
import json
import re
import sys
import tarfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# --- Impostazioni (modificale a piacere) --------------------------------------
PRIMA_STAGIONE = 2016    # anno d'inizio: 2016 = stagione 2016-17
ULTIMA_STAGIONE = 2025   # 2025 = stagione 2025-26
MIN_FGA = 50             # giocatori con meno tiri in una stagione vengono scartati
CELLA = 10               # lato delle celle della griglia di lega (in decimi di piede)

LISTA = "https://raw.githubusercontent.com/shufinskiy/nba_data/main/list_data.txt"
OUT = Path("data")
CACHE = Path("cache")

# Griglia del mezzo campo: x da -250 a 250, y da -50 a 420
X_MIN, Y_MIN = -250, -50
COLONNE, RIGHE = 50, 47

CAMPI = ["x", "y", "made", "dist", "period", "type", "date",
         "opp", "action", "zone", "po"]


# --- Funzioni di supporto -----------------------------------------------------
def nome_stagione(anno):
    """2025 -> '2025-26'"""
    return f"{anno}-{str(anno + 1)[-2:]}"


def carica_lista():
    """Scarica l'elenco dei dataset disponibili: nome -> indirizzo."""
    r = requests.get(LISTA, timeout=30)
    r.raise_for_status()
    voci = {}
    for riga in r.text.strip().splitlines():
        if "=" in riga:
            nome, url = riga.split("=", 1)
            voci[nome.strip()] = url.strip()
    return voci


def carica_squadre():
    """Elenco squadre dalla libreria nba_api (funziona anche offline)."""
    from nba_api.stats.static import teams
    return teams.get_teams()


def scarica_tabella(nome, voci):
    """Scarica (o legge dalla cache) un dataset e lo restituisce come tabella."""
    if nome not in voci:
        return None

    file_cache = CACHE / f"{nome}.tar.xz"
    if file_cache.exists():
        contenuto = file_cache.read_bytes()
    else:
        print(f"    scarico {nome}...")
        for tentativo in range(3):
            try:
                r = requests.get(voci[nome], timeout=180)
                r.raise_for_status()
                contenuto = r.content
                break
            except Exception as e:
                print(f"    tentativo {tentativo + 1} fallito: {e}")
                time.sleep(3)
        else:
            return None
        file_cache.write_bytes(contenuto)

    with tarfile.open(fileobj=io.BytesIO(contenuto), mode="r:*") as tar:
        membro = [m for m in tar.getmembers() if m.name.endswith(".csv")][0]
        return pd.read_csv(tar.extractfile(membro))


def scrivi_json(percorso, dati):
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, separators=(",", ":"), ensure_ascii=False),
                        encoding="utf-8")


# --- Elaborazione di una stagione --------------------------------------------
def prepara_tabella(df):
    """Aggiunge le colonne calcolate che ci servono."""
    df = df.copy()
    df["ZONE"] = df["SHOT_ZONE_BASIC"].astype(str) + "|" + df["SHOT_ZONE_AREA"].astype(str)
    df["TYPE"] = np.where(df["SHOT_TYPE"].astype(str).str.startswith("3"), 3, 2)
    return df.sort_values(
        ["GAME_DATE", "GAME_ID", "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING"],
        ascending=[True, True, True, False, False],
    )


def medie_lega(df):
    """Tiri e canestri della lega per zona e per cella (solo regular season)."""
    lega = df[df["PO"] == 0]

    zone = {}
    for zona, g in lega.groupby("ZONE"):
        zone[zona] = [int(len(g)), int(g["SHOT_MADE_FLAG"].sum())]

    cx = ((lega["LOC_X"] - X_MIN) // CELLA).astype(int)
    cy = ((lega["LOC_Y"] - Y_MIN) // CELLA).astype(int)
    valide = (cx >= 0) & (cx < COLONNE) & (cy >= 0) & (cy < RIGHE)
    celle = pd.DataFrame({"cx": cx[valide], "cy": cy[valide],
                          "made": lega.loc[valide, "SHOT_MADE_FLAG"]})
    griglia = {}
    for (gx, gy), g in celle.groupby(["cx", "cy"]):
        griglia[f"{gx},{gy}"] = [int(len(g)), int(g["made"].sum())]

    return {"zones": zone, "grid": griglia}


def scrivi_giocatori(df, stagione, abbr_per_id, giocatori):
    """Scrive un file JSON per ogni giocatore della stagione. Ritorna quanti ne ha scritti."""
    # Avversario: se la squadra del giocatore è la squadra di casa, l'avversario è la ospite
    abbr = df["TEAM_ID"].map(abbr_per_id)
    df = df.assign(OPP=df["VTM"].where(abbr == df["HTM"], df["HTM"]))

    scritti = 0
    for pid, g in df.groupby("PLAYER_ID"):
        if len(g) < MIN_FGA:
            continue

        nome = str(g["PLAYER_NAME"].iloc[-1])
        squadra_principale = int(g["TEAM_ID"].value_counts().idxmax())

        # Liste di lookup: nei tiri salviamo solo l'indice, così il file pesa meno
        opp = sorted(g["OPP"].astype(str).unique())
        azioni = sorted(g["ACTION_TYPE"].astype(str).unique())
        zone = sorted(g["ZONE"].unique())
        i_opp = {v: i for i, v in enumerate(opp)}
        i_azi = {v: i for i, v in enumerate(azioni)}
        i_zon = {v: i for i, v in enumerate(zone)}

        tiri = [
            [int(x), int(y), int(m), int(d), int(p), int(t), int(dt),
             i_opp[str(o)], i_azi[str(a)], i_zon[z], int(po)]
            for x, y, m, d, p, t, dt, o, a, z, po in zip(
                g["LOC_X"], g["LOC_Y"], g["SHOT_MADE_FLAG"], g["SHOT_DISTANCE"],
                g["PERIOD"], g["TYPE"], g["GAME_DATE"], g["OPP"],
                g["ACTION_TYPE"], g["ZONE"], g["PO"],
            )
        ]

        scrivi_json(OUT / "shots" / stagione / f"{int(pid)}.json", {
            "player": {"id": int(pid), "name": nome},
            "season": stagione,
            "fields": CAMPI,
            "lookups": {"opp": opp, "action": azioni, "zone": zone},
            "shots": tiri,
        })

        scheda = giocatori.setdefault(int(pid), {"id": int(pid), "name": nome, "s": {}})
        scheda["name"] = nome  # le stagioni arrivano in ordine: resta il nome più recente
        scheda["s"][stagione] = {
            "fga": int(len(g)),
            "fgm": int(g["SHOT_MADE_FLAG"].sum()),
            "tid": squadra_principale,
        }
        scritti += 1
    return scritti


# --- Programma principale -----------------------------------------------------
def main():
    print("Scarico l'elenco dei dataset...")
    voci = carica_lista()

    squadre = carica_squadre()
    abbr_per_id = {t["id"]: t["abbreviation"] for t in squadre}

    OUT.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)

    giocatori = {}
    lega = {}
    stagioni_fatte = []

    for anno in range(PRIMA_STAGIONE, ULTIMA_STAGIONE + 1):
        stagione = nome_stagione(anno)
        print(f"\nStagione {stagione}")

        reg = scarica_tabella(f"shotdetail_{anno}", voci)
        if reg is None:
            print("    regular season non disponibile, salto la stagione")
            continue
        reg["PO"] = 0

        po = scarica_tabella(f"shotdetail_po_{anno}", voci)
        if po is not None:
            po["PO"] = 1
            df = pd.concat([reg, po], ignore_index=True)
        else:
            df = reg

        df = prepara_tabella(df)
        lega[stagione] = medie_lega(df)
        n = scrivi_giocatori(df, stagione, abbr_per_id, giocatori)
        stagioni_fatte.append(stagione)
        print(f"    {len(df)} tiri totali, {n} giocatori salvati")

    if not stagioni_fatte:
        sys.exit("Nessuna stagione elaborata. Incollami l'output qui sopra.")

    # Indici
    elenco = sorted(giocatori.values(), key=lambda p: p["name"])
    scrivi_json(OUT / "players.json", elenco)
    scrivi_json(OUT / "teams.json", [
        {"id": t["id"], "name": t["full_name"], "abbr": t["abbreviation"]} for t in squadre
    ])
    scrivi_json(OUT / "league.json", {
        "cell": CELLA, "xmin": X_MIN, "ymin": Y_MIN, "cols": COLONNE, "rows": RIGHE,
        "seasons": lega,
    })
    scrivi_json(OUT / "meta.json", {
        "seasons": stagioni_fatte,
        "generated": datetime.date.today().isoformat(),
        "min_fga": MIN_FGA,
        "shot_fields": CAMPI,
        "source": "github.com/shufinskiy/nba_data",
    })

    # Riepilogo
    file_tiri = list((OUT / "shots").rglob("*.json"))
    peso = sum(f.stat().st_size for f in OUT.rglob("*.json")) / 1024 / 1024
    print(f"\nFatto! {len(elenco)} giocatori, {len(file_tiri)} file di tiri, "
          f"{peso:.1f} MB in totale nella cartella data/")


if __name__ == "__main__":
    main()
