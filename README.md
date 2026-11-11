# Shot Lab

Mappe dei tiri NBA: shot chart, heatmap esagonali e statistiche per giocatore, stagione per stagione. Web app responsive, scritta in HTML, CSS e JavaScript puro, pensata per essere pubblicata su GitHub Pages.

**Demo:** https://matrixr92.github.io/nba-shot-lab/

## Cosa fa

Il sito ha tre modalità: **Giocatore**, **Confronto** e **Squadra**. Si parte dalla ricerca e tutto si può condividere con un link.

### Giocatore
- **Ricerca** con suggerimenti e foto, stagione per stagione dal 1996-97 a oggi.
- **Card del giocatore** con foto, logo della squadra (cliccabile, apre la vista Squadra) e numeri chiave: tiri segnati/tentati, FG%, 3P%, eFG%, distanza media e quota di tiri da 3.
- **Tre viste del campo:**
  - **Punti**: ogni tiro sul mezzo campo, segnati pieni e sbagliati a croce, con filtro segnati/sbagliati. Toccando o passando vicino a un tiro compare un cartellino con data, avversario, quarto, tipo di tiro, distanza ed esito.
  - **Heatmap**: esagoni dove la dimensione indica la frequenza dei tiri e il colore la percentuale rispetto alla media NBA nella stessa zona (blu sotto la media, rosso sopra).
  - **Zone**: percentuale di realizzazione per area del campo.
- **Filtri**: stagione, regular season o playoff, tiri da 2 o da 3 punti, quarto e avversario.
- **Istogramma** dei tiri per distanza, con la percentuale di realizzazione per fascia.
- **Come tira**: barre per tipo di tiro (schiacciate, entrate e appoggi, jump shot, step-back, floater…) con quota sul totale e percentuale di realizzazione.
- **Andamento nella stagione**: percentuale dal campo sulle ultime 10 partite, con la media della stagione, il periodo migliore e quello più freddo.
- **Replay della stagione**: un cursore (o il tasto play) fa avanzare la stagione partita dopo partita; mappa, statistiche e grafici crescono con i tiri.
- **In sintesi**: commenti automatici (zona più forte, zona più debole, quota di tiri da 3).

### Confronto
Due giocatori (o lo stesso giocatore in due stagioni) con heatmap affiancate, mappa delle differenze, tabella testa a testa e confronto delle distanze di tiro.

### Squadra
Ricerca squadra, stagione e interruttore **Regular season / Playoff**.
- **Record** vittorie-sconfitte con il piazzamento in lega (regular season).
- Mappa di **attacco** (dove tira) e di **difesa** (dove concede i tiri agli avversari), in heatmap o zone.
- **Statistiche** con piazzamento nella lega: FG%, 3P%, eFG%.
- **Roster e leader**: chi ha tirato di più, il miglior tiratore da 3, il più preciso e chi tira di più da ogni zona. Conta i tiri fatti con quella maglia, anche per chi è stato scambiato. Un clic porta alla vista Giocatore.
- **In sintesi**: commenti automatici e tabella per zona (quota di tiri, percentuale, media NBA, piazzamento).
- **Negli anni**: quota di tiri da 3 ed eFG% in attacco e in difesa dal 1996-97, con la media NBA; un clic su un anno lo seleziona.

### In generale
- **Condividi**: link che riapre la stessa vista (modalità, stagione, filtri) e immagine della mappa da scaricare o condividere.
- **Tema chiaro e scuro**.
- **Responsive**, installabile sulla schermata Home come app.

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
    ├── team_summary.json     totali di attacco e difesa di ogni squadra (per i piazzamenti)
    ├── teams/<id>.json       attacco, difesa, playoff, record e leader di una squadra, stagione per stagione
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

Poi basta fare commit e push della cartella `data/`. Le partite di play-in non sono incluse. Il bilancio vittorie-sconfitte viene da una richiesta in più per stagione (`cache/record/`): se fallisce, lo script lo dice e il resto del sito funziona lo stesso.
