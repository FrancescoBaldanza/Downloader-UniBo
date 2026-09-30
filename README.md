# UniBo Downloader

Applicazione nativa macOS con interfaccia grafica moderna (PyQt6) per sincronizzare e organizzare automaticamente i materiali didattici dei corsi universitari da Virtuale (Moodle UniBo) sul tuo Mac.

---

## Funzionalita' Principali

- **Interfaccia Grafica Moderna**: Design pulito in perfetto stile macOS, con palette ufficiale dell'Universita' di Bologna.
- **Autenticazione Sicura**: Gestione protetta delle credenziali istituzionali (`@studio.unibo.it`) con supporto SSO Microsoft / UniBo e persistenza sessione Moodle.
- **Gestione Corsi & Cartelle**: Aggiungi insegnamenti inserendo semplicemente l'URL della pagina Virtuale o il relativo ID numerico. Scegli dove organizzare i materiali (es. `~/Desktop/UniBo`).
- **Sincronizzazione Automatica & Incrementale**: Rileva nuovi file, dispense, slide ed esercizi senza riscaricare i documenti gia' presenti.
- **Pianificatore Integrato (Scheduler)**: Imposta orari e frequenze di sincronizzazione (tutti i giorni, una sola volta o giorni selezionati) con notifiche macOS al termine.
- **Tracciamento & Statistiche**: Monitora lo stato di ogni corso, la dimensione totale dei materiali scaricati e la data dell'ultimo controllo.

---

## Installazione & Requisiti

### 1. Installazione dipendenze
Assicurati di avere Python 3.9+ e installa i pacchetti necessari:

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Avvio dell'Applicazione
Per avviare direttamente la GUI:

```bash
python3 main.py
```

---

## Creazione del Bundle macOS (`UniBo Downloader.app`)

Il progetto include uno script per compilare e generare l'applicazione nativa macOS `.app` completa di launcher Mach-O, icona ufficiale ad alta risoluzione e permessi di sistema TCC (Desktop, Documenti, Download):

```bash
python3 scripts/create_app_bundle.py
```

L'applicazione `UniBo Downloader.app` verra' generata e posizionata sia nella cartella del progetto che con collegamento sulla Scrivania.
