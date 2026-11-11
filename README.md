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
- **Filtro per avversario** e **commenti automatici** sotto la mappa (zona più forte, zona più debole, quota di tiri da 3).
- **Come tira**: barre per tipo di tiro (schiacciate, entrate e appoggi, jump shot, step-back, floater…) con quota sul totale e percentuale di realizzazione.
- **Andamento nella stagione**: percentuale dal campo sulle ultime 10 partite, con la media della stagione, il periodo migliore e quello più freddo.
- **Replay della stagione**: un cursore (o il tasto play) fa avanzare la stagione partita dopo partita; mappa, statistiche e grafici crescono con i tiri.
- **Dettaglio del tiro**: nella vista Punti, toccando o passando vicino a un tiro compare un cartellino con data, avversario, quarto, tipo di tiro, distanza ed esito.
- **Condividi**: link che riapre la stessa vista (giocatore, stagione, filtri) e immagine della mappa da scaricare o condividere.
- **Tema chiaro e scuro**.
- **Responsive**: pensata per desktop e mobile.

## Come leggere i grafici

- **eFG%** (percentuale effettiva dal campo) = (canestri segnati + 0,5 × canestri da 3 segnati) / tiri tentati.
- Nelle heatmap e nelle zone il colore confronta il giocatore con la **media NBA di regular season** della stessa stagione nella stessa area del campo. Per non esagerare quando i tiri sono pochi, la percentuale di ogni esagono viene avvicinata alla media della lega (più tiri ci sono, meno l'aggiustamento conta).
- Nella mappa delle differenze compaiono solo gli esagoni in cui entrambi i giocatori hanno tirato almeno 3 volte.

## Fonti dei dati e crediti

- **Dati dei tiri**: statistiche ufficiali della NBA (NBA Stats), scaricate con la libreria [nba_api](https://github.com/swar/nba_api).
- **Origine dei dati**: statistiche di NBA.com ([stats.nba.com](https://www.nba.com/stats)). Tutti i diritti sui dati appartengono alla NBA.
- **Foto dei giocatori e loghi delle squadre**: non sono contenuti in questo repository, vengono caricati al momento dal server della NBA (`cdn.nba.com`). Appartengono alla NBA, alle squadre e ai rispettivi titolari.
- **Libreria [nba_api](https://github.com/swar/nba_api)** di Swar Patel: usata dallo script di preparazione per leggere l'API della NBA.
- **Font**: [Barlow e Barlow Condensed](https://fonts.google.com/specimen/Barlow) di Jeremy Tribby, tramite Google Fonts (licenza SIL Open Font License).

> Shot Lab è un progetto personale, senza scopo di lucro. Non è affiliato, sponsorizzato né approvato dalla NBA o dalle sue squadre. Nomi, loghi e immagini sono marchi dei rispettivi proprietari.

## Come funziona

```
nba-shot-lab/
├── index.html            il sito (HTML, CSS e JavaScript in un solo file)
├── manifest.webmanifest  per aggiungerlo alla schermata Home
├── icons/                icone dell'app
├── scripts/
│   └── build_database.py script che scarica e prepara i dati
└── data/                 file JSON generati dallo script
    ├── meta.json             informazioni generali
    ├── players.json          elenco giocatori, stagioni e squadre
    ├── teams.json            elenco squadre
    ├── league.json           medie di lega per zona e per cella del campo
    └── players/<id>.json     tutti i tiri di un giocatore, stagione per stagione
```

`scripts/build_database.py` legge l'API NBA a finestre di date, tiene i dati grezzi in `cache/` (che non va caricata su GitHub) e scrive un file JSON per ogni giocatore. Ogni tiro è una lista compatta di numeri (posizione, esito, distanza, quarto, tipo, data, avversario, tipo di azione, zona, playoff, stagione). Il sito carica solo il file del giocatore scelto, quindi resta veloce anche da telefono.

## Provarlo in locale

I browser bloccano la lettura dei JSON se la pagina si apre con un doppio clic, serve un piccolo server locale. Nella cartella del progetto:

```bash
python3 -m http.server
```

Poi apri http://localhost:8000.

## Aggiornare i dati

Servono Python 3 e alcune librerie: `pip install nba_api pandas numpy`.

- **Prima volta** (tutte le stagioni, dal 1996-97): lancia `scripts/build_database.py`. Ci vuole del tempo, ma si può interrompere e rilanciare: riparte da dove era arrivato.
- **Aggiornamenti**: rilancia lo script. Le stagioni concluse non vengono riscaricate, per quella in corso vengono riprese le ultime tre settimane. Per una sola stagione: `build_database.py 2026` (2026 = 2026-27).

Poi basta fare commit e push della cartella `data/`. Le partite di play-in non sono incluse.
