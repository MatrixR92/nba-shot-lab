# Shot Lab

Mappe dei tiri NBA: shot chart, heatmap esagonali e statistiche per giocatore, stagione per stagione. Web app responsive, scritta in HTML, CSS e JavaScript puro, pensata per essere pubblicata su GitHub Pages.

**Demo:** https://TUO-USERNAME.github.io/nba-shot-lab/

## Cosa fa

- **Ricerca giocatore** con suggerimenti e foto, su 10 stagioni (dal 2016-17 al 2025-26).
- **Card del giocatore** con foto, logo della squadra e numeri chiave: tiri segnati/tentati, FG%, 3P%, eFG%, distanza media e quota di tiri da 3.
- **Tre viste del campo:**
  - **Punti**: ogni tiro sul mezzo campo, segnati pieni e sbagliati a croce, con filtro segnati/sbagliati.
  - **Heatmap**: esagoni dove la dimensione indica la frequenza dei tiri e il colore la percentuale rispetto alla media NBA nella stessa zona (blu sotto la media, rosso sopra).
  - **Zone**: percentuale di realizzazione per area del campo.
- **Filtri**: stagione, regular season o playoff, tiri da 2 o da 3 punti, quarto.
- **Istogramma** dei tiri per distanza, con la percentuale di realizzazione per fascia.
- **Modalità Confronto**: due giocatori (o lo stesso giocatore in due stagioni) con heatmap affiancate, una mappa delle differenze, tabella testa a testa e confronto delle distanze di tiro.
- **Responsive**: pensata per desktop e mobile.

## Come leggere i grafici

- **eFG%** (percentuale effettiva dal campo) = (canestri segnati + 0,5 × canestri da 3 segnati) / tiri tentati.
- Nelle heatmap e nelle zone il colore confronta il giocatore con la **media NBA di regular season** della stessa stagione nella stessa area del campo. Per non esagerare quando i tiri sono pochi, la percentuale di ogni esagono viene avvicinata alla media della lega (più tiri ci sono, meno l'aggiustamento conta).
- Nella mappa delle differenze compaiono solo gli esagoni in cui entrambi i giocatori hanno tirato almeno 3 volte.

## Fonti dei dati e crediti

- **Dati dei tiri**: dataset pubblico [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) di [@shufinskiy](https://github.com/shufinskiy), che raccoglie i dati dei tiri (shot detail) dalle statistiche ufficiali della NBA. Un grande grazie all'autore per averli resi disponibili. Per le condizioni d'uso del dataset fai riferimento al suo repository.
- **Origine dei dati**: statistiche di NBA.com ([stats.nba.com](https://www.nba.com/stats)). Tutti i diritti sui dati appartengono alla NBA.
- **Foto dei giocatori e loghi delle squadre**: non sono contenuti in questo repository, vengono caricati al momento dal server della NBA (`cdn.nba.com`). Appartengono alla NBA, alle squadre e ai rispettivi titolari.
- **Libreria [nba_api](https://github.com/swar/nba_api)** di Swar Patel: usata solo dallo script di preparazione dei dati, per l'elenco delle squadre.
- **Font**: [Barlow e Barlow Condensed](https://fonts.google.com/specimen/Barlow) di Jeremy Tribby, tramite Google Fonts (licenza SIL Open Font License).

> Shot Lab è un progetto personale, senza scopo di lucro. Non è affiliato, sponsorizzato né approvato dalla NBA o dalle sue squadre. Nomi, loghi e immagini sono marchi dei rispettivi proprietari.

## Come funziona

```
nba-shot-lab/
├── index.html        ← il sito (tutto in un file: HTML, CSS e JavaScript)
├── build_data.py     ← script che prepara i dati
└── data/             ← file JSON generati dallo script
    ├── meta.json         informazioni generali
    ├── players.json      elenco giocatori, stagioni e squadre
    ├── teams.json        elenco squadre
    ├── league.json       medie di lega per zona e per cella del campo
    └── shots/<stagione>/<id giocatore>.json
```

`build_data.py` scarica i dataset delle stagioni, li elabora e scrive un piccolo file JSON per ogni giocatore e stagione. Ogni tiro è salvato come lista compatta di numeri (posizione, esito, distanza, quarto, tipo, data, avversario, tipo di azione, zona, playoff). Il sito legge solo i file che servono, quindi resta veloce anche da telefono.

## Provarlo in locale

I browser bloccano la lettura dei JSON se la pagina si apre con un doppio clic, serve un piccolo server locale. Nella cartella del progetto:

```bash
python3 -m http.server
```

Poi apri http://localhost:8000.

## Aggiornare i dati

Servono Python 3 e alcune librerie:

```bash
pip3 install requests pandas numpy nba_api
python3 build_data.py
```

In cima a `build_data.py` si possono cambiare le stagioni coperte (`PRIMA_STAGIONE`, `ULTIMA_STAGIONE`) e il numero minimo di tiri per includere un giocatore (`MIN_FGA`). I dataset scaricati finiscono nella cartella `cache/`, che non va caricata su GitHub.

La copertura dei dati dipende dal dataset di origine: le stagioni più recenti compaiono solo quando l'autore le aggiunge.
