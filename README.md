# FanSale Ticket Bot

Bot Python che monitora in tempo reale i biglietti disponibili su FanSale, filtrando per quantità e disponibilità effettiva. Aggira la protezione Akamai aprendo un'istanza Chrome non rilevabile e interrogando l'endpoint JSON tramite `fetch()` nel browser.

## Requisiti

- Python 3.7+
- Google Chrome installato (versione 148)
- pip

## Installazione

```bash
pip install -r requirements.txt
```

## Avvio

```bash
python3 bot.py
```

Al primo avvio si apre una finestra Chrome visibile: attende 5 secondi per il completamento della validazione Akamai, poi avvia il monitoraggio.

## Come funziona

Il bot apre Chrome tramite `undetected-chromedriver`, naviga su FanSale per acquisire i cookie di sessione (incluso `_abck` di Akamai), quindi ogni **15 secondi** esegue una `fetch()` JavaScript direttamente nel browser verso l'endpoint JSON. Per ogni offerta applica due filtri:

1. **Filtro quantità**: vengono considerate solo le offerte con esattamente 2 biglietti (`currentAmount == 2`)
2. **Filtro disponibilità**: le offerte temporaneamente bloccate nel carrello di un altro utente vengono scartate, rilevando una specifica stringa nel campo `evdetailsSplittingTypeTooltipHtml`

Quando un'offerta supera entrambi i filtri, il bot stampa in console una notifica con:
- Numero di biglietti
- Prezzo totale (incluse commissioni)
- Link diretto all'acquisto

Le offerte già notificate vengono tracciate in memoria per evitare notifiche duplicate nella stessa sessione.

## Output di esempio

```
🎟️  OFFERTA DISPONIBILE
Biglietti: 2
Prezzo: 124.50 €
Link: https://www.fansale.it/biglietti/...
```

## Notifiche Telegram (opzionale)

Il bot può inviare le notifiche direttamente su Telegram. Se le variabili non sono configurate, il bot funziona comunque stampando solo in console.

### 1. Creare il bot su Telegram

1. Apri Telegram e cerca **@BotFather**
2. Invia il comando `/newbot`
3. Scegli un nome visibile (es. `FanSale Monitor`)
4. Scegli uno username univoco che termina in `bot` (es. `fansale_monitor_bot`)
5. BotFather ti risponderà con il **token API** nel formato `123456789:AAF...xyz` — copialo

### 2. Ottenere il proprio Chat ID

1. Cerca il tuo bot su Telegram e invia un messaggio (es. `/start`)
2. Apri nel browser (sostituendo `<TOKEN>`):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Cerca il campo `"id"` dentro `"chat"` — quello è il tuo **Chat ID**

### 3. Configurare il file `.env`

Crea o aggiorna il file `.env` nella cartella del progetto:

```
TELEGRAM_TOKEN=123456789:AAF...xyz
TELEGRAM_CHAT_ID=987654321
```

---

## Note

- Il bot non salva dati su disco; riavviandolo, le offerte già viste verranno notificate nuovamente.
- Richiede connessione internet attiva per tutta la durata del monitoraggio.
- La finestra Chrome deve rimanere aperta durante il monitoraggio.
