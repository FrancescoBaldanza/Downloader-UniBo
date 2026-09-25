# Downloader-UniBo (`dlub`)

Sei uno studente dell'Università di Bologna e vuoi sincronizzare una cartella della sul tuo pc con quella dei tuoi corsi su Virtuale?
Puoi usare Downloader-UniBo per farlo in modo sicuro: i file scaricati non sono mai corrotti e **le le tue credenziali istituzionali non sono visibili a nessuno**.

Inserisci le tue credenziali, definisci la cartella dove salvare le cartelle dei corsi, definisci i corsi e inifine sincronizza la cartella.

---

## Installazione

Per installarlo:
```bash
pip install -e .
```

Per verificare sia installato:
```bash
which dlub
```

---

## Istruzioni

Apri il terminale e digita:

### 1. Inizializzazione Credenziali
```bash
dlub -init "tua.mail@studio.unibo.it" "tua_password"
```

### 2. Impostazione Cartella di Destinazione

```bash
dlub -dir "~/Desktop/UniBo" # A tua scelta
```

### 3. Definizione Corsi
Definisce un corso associando il suo nome e il link o ID di Virtuale (estrae e valida automaticamente l'ID numerico variabile):
```bash
dlub -def "Nome a scelta per corso" "Link pagina virtuale"

# (Oppure solo l'ID numerico)
dlub -def "Nome a scelta per corso" <ID>
```



### 4. Pianificazione Automatica

Per esempio se volessi pianificare di scaricare il materiale relativo a `Fisica` per le `08:00` scrivi:
```bash
dlub -schedule "Fisica" "08:00"
```

## Comandi Extra

### 4. Download diretto

```bash
# Tramite Nome associato
dlub -get "Fisica Generale"

# Tramite ID
dlub -get 80238

# Tramite URL diretto
dlub -get "https://virtuale.unibo.it/course/view.php?id=80238"

# Tutti i corsi registrati
dlub -get all
```

### 6. Visualizza Lista Corsi 
```bash
dlub -list
```

### 7. Diagnostica
```bash
dlub -doctor
```

