import os
import time
import requests
import undetected_chromedriver as uc
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.fansale.it"
INTERVAL = 15
REFRESH_EVERY = 5  # rinaviga sulla home ogni N request per ottenere cookie freschi

AVAILABLE_TEXTS = (
    "L'offerta può essere acquistato solo al numero di biglietti visualizzato.",
    "L'offerta può essere acquistata con un numero individuale di biglietti.",
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

seen_ids = set()
_driver = None
_request_count = 0


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def _log_cookies():
    cookies = _driver.get_cookies()
    abck = next((c['value'][:60] for c in cookies if c['name'] == '_abck'), 'assente')
    log(f"Cookie acquisiti: {[c['name'] for c in cookies]}")
    log(f"_abck (inizio): {abck}...")


def init_session():
    global _driver

    log("Avvio Chrome (undetected)...")
    options = uc.ChromeOptions()
    options.add_argument("--lang=it-IT")
    _driver = uc.Chrome(options=options, headless=False, version_main=148)

    log(f"Navigazione verso {BASE_URL}...")
    _driver.get(BASE_URL)

    log("Attesa validazione Akamai (5s)...")
    time.sleep(5)
    _log_cookies()


def refresh_session():
    log(f"Refresh sessione: rinavigazione verso la home per aggiornare i cookie...")
    _driver.get(BASE_URL)
    time.sleep(5)
    _log_cookies()


def _do_fetch(url):
    return _driver.execute_async_script(
        """
        var callback = arguments[arguments.length - 1];
        fetch(arguments[0], {
            headers: {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.fansale.it/',
            }
        })
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) { callback({ok: true, data: data}); })
        .catch(function(err) { callback({ok: false, error: err.toString()}); });
        """,
        url,
    )


def fetch_offers():
    global _request_count
    _request_count += 1

    if _request_count % REFRESH_EVERY == 0:
        log(f"Refresh programmato (ogni {REFRESH_EVERY} request)")
        refresh_session()

    # url = f"https://www.fansale.it/json/offers/21061016?_={int(time.time() * 1000)}"  # coez
    url = f"https://www.fansale.it/json/offers/20456011?_={int(time.time() * 1000)}"  # ultimo
    log(f"fetch() in-browser -> {url}")

    result = _do_fetch(url)

    if not result.get("ok"):
        error = result.get("error", "Errore sconosciuto")
        if "403" in error:
            log("403 ricevuto — refresh sessione e retry...")
            refresh_session()
            result = _do_fetch(url)
            if not result.get("ok"):
                raise Exception(result.get("error", "Errore sconosciuto dopo refresh"))
        else:
            raise Exception(error)

    offers = result["data"].get("offers", [])
    log(f"Risposta OK — offerte: {len(offers)}")
    return offers


def is_valid(offer):
    offer_id = offer.get("id")
    amount = offer.get("currentAmount")
    if amount != 2 and amount != 1:
        log(f"Offerta {offer_id} scartata: quantità {amount} (richiesta 1 o 2)")
        return False
    tooltip = offer.get("evdetailsSplittingTypeTooltipHtml", "")
    if not any(t in tooltip for t in AVAILABLE_TEXTS):
        log(f"Offerta {offer_id} scartata: testo disponibilità assente nel tooltip")
        return False
    log(f"Offerta {offer_id} VALIDA — quantità: {amount}")
    return True


def format_notification(offer):
    price = offer.get("minPurchasablePriceWithBuyerCommission", "N/A")
    url = BASE_URL + offer.get("initialOfferUrl", "")
    return (
        f"🎟️  OFFERTA DISPONIBILE\n"
        f"Biglietti: {offer['currentAmount']}\n"
        f"Prezzo: {price} €\n"
        f"Link: {url} \n"
        
    )


def send_telegram(chat_id, text):
    if not TELEGRAM_TOKEN:
        log("Telegram non inviato: TELEGRAM_TOKEN non configurato")
        return
    if not chat_id:
        log("Telegram non inviato: chat_id non disponibile (invia un messaggio al bot prima di avviarlo)")
        return
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            timeout=10,
        )
        print(response.text)

        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        
        # Questo costringe Python a lanciare un'eccezione se Telegram risponde con un errore (es. 400, 401)
        response.raise_for_status() 
        
        log("Telegram: messaggio inviato")
    except requests.RequestException as e:
        # Se c'è un errore, qui vedrai cosa ha risposto Telegram
        if 'response' in locals() and response is not None:
            log(f"Telegram non inviato. Errore: {response.status_code} - {response.text}")
        else:
            log(f"Telegram non inviato: {e}")

def main():
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        log(f"Telegram attivo. Chat ID: {TELEGRAM_CHAT_ID}")
    else:
        log("Telegram non attivo: configura TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nel file .env")

    init_session()
    log("Bot avviato. Monitoraggio in corso...")

    while True:
        try:
            offers = fetch_offers()
            for offer in offers:
                offer_id = offer.get("id")
                if offer_id in seen_ids:
                    continue
                if is_valid(offer):
                    seen_ids.add(offer_id)
                    message = format_notification(offer)
                    print(message)
                    send_telegram(TELEGRAM_CHAT_ID, message)
        except Exception as e:
            log(f"Errore: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
