import os
import sys
import random
from datetime import datetime, timedelta
from typing import List, Optional

# Ensure app package is discoverable from both root and backend directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.database import init_db, get_db, Offer, Order, Setting, ActivityLog
from app.review_generator import generate_review
from app.screenshot_service import generate_amazon_order_screenshot, SCREENSHOTS_DIR
from app.telegram_service import telegram_service, scrape_telegram_channel_offers
from app.email_service import create_order_from_data

import hashlib

# Inizializza DB
init_db()

app = FastAPI(title="Amazon Routine Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Monta la cartella degli screenshot
app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")

# Default password if not set in DB or ENV
def get_env_admin_password() -> str:
    return (
        os.getenv("ADMIN_PASSWORD")
        or os.getenv("admin_password")
        or os.getenv("PASSWORD")
        or os.getenv("password")
        or "123456"
    )

def get_current_admin_password(db: Session) -> str:
    env_pwd = get_env_admin_password()
    if env_pwd != "123456":
        return env_pwd
    s = db.query(Setting).filter_by(key="admin_password").first()
    if s and s.value:
        return s.value
    return env_pwd

def generate_auth_token(password: str) -> str:
    return hashlib.sha256(f"amz_salt_{password}_routine".encode()).hexdigest()

# Pydantic Schemas
class LoginPayload(BaseModel):
    password: str

class ChangePasswordPayload(BaseModel):
    old_password: str
    new_password: str

class SettingUpdate(BaseModel):
    key: str
    value: str

class RequestOfferPayload(BaseModel):
    recipient_override: Optional[str] = None

class ConfirmOrderPayload(BaseModel):
    recipient_override: Optional[str] = None

class SimulateOfferPayload(BaseModel):
    title: str
    price_info: str
    seller_contact: Optional[str] = "@venditore_promo"
    image_url: Optional[str] = None

class SimulateOrderPayload(BaseModel):
    product_title: str
    price: float
    order_number: Optional[str] = None
    seller_contact: Optional[str] = "@venditore_promo"
    product_image: Optional[str] = None

class TelegramChannelPayload(BaseModel):
    channel_name: str

class TelegramSendCodePayload(BaseModel):
    phone: Optional[str] = None

class TelegramVerifyPayload(BaseModel):
    code: str
    password_2fa: Optional[str] = None

class ParseTelegramPostPayload(BaseModel):
    raw_text: str
    image_url: Optional[str] = None
    channel_name: Optional[str] = None

class UploadScreenshotPayload(BaseModel):
    image_base64: str

class CreateOrderWithScreenshotPayload(BaseModel):
    product_title: str
    order_number: Optional[str] = None
    price: float = 0.0
    seller_contact: Optional[str] = None
    image_base64: Optional[str] = None

# ----------------- AUTHENTICATION & ACCESS CONTROL -----------------

@app.post("/api/auth/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    """Verifica la password di sicurezza e restituisce un token di sessione autenticato"""
    current_pwd = get_current_admin_password(db)
    if payload.password == current_pwd:
        token = generate_auth_token(current_pwd)
        return {"success": True, "token": token, "message": "Accesso consentito con successo!"}
    raise HTTPException(status_code=401, detail="Password errata. Riprova.")

@app.get("/api/auth/status")
def auth_status(token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Verifica se il token fornito è valido"""
    current_pwd = get_current_admin_password(db)
    valid_token = generate_auth_token(current_pwd)
    return {"authenticated": bool(token and token == valid_token)}

@app.post("/api/auth/change-password")
def change_password(payload: ChangePasswordPayload, db: Session = Depends(get_db)):
    """Permette all'utente di cambiare la password di sicurezza"""
    current_pwd = get_current_admin_password(db)
    if payload.old_password != current_pwd:
        raise HTTPException(status_code=401, detail="La password attuale non è corretta")
    
    if len(payload.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="La nuova password deve contenere almeno 4 caratteri")

    s = db.query(Setting).filter_by(key="admin_password").first()
    if s:
        s.value = payload.new_password.strip()
    else:
        db.add(Setting(key="admin_password", value=payload.new_password.strip()))
    db.commit()
    
    new_token = generate_auth_token(payload.new_password.strip())
    return {"success": True, "token": new_token, "message": "Password aggiornata con successo!"}

# ----------------- TELEGRAM AUTH & CHANNEL MANAGEMENT -----------------

@app.get("/api/telegram/status")
async def get_telegram_status(db: Session = Depends(get_db)):
    """Restituisce lo stato di connessione e autorizzazione dell'account Telegram"""
    return await telegram_service.get_auth_status(db)

@app.post("/api/telegram/send-code")
async def send_telegram_code(payload: Optional[TelegramSendCodePayload] = None, db: Session = Depends(get_db)):
    phone = payload.phone if payload and payload.phone else None
    res = await telegram_service.send_auth_code(db, phone)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Errore invio codice"))
    return res

@app.post("/api/telegram/verify-code")
async def verify_telegram_code(payload: TelegramVerifyPayload, db: Session = Depends(get_db)):
    res = await telegram_service.verify_auth_code(db, payload.code, payload.password_2fa)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Codice non valido o scaduto"))
    return res

@app.post("/api/telegram/logout")
async def telegram_logout(db: Session = Depends(get_db)):
    """Disconnette l'account Telegram e rimuove la sessione"""
    return await telegram_service.logout(db)

@app.get("/api/telegram/channel")
def get_active_channel(db: Session = Depends(get_db)):
    """Restituisce il canale Telegram attualmente attivo e monitorato"""
    channel_name = (
        telegram_service.get_setting(db, "active_telegram_channel")
        or telegram_service.get_setting(db, "telegram_channel")
        or "Articoli Addicted"
    )
    return {
        "channel_name": channel_name,
        "is_active": True
    }

@app.post("/api/telegram/channel")
def set_active_channel(payload: TelegramChannelPayload, db: Session = Depends(get_db)):
    clean_channel = payload.channel_name.strip()
    if clean_channel.startswith("https://t.me/+"):
        clean_channel = clean_channel
    elif clean_channel.startswith("https://t.me/s/"):
        clean_channel = "@" + clean_channel.replace("https://t.me/s/", "").strip("/")
    elif clean_channel.startswith("https://t.me/"):
        clean_channel = "@" + clean_channel.replace("https://t.me/", "").strip("/")
    elif " " not in clean_channel and not clean_channel.startswith("@") and not clean_channel.startswith("+"):
        clean_channel = "@" + clean_channel

    for k in ["active_telegram_channel", "telegram_channel"]:
        setting = db.query(Setting).filter_by(key=k).first()
        if setting:
            setting.value = clean_channel
        else:
            db.add(Setting(key=k, value=clean_channel))
    
    log = ActivityLog(
        action_type="CHANNEL_SET",
        title=f"Canale Telegram Operativo Impostato: {clean_channel}",
        details=f"Il monitoraggio delle offerte fa ora riferimento a {clean_channel}."
    )
    db.add(log)
    db.commit()
    return {"success": True, "channel_name": clean_channel}

@app.post("/api/telegram/sync-channel")
async def sync_telegram_channel(payload: Optional[TelegramChannelPayload] = None, db: Session = Depends(get_db)):
    """Scarica automaticamente le ultime offerte live dal canale Telegram autorizzato o pubblico"""
    channel = payload.channel_name if payload and payload.channel_name else get_active_channel(db)["channel_name"]
    
    # 1. Prova con il client Telegram autorizzato
    try:
        tele_res = await telegram_service.sync_channel_live(db, channel, limit=30)
        if tele_res.get("success"):
            return tele_res
        elif tele_res.get("auth_required"):
            return tele_res
    except Exception as e:
        print(f"[Telethon Sync Error] {e}")

    # 2. Fallback su anteprima web pubblica per canali pubblici
    offers_data = scrape_telegram_channel_offers(channel, limit=25)
    if offers_data:
        db.query(Offer).filter(Offer.status == "new").delete()
        db.commit()

        added_count = 0
        for item in offers_data:
            off = Offer(
                title=item["title"],
                price_info=item["price_info"],
                seller_contact=item["seller_contact"],
                image_url=item["image_url"],
                refund_pct=100.0,
                taxes_covered=item["taxes_covered"],
                channel_name=channel,
                status="new"
            )
            db.add(off)
            added_count += 1

        if added_count > 0:
            log = ActivityLog(
                action_type="CHANNEL_SYNC",
                title=f"Sincronizzazione Canale {channel}",
                details=f"Importate con successo {added_count} offerte con foto e contatti."
            )
            db.add(log)
            db.commit()

        return {
            "success": True,
            "count": added_count,
            "message": f"Sincronizzazione completata: {added_count} nuove offerte importate da {channel}!"
        }

    # 3. Se ci sono già offerte nel DB
    existing_count = db.query(Offer).filter(Offer.status.in_(["new", "requested"])).count()
    if existing_count > 0:
        return {
            "success": True,
            "count": existing_count,
            "message": f"Feed offerte aggiornato: {existing_count} offerte attive pronte per la selezione!"
        }

    return {
        "success": False,
        "auth_required": True,
        "count": 0,
        "message": f"Nessun post rilevato per '{channel}'. Collega il tuo account Telegram nelle Impostazioni per sincronizzare i canali privati."
    }

@app.post("/api/telegram/parse-post")
def parse_and_create_offer(payload: ParseTelegramPostPayload, db: Session = Depends(get_db)):
    """
    Riceve il testo e/o l'immagine di un post dal canale Telegram ed estrae
    automaticamente titolo prodotto, condizioni di spesa, rimborso, e username venditore.
    """
    raw = payload.raw_text.strip()
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    
    # 1. Estrazione contatto venditore (@username)
    import re
    seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw)
    seller_contact = "@venditore"
    if seller_match:
        # Seleziona il primo che non sia il nome del canale stesso
        for cand in seller_match:
            cand_full = f"@{cand}"
            active_chan = get_active_channel(db)["channel_name"]
            if cand_full.lower() != active_chan.lower():
                seller_contact = cand_full
                break
        if seller_contact == "@venditore" and seller_match:
            seller_contact = f"@{seller_match[0]}"

    # 2. Estrazione Condizioni Spesa & Prezzo
    price_info = "100% rimborso"
    for line in lines:
        if any(w in line.lower() for w in ["paga", "costo", "euro", "€", "tasse", "rimborso", "spesa", "commission"]):
            price_info = line
            break

    # 3. Copertura Tasse
    taxes_covered = True
    if any(w in raw.lower() for w in ["tasse forse", "tasse a parte", "no tasse", "tasse non coperte", "forse"]):
        taxes_covered = False
    elif any(w in raw.lower() for w in ["tasse coperte", "tasse incluse", "nessuna commissione", "senza tasse"]):
        taxes_covered = True

    # 4. Titolo Prodotto
    title = "Prodotto in Offerta da Telegram"
    for line in lines:
        # Trova la prima riga che non sia solo un tag o un prezzo o contatto
        clean_l = re.sub(r'https?://\S+', '', line)
        clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
        if len(clean_l) > 10 and not any(w in clean_l.lower() for w in ["contattare", "pm per link", "disponibile"]):
            title = clean_l
            break
    if title == "Prodotto in Offerta da Telegram" and lines:
        title = lines[0][:80]

    # 5. Immagine
    img_url = payload.image_url
    if not img_url:
        img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

    active_chan = get_active_channel(db)["channel_name"]
    offer = Offer(
        title=title,
        price_info=price_info,
        seller_contact=seller_contact,
        image_url=img_url,
        refund_pct=100.0,
        taxes_covered=taxes_covered,
        channel_name=payload.channel_name or active_chan,
        status="new"
    )
    db.add(offer)

    log = ActivityLog(
        action_type="OFFER_RECEIVED",
        title=f"Nuova Offerta dal Canale {active_chan}: {title[:40]}...",
        details=f"Condizioni: {price_info} | Contatto Venditore: {seller_contact}"
    )
    db.add(log)
    db.commit()
    db.refresh(offer)

    return {
        "success": True,
        "offer": {
            "id": offer.id,
            "title": offer.title,
            "price_info": offer.price_info,
            "seller_contact": offer.seller_contact,
            "image_url": offer.image_url,
            "taxes_covered": offer.taxes_covered
        }
    }

def consolidate_offer_albums(db: Session):
    """Assicura che gli album Telegram abbiano le foto collage e i titoli aggregati corretti"""
    try:
        base = SCREENSHOTS_DIR
        cosmetics = [os.path.join(base, f"tg_offer_{i}.jpg") for i in [46218, 46219, 46220, 46221]]
        out_cosmetics = os.path.join(base, "tg_album_46218_46221.jpg")
        if any(os.path.exists(p) for p in cosmetics):
            from app.telegram_service import create_album_collage
            create_album_collage([p for p in cosmetics if os.path.exists(p)], out_cosmetics)

        creams = [os.path.join(base, f"tg_offer_{i}.jpg") for i in [46222, 46223]]
        out_creams = os.path.join(base, "tg_album_46222_46223.jpg")
        if any(os.path.exists(p) for p in creams):
            from app.telegram_service import create_album_collage
            create_album_collage([p for p in creams if os.path.exists(p)], out_creams)

        # Rimuovi parti orfane duplicate
        db.query(Offer).filter(Offer.message_id.in_(["46219", "46220", "46221", "46223"])).delete(synchronize_session=False)

        # Aggiorna offerta set cosmetici
        off_cosm = db.query(Offer).filter_by(message_id="46218").first()
        if off_cosm:
            off_cosm.title = "Shampoo solido • Fondotinta • Rossetto • Siero effetto lifting"
            off_cosm.price_info = "FEEDBACK - non serve recensione • 100% - tasse coperte"
            if os.path.exists(out_cosmetics):
                off_cosm.image_url = "/screenshots/tg_album_46218_46221.jpg"
            off_cosm.taxes_covered = True

        # Aggiorna offerta set creme
        off_cream = db.query(Offer).filter_by(message_id="46222").first()
        if off_cream:
            off_cream.title = "Crema viso • Crema gambe"
            off_cream.price_info = "FEEDBACK - non serve recensione • 100% - tasse coperte"
            if os.path.exists(out_creams):
                off_cream.image_url = "/screenshots/tg_album_46222_46223.jpg"
            off_cream.taxes_covered = True

        db.commit()
    except Exception as e:
        db.rollback()

@app.get("/api/offers")
def get_offers(status: Optional[str] = None, include_dismissed: bool = False, db: Session = Depends(get_db)):
    # Rimuovi automaticamente offerte orfane incomplete o frammentate da vecchi import
    try:
        consolidate_offer_albums(db)
        db.query(Offer).filter(
            Offer.status == "new",
            or_(
                Offer.title.like("Articolo Offerta #%"),
                Offer.title == "Prodotto in Promozione"
            )
        ).delete(synchronize_session=False)

        # Deduplica globale tra tutte le offerte attive (sia 'new' che 'requested')
        all_active = db.query(Offer).filter(Offer.status.in_(["new", "requested"])).order_by(desc(Offer.created_at), desc(Offer.id)).all()
        seen_titles = set()
        for o in all_active:
            clean_t = o.title.strip().lower()
            if clean_t in seen_titles:
                db.delete(o)
            else:
                seen_titles.add(clean_t)

        db.commit()
    except Exception as e:
        db.rollback()

    query = db.query(Offer)
    if not include_dismissed:
        query = query.filter(Offer.status != "dismissed")
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(desc(Offer.created_at), desc(Offer.id))
    return query.all()

@app.post("/api/offers/{offer_id}/request")
async def request_offer(offer_id: int, payload: RequestOfferPayload = RequestOfferPayload(), db: Session = Depends(get_db)):
    offer = db.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    
    offer.status = "requested"
    
    # Crea SEMPRE l'ordine in 'Da Confermare' pronto per inserire la ricevuta Amazon
    existing_order = db.query(Order).filter_by(product_title=offer.title).first()
    if not existing_order:
        new_order_num = f"408-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
        order_date = datetime.utcnow()
        rev_data = generate_review(offer.title, gemini_api_key=get_gemini_api_key(db))
        new_order = Order(
            order_number=new_order_num,
            product_title=offer.title,
            product_image=offer.image_url,
            seller_contact=offer.seller_contact or "@alex8700",
            price_paid=0.00,
            refund_amount=0.00,
            status="pending_confirmation",
            order_date=order_date,
            review_target_date=order_date + timedelta(days=10),
            review_title=rev_data.get("title", "Ottimo acquisto, qualità eccellente!"),
            review_body=rev_data.get("body", "Prodotto eccellente e spedizione rapida. Consigliatissimo!"),
            is_test=False
        )
        db.add(new_order)
    db.commit()

    # Invia messaggio di richiesta disponibilità ad Alex
    try:
        await telegram_service.send_availability_request(
            db=db,
            offer=offer,
            recipient="me"
        )
    except Exception as e:
        print(f"[Telegram Send Request Error] {e}")
    
    return {
        "success": True, 
        "message": "Richiesta inviata ad Alex! Scheda creata in Da Confermare."
    }

@app.post("/api/offers/{offer_id}/reset")
def reset_offer_status(offer_id: int, db: Session = Depends(get_db)):
    """Reimposta lo stato di un'offerta a 'new' per poter richiedere nuovamente la disponibilità"""
    offer = db.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    offer.status = "new"
    db.commit()
    return {"success": True, "message": "Stato offerta reimpostato a Nuovo!"}

@app.post("/api/offers/reset-all")
def reset_all_offers_status(db: Session = Depends(get_db)):
    """Reimposta tutte le offerte con richiesta inviata a 'new'"""
    count = db.query(Offer).filter_by(status="requested").update({"status": "new"})
    db.commit()
    return {"success": True, "count": count, "message": f"{count} richieste reimpostate a Nuovo!"}

@app.delete("/api/offers/{offer_id}")
def dismiss_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    db.delete(offer)
    db.commit()
    return {"success": True}

# ----------------- ORDERS / CONFIRMATIONS ENDPOINTS -----------------

def get_gemini_api_key(db: Session) -> Optional[str]:
    s = db.query(Setting).filter_by(key="gemini_api_key").first()
    return s.value.strip() if s and s.value and s.value.strip() else None

@app.get("/api/orders")
def get_orders(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Order).order_by(desc(Order.order_date))
    if status:
        query = query.filter_by(status=status)
    
    orders = query.all()
    res = []
    now = datetime.utcnow()
    updated_db = False
    gemini_key = get_gemini_api_key(db)
    
    for o in orders:
        if not o.review_target_date:
            base_date = o.confirmation_sent_at or o.order_date or now
            o.review_target_date = base_date + timedelta(days=10)
            updated_db = True
            
        # Rigenera se mancante o se era rimasta la vecchia recensione generica identica
        if not o.review_title or not o.review_body or o.review_title == "Ottimo prodotto, spedizione impeccabile" or "Arrivato puntuale, ben imballato. Qualità dei materiali ottima e facilissimo da utilizzare." in (o.review_body or ""):
            rev_data = generate_review(o.product_title, gemini_api_key=gemini_key)
            o.review_title = rev_data.get("title", "Ottimo acquisto, qualità eccellente!")
            o.review_body = rev_data.get("body", "Prodotto eccellente e spedizione rapida. Consigliatissimo!")
            updated_db = True
            
        remaining_seconds = (o.review_target_date - now).total_seconds()
        if o.status in ["review_ready", "review_submitted", "reimbursed"] or remaining_seconds <= 0:
            days_until_review = 0
        else:
            days_until_review = max(1, int(remaining_seconds // 86400))
            
        res.append({
            "id": o.id,
            "order_number": o.order_number,
            "product_title": o.product_title,
            "product_image": o.product_image,
            "seller_contact": o.seller_contact,
            "price_paid": o.price_paid,
            "refund_amount": o.refund_amount,
            "status": o.status,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "confirmation_screen_url": o.confirmation_screen_url,
            "confirmation_sent_at": o.confirmation_sent_at.isoformat() if o.confirmation_sent_at else None,
            "review_target_date": o.review_target_date.isoformat() if o.review_target_date else None,
            "days_until_review": days_until_review,
            "review_title": o.review_title,
            "review_body": o.review_body,
            "review_submitted_at": o.review_submitted_at.isoformat() if o.review_submitted_at else None,
            "review_screen_url": o.review_screen_url,
            "refunded_at": o.refunded_at.isoformat() if o.refunded_at else None,
            "is_test": o.is_test
        })
    if updated_db:
        db.commit()
    return res

class OfferUpdatePayload(BaseModel):
    title: Optional[str] = None
    price_info: Optional[str] = None

@app.put("/api/offers/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdatePayload, db: Session = Depends(get_db)):
    """Permette di modificare il nome articolo o le condizioni di spesa"""
    offer = db.query(Offer).filter_by(id=offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offerta non trovata")
    if payload.title is not None and payload.title.strip():
        offer.title = payload.title.strip()
    if payload.price_info is not None and payload.price_info.strip():
        offer.price_info = payload.price_info.strip()
    db.commit()
    return {"success": True, "title": offer.title, "price_info": offer.price_info}

@app.post("/api/orders/{order_id}/confirm-and-send")
async def confirm_and_send_order(order_id: int, payload: ConfirmOrderPayload = ConfirmOrderPayload(), db: Session = Depends(get_db)):
    """
    IL TASTO DI CONFERMA:
    Invia lo screenshot dell'ordine e il numero al venditore Telegram e sposta l'ordine
    nello stato 'waiting_review' attivando il timer di 10 giorni.
    """
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
        
    target_contact = payload.recipient_override or order.seller_contact or "@venditore_telegram"
    
    now = datetime.utcnow()
    order.status = "waiting_review"
    order.confirmation_sent_at = now
    order.review_target_date = now + timedelta(days=10)
    
    if not order.review_title or not order.review_body:
        rev_data = generate_review(order.product_title, gemini_api_key=get_gemini_api_key(db))
        order.review_title = rev_data.get("title", "Ottimo acquisto, qualità eccellente!")
        order.review_body = rev_data.get("body", "Prodotto eccellente e spedizione rapida. Consigliatissimo!")
        
    db.commit()
    
    # Invia screenshot a venditore via Telegram
    try:
        await telegram_service.send_order_confirmation(
            db=db,
            order=order,
            recipient="me"
        )
    except Exception as e:
        print(f"[Telegram Send Screen Error] {e}")
    
    return {"success": True, "message": "Screenshot e Numero Ordine inviati! Ordine spostato in Recensioni 5★."}

@app.post("/api/orders/{order_id}/send-review")
async def send_review_confirmation(order_id: int, db: Session = Depends(get_db)):
    """Invia la conferma della recensione pubblicata al venditore"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
        
    res = await telegram_service.send_review_confirmation(
        db=db,
        order=order,
        recipient=order.seller_contact
    )
    
    if res.get("success"):
        return res
    else:
        raise HTTPException(status_code=500, detail=f"Errore durante l'invio recensione: {res.get('error', 'Invio fallito')}")

@app.post("/api/orders/{order_id}/mark-refunded")
def mark_order_refunded(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    order.status = "reimbursed"
    order.refunded_at = datetime.utcnow()
    
    log = ActivityLog(
        action_type="REFUND_RECEIVED",
        title=f"Rimborso Ricevuto: €{order.refund_amount:.2f}",
        details=f"Ordine {order.order_number} ({order.product_title}) saldato con successo!"
    )
    db.add(log)
    db.commit()
    return {"success": True}

@app.get("/api/orders/{order_id}/regenerate-review")
def regenerate_order_review(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    review = generate_review(order.product_title, gemini_api_key=get_gemini_api_key(db))
    order.review_title = review["title"]
    order.review_body = review["body"]
    
    # Aggiorna anche l'immagine dello screenshot recensione
    from app.screenshot_service import generate_amazon_review_screenshot
    order.review_screen_url = generate_amazon_review_screenshot(
        order_number=order.order_number,
        product_title=order.product_title,
        review_title=review["title"],
        review_body=review["body"]
    )
    db.commit()
    return review

@app.post("/api/orders/{order_id}/fast-forward-timer")
def fast_forward_order_timer(order_id: int, db: Session = Depends(get_db)):
    """Simula lo scadere immediato dei 10 giorni per testare l'invio recensione"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    order.review_target_date = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    return {"success": True, "message": "Timer avanzato a 10 giorni! Recensione sbloccata."}

@app.post("/api/orders/{order_id}/reset-timer")
def reset_order_timer(order_id: int, db: Session = Depends(get_db)):
    """Reimposta il timer a 10 giorni da adesso"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    now = datetime.utcnow()
    order.confirmation_sent_at = now
    order.review_target_date = now + timedelta(days=10)
    db.commit()
    return {"success": True, "message": "Timer reimpostato a 10 giorni da adesso!"}

@app.get("/api/orders/{order_id}/review-screen")
def get_order_review_screen(order_id: int, db: Session = Depends(get_db)):
    """Restituisce l'URL dell'immagine dello screenshot della recensione Amazon a 5 stelle"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    
    from app.screenshot_service import generate_amazon_review_screenshot
    if not order.review_screen_url:
        order.review_screen_url = generate_amazon_review_screenshot(
            order_number=order.order_number,
            product_title=order.product_title,
            review_title=order.review_title or "Ottimo prodotto, spedizione impeccabile",
            review_body=order.review_body or "Arrivato puntuale, ben imballato. Qualità dei materiali ottima e facilissimo da utilizzare. Pienamente soddisfatto!"
        )
        db.commit()
        
    return {"review_screen_url": order.review_screen_url}

@app.post("/api/orders/{order_id}/upload-screenshot")
def upload_order_screenshot(order_id: int, payload: UploadScreenshotPayload, db: Session = Depends(get_db)):
    """Permette all'utente di caricare o incollare lo screenshot originale reale preso dall'app/sito Amazon"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    
    import base64
    raw_b64 = payload.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    
    img_bytes = base64.b64decode(raw_b64)
    filename = f"orig_screen_{order.id}_{int(datetime.utcnow().timestamp())}.jpg"
    file_path = os.path.join(SCREENSHOTS_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(img_bytes)
        
    order.confirmation_screen_url = f"/screenshots/{filename}"
    db.commit()
    
    return {
        "success": True,
        "confirmation_screen_url": order.confirmation_screen_url,
        "message": "Screenshot originale caricato con successo!"
    }

@app.post("/api/orders/{order_id}/upload-review-screenshot")
def upload_order_review_screenshot(order_id: int, payload: UploadScreenshotPayload, db: Session = Depends(get_db)):
    """Permette all'utente di caricare o incollare lo screenshot originale reale della recensione da iPhone/PC"""
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    
    import base64
    raw_b64 = payload.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    
    img_bytes = base64.b64decode(raw_b64)
    filename = f"orig_review_screen_{order.id}_{int(datetime.utcnow().timestamp())}.jpg"
    file_path = os.path.join(SCREENSHOTS_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(img_bytes)
        
    order.review_screen_url = f"/screenshots/{filename}"
    db.commit()
    
    return {
        "success": True,
        "review_screen_url": order.review_screen_url,
        "message": "Screenshot recensione originale caricato con successo!"
    }

@app.post("/api/orders/{order_id}/grab-latest-pc-screenshot")
def grab_latest_pc_screenshot(order_id: int, db: Session = Depends(get_db)):
    """
    Rileva semi-automaticamente l'ultimo screenshot appena scattato sul PC/Windows
    (es. tramite tasto Stamp o Win+Shift+S salvato in Immagini/Screenshots, Desktop o Download).
    """
    order = db.query(Order).filter_by(id=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    import shutil
    user_home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(user_home, "Pictures", "Screenshots"),
        os.path.join(user_home, "Immagini", "Screenshots"),
        os.path.join(user_home, "Pictures"),
        os.path.join(user_home, "Immagini"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Downloads"),
    ]

    candidate_files = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for fname in os.listdir(sdir):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    fpath = os.path.join(sdir, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        candidate_files.append((mtime, fpath, fname))
                    except:
                        pass

    if not candidate_files:
        raise HTTPException(status_code=404, detail="Nessuno screenshot recente trovato nella cartella Immagini/Desktop.")

    # Ordina per il più recente
    candidate_files.sort(key=lambda x: x[0], reverse=True)
    latest_time, latest_path, latest_name = candidate_files[0]

    # Copia nella cartella screenshots dell'app
    ext = os.path.splitext(latest_name)[1] or ".jpg"
    dest_filename = f"orig_screen_{order.id}_{int(datetime.utcnow().timestamp())}{ext}"
    dest_path = os.path.join(SCREENSHOTS_DIR, dest_filename)
    shutil.copyfile(latest_path, dest_path)

    order.confirmation_screen_url = f"/screenshots/{dest_filename}"
    db.commit()

    return {
        "success": True,
        "source_file": latest_name,
        "confirmation_screen_url": order.confirmation_screen_url,
        "message": f"Screenshot '{latest_name}' catturato e collegato all'ordine!"
    }

@app.post("/api/orders/create-from-original-screenshot")
def create_order_with_original_screenshot(payload: CreateOrderWithScreenshotPayload, db: Session = Depends(get_db)):
    """Crea una nuova pratica caricando direttamente lo screenshot originale di Amazon"""
    import base64
    order_num = payload.order_number or f"408-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
    filename = f"orig_screen_custom_{int(datetime.utcnow().timestamp())}.jpg"
    file_path = os.path.join(SCREENSHOTS_DIR, filename)
    
    if payload.image_base64:
        raw_b64 = payload.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        with open(file_path, "wb") as f:
            f.write(img_bytes)
        screen_url = f"/screenshots/{filename}"
    else:
        screen_url = generate_amazon_order_screenshot(order_num, payload.product_title, payload.price)
        
    order = create_order_from_data(
        db=db,
        order_number=order_num,
        product_title=payload.product_title,
        price=payload.price,
        seller_contact=payload.seller_contact or "@venditore_test",
        is_test=True
    )
    order.confirmation_screen_url = screen_url
    db.commit()
    
    return {
        "success": True,
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "product_title": order.product_title,
            "confirmation_screen_url": order.confirmation_screen_url
        },
        "message": "Ordine registrato con il tuo screenshot originale! Pronto per il Tasto di Conferma."
    }

# ----------------- STATS & LOGS -----------------

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total_spent = sum(o.price_paid for o in db.query(Order).filter(Order.status != "cancelled").all())
    pending_refund = sum(o.refund_amount for o in db.query(Order).filter(Order.status.in_(["waiting_review", "review_ready", "review_submitted", "pending_confirmation"])).all())
    reimbursed_total = sum(o.refund_amount for o in db.query(Order).filter_by(status="reimbursed").all())
    
    new_offers_count = db.query(Offer).filter_by(status="new").count()
    pending_confirmation_count = db.query(Order).filter_by(status="pending_confirmation").count()
    active_orders_count = db.query(Order).filter(Order.status.in_(["pending_confirmation", "waiting_review", "review_ready", "review_submitted"])).count()
    
    return {
        "total_spent": total_spent,
        "pending_refund": pending_refund,
        "reimbursed_total": reimbursed_total,
        "new_offers_count": new_offers_count,
        "pending_confirmation_count": pending_confirmation_count,
        "active_orders_count": active_orders_count
    }

@app.get("/api/logs")
def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(desc(ActivityLog.timestamp)).limit(limit).all()

# ----------------- SETTINGS -----------------

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@app.post("/api/settings")
def update_settings(items: List[SettingUpdate], db: Session = Depends(get_db)):
    for item in items:
        s = db.query(Setting).filter_by(key=item.key).first()
        if s:
            s.value = item.value
        else:
            db.add(Setting(key=item.key, value=item.value))
    db.commit()
    return {"success": True}

# ----------------- SIMULATOR / TEST ENDPOINTS -----------------

DEMO_PRODUCTS = [
    {
        "title": "Comodino Moderno Cilindrico 2 Ripiani con Vano Nascosto",
        "price_info": "si paga 8,00€ - 10% (tasse coperte)",
        "seller_contact": "@venditore_arredo",
        "image_url": "https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80",
        "price": 8.00
    },
    {
        "title": "Lavatappeti e Divani Portatile ad Aspirazione Profonda 650W",
        "price_info": "si paga 20,00€ (tasse da verificare)",
        "seller_contact": "@venditore_elettro",
        "image_url": "https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=800&q=80",
        "price": 20.00
    },
    {
        "title": "Auricolari Bluetooth 5.3 con Cancellazione Rumore ANC e Display LED",
        "price_info": "100% rimborso (nessuna tassa)",
        "seller_contact": "@tech_promo_deals",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=80",
        "price": 29.99
    },
    {
        "title": "Smartwatch Fitness Tracker con Cardiofrequenzimetro e Monitor Sonno",
        "price_info": "si paga 15,00€ (tasse coperte)",
        "seller_contact": "@smart_gadget_hub",
        "image_url": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80",
        "price": 34.50
    }
]

@app.post("/api/simulator/new-offer")
def simulate_new_offer(payload: SimulateOfferPayload, db: Session = Depends(get_db)):
    """Crea una nuova offerta di test per simulare l'arrivo di un post Telegram"""
    img = payload.image_url
    if not img:
        # Seleziona una foto adatta se disponibile
        for p in DEMO_PRODUCTS:
            if p["title"].lower() in payload.title.lower() or payload.title.lower() in p["title"].lower():
                img = p["image_url"]
                break
        if not img:
            img = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

    offer = Offer(
        title=payload.title,
        price_info=payload.price_info,
        seller_contact=payload.seller_contact,
        image_url=img,
        refund_pct=100.0,
        taxes_covered=True,
        status="new"
    )
    db.add(offer)
    
    log = ActivityLog(
        action_type="OFFER_RECEIVED",
        title=f"Nuova Offerta Telegram: {payload.title}",
        details=f"Condizioni: {payload.price_info} | Contatto: {payload.seller_contact}"
    )
    db.add(log)
    db.commit()
    db.refresh(offer)
    return offer

@app.post("/api/simulator/new-order")
def simulate_new_order(payload: SimulateOrderPayload, db: Session = Depends(get_db)):
    """Simula l'acquisto su Amazon e l'arrivo della mail di conferma con screenshot pronto"""
    random_id = f"408-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
    order_num = payload.order_number or random_id
    
    img = payload.product_image
    if not img:
        for p in DEMO_PRODUCTS:
            if p["title"].lower() in payload.product_title.lower() or payload.product_title.lower() in p["title"].lower():
                img = p["image_url"]
                break
        if not img:
            img = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

    order = create_order_from_data(
        db=db,
        order_number=order_num,
        product_title=payload.product_title,
        price=payload.price,
        seller_contact=payload.seller_contact,
        is_test=True,
        product_image=img
    )
    return order

@app.post("/api/simulator/reset-demo")
def reset_demo_data(db: Session = Depends(get_db)):
    """Ripristina un set di offerte e ordini di test completi di foto zoomabili ad alta definizione"""
    db.query(Offer).delete()
    db.query(Order).delete()
    db.query(ActivityLog).delete()
    
    # 1. Offerta Comodino
    off1 = Offer(
        title="Comodino Moderno Cilindrico 2 Ripiani con Vano Nascosto",
        price_info="si paga 8,00€ - 10% (tasse coperte)",
        seller_contact="@venditore_arredo",
        image_url="https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80",
        refund_pct=100.0,
        taxes_covered=True,
        status="new",
        created_at=datetime.utcnow() - timedelta(minutes=10)
    )
    
    # 2. Offerta Lavatappeti
    off2 = Offer(
        title="Lavatappeti e Divani Portatile ad Aspirazione Profonda 650W",
        price_info="si paga 20,00€ (tasse da verificare)",
        seller_contact="@venditore_elettro",
        image_url="https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=800&q=80",
        refund_pct=100.0,
        taxes_covered=False,
        status="new",
        created_at=datetime.utcnow() - timedelta(minutes=45)
    )

    # 3. Offerta Auricolari
    off3 = Offer(
        title="Auricolari Bluetooth 5.3 con Cancellazione Rumore ANC e Custodia Ricarica",
        price_info="100% rimborso (nessuna commissione)",
        seller_contact="@tech_promo_deals",
        image_url="https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=80",
        refund_pct=100.0,
        taxes_covered=True,
        status="new",
        created_at=datetime.utcnow() - timedelta(hours=2)
    )
    db.add_all([off1, off2, off3])
    db.commit()

    # 4. Ordine in attesa di Tasto di Conferma (con foto e screen)
    ord1 = create_order_from_data(
        db=db,
        order_number="408-7392014-9182341",
        product_title="Comodino Moderno Cilindrico 2 Ripiani Bianco",
        price=8.00,
        seller_contact="@venditore_arredo",
        is_test=True,
        product_image="https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=800&q=80"
    )

    # 5. Ordine in attesa di recensione (Giorno 8/10)
    ord2 = create_order_from_data(
        db=db,
        order_number="408-5521908-1124509",
        product_title="Lavatappeti Aspirapolvere per Divani e Tappeti 650W",
        price=20.00,
        seller_contact="@venditore_elettro",
        is_test=True,
        product_image="https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&w=800&q=80"
    )
    ord2.status = "waiting_review"
    ord2.order_date = datetime.utcnow() - timedelta(days=8)
    ord2.review_target_date = datetime.utcnow() + timedelta(days=2)

    # 6. Ordine pronto per rimborso PayPal
    ord3 = create_order_from_data(
        db=db,
        order_number="408-1934850-8472910",
        product_title="Smartwatch Fitness Tracker Display AMOLED Impermeabile",
        price=34.50,
        seller_contact="@smart_gadget_hub",
        is_test=True,
        product_image="https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80"
    )
    ord3.status = "review_submitted"
    ord3.order_date = datetime.utcnow() - timedelta(days=12)
    ord3.review_target_date = datetime.utcnow() - timedelta(days=2)
    ord3.review_submitted_at = datetime.utcnow() - timedelta(days=1)
    
    db.commit()
    return {"success": True, "message": "Demo data resettati con successo!"}

# Inserisci dati iniziali demo se il DB è vuoto o aggiorna immagini mancanti
@app.on_event("startup")
def populate_demo_data_if_empty():
    db = next(get_db())
    try:
        if db.query(Offer).count() == 0 and db.query(Order).count() == 0:
            reset_demo_data(db)
        else:
            # Aggiorna offerte senza immagini
            for o in db.query(Offer).filter(Offer.image_url == None).all():
                for p in DEMO_PRODUCTS:
                    if p["title"][:15].lower() in o.title.lower() or o.title[:15].lower() in p["title"].lower():
                        o.image_url = p["image_url"]
                        break
                if not o.image_url:
                    o.image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"
            
            for ord in db.query(Order).filter(Order.product_image == None).all():
                for p in DEMO_PRODUCTS:
                    if p["title"][:15].lower() in ord.product_title.lower() or ord.product_title[:15].lower() in p["title"].lower():
                        ord.product_image = p["image_url"]
                        break
                if not ord.product_image:
                    ord.product_image = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"
            db.commit()
    finally:
        db.close()

# Monta la cartella del frontend statico
candidate_frontend_dirs = [
    os.path.join(PROJECT_DIR, "frontend"),
    os.path.join(BACKEND_DIR, "frontend"),
    "/app/frontend",
    os.path.join(os.getcwd(), "frontend")
]
FRONTEND_DIR = None
for candidate in candidate_frontend_dirs:
    if os.path.exists(candidate) and os.path.isdir(candidate):
        FRONTEND_DIR = candidate
        break

if FRONTEND_DIR:
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
