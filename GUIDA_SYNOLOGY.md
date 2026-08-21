# 🚀 Guida all'Installazione su Synology NAS (e PC)

Questa guida ti spiega in modo semplice come installare e avviare **Amazon Review & Refund Routine Manager** sul tuo **NAS Synology** per averlo attivo 24 ore su 24 a costo zero, controllabile dal tuo **iPhone** e dal tuo **PC**.

---

## 📱 Come usarlo sul NAS Synology (Consigliato)

### Requisiti:
- Un NAS Synology con installata l'applicazione **Container Manager** (o **Docker** se usi una versione precedente di DSM). La trovi gratuitamente nel *Centro pacchetti* del Synology.

---

### Procedura in 3 semplici passi:

#### 1. Carica la cartella sul tuo NAS
1. Apri **File Station** sul tuo Synology DSM.
2. Crea una cartella chiamata `amazon-manager` all'interno della cartella condivisa `docker` (percorso: `docker/amazon-manager`).
3. Trascina e copia all'interno di `docker/amazon-manager` tutti i file del progetto:
   - `Dockerfile`
   - `docker-compose.yml`
   - la cartella `backend/`
   - la cartella `frontend/`

---

#### 2. Avvia da Container Manager
1. Nel DSM del Synology, apri l'app **Container Manager**.
2. Nel menu a sinistra clicca su **Progetto** (Project) e poi sul pulsante **Crea** (Create).
3. Compila la schermata in questo modo:
   - **Nome progetto**: `amazon-manager`
   - **Percorso**: Seleziona la cartella `docker/amazon-manager` che hai creato prima.
   - **Origine**: Seleziona *Usa un file docker-compose.yml esistente*.
4. Clicca su **Avanti** e poi su **Fine**.
5. Synology costruirà e avvierà il container in automatico!

---

#### 3. Apri l'app da PC e da iPhone
- **Da PC**: Apri il browser e digita l'indirizzo IP del tuo NAS con la porta `8000`:
  `http://IP-DEL-TUO-NAS:8000` (es. `http://192.168.1.100:8000`).
- **Da iPhone (Come App Nativa)**:
  1. Apri **Safari** su iPhone e collegati a `http://IP-DEL-TUO-NAS:8000`.
  2. Premi il pulsante di **Condivisione** in basso al centro (l'icona del quadrato con la freccia verso l'alto).
  3. Scorri e tocca **"Aggiungi alla schermata Home"**.
  4. Avrai l'icona dell'app sulla schermata del telefono, avviabile a schermo intero senza barre del browser!

---

## 💻 Come provarlo subito in locale sul tuo PC (Windows)

Se prima di caricarlo sul Synology vuoi provarlo e testarlo subito sul tuo PC Windows:

1. Apri una finestra di PowerShell.
2. Entra nella cartella del progetto:
   ```powershell
   cd C:\Users\garci\.gemini\antigravity\scratch\amazon_routine_manager
   ```
3. Installa le dipendenze:
   ```powershell
   pip install -r backend/requirements.txt
   ```
4. Avvia il server:
   ```powershell
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. Apri il browser su `http://localhost:8000`.

---

## 🛡️ Modalità Sandbox (Test Sicuro)

L'applicazione si avvia automaticamente con la **Modalità Sandbox attiva**:
- Puoi cliccare su **"Simula Dati"** in alto a destra per simulare l'arrivo di nuove offerte e nuovi acquisti con generazione dello screenshot.
- Puoi premere il **"Tasto di Conferma"** e vedere come vengono formattati i messaggi e archiviati i registri senza inviare nulla a contatti reali finché non sei pronto.
- Dalla rotellina delle **Impostazioni** (⚙️) puoi inserire i parametri di produzione quando deciderai di passare alla modalità reale.
