import os
import re
import html
import asyncio
import requests
from datetime import datetime
from telethon import TelegramClient, events
from sqlalchemy.orm import Session
from app.database import Setting, ActivityLog, Order, Offer

def clean_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    # Replace <br/> and </p> with newlines
    text = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def scrape_telegram_channel_offers(channel_identifier: str, limit: int = 15) -> list:
    """
    Scarica e analizza i post più recenti da un canale pubblico Telegram tramite l'anteprima web (https://t.me/s/...)
    Estrae: ID messaggio, Foto ad alta risoluzione, Testo, Titolo prodotto, Condizioni di spesa e Contatto Venditore.
    """
    clean = channel_identifier.strip().lstrip('@')
    clean = clean.replace("https://t.me/s/", "").replace("https://t.me/", "").strip("/")
    
    if not clean or clean.startswith("+"):
        # Canale privato con link di invito
        return []

    url = f"https://t.me/s/{clean}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []
            
        page_html = resp.text
        
        # Trova tutti i blocchi messaggio
        # Ogni messaggio è racchiuso in <div class="tgme_widget_message_wrap js-widget_message_wrap" ...>
        message_blocks = re.findall(r'<div class="tgme_widget_message\b[^>]*>(.*?)<div class="tgme_widget_message_footer\b', page_html, re.DOTALL)
        
        offers_found = []
        for block in message_blocks[-limit:]:
            # 1. Estrazione Foto
            # style="background-image:url('...')"
            img_match = re.search(r'background-image:url\([\'"]?(https?://[^\'")]+)[\'"]?\)', block)
            if not img_match:
                img_match = re.search(r'src=[\'"]?(https?://[^\'">\s]+)[\'"]?', block)
            img_url = img_match.group(1) if img_match else None

            # 2. Estrazione Testo
            text_match = re.search(r'<div class="tgme_widget_message_text\b[^>]*>(.*?)</div>', block, re.DOTALL)
            raw_text = clean_html_text(text_match.group(1)) if text_match else ""

            if not raw_text and not img_url:
                continue

            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            # 3. Estrazione Contatto Venditore
            seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw_text)
            seller_contact = "@venditore"
            if seller_match:
                for cand in seller_match:
                    if cand.lower() != clean.lower():
                        seller_contact = f"@{cand}"
                        break

            # 4. Estrazione Condizioni Spesa & Rimborso
            price_info = "100% rimborso"
            for line in lines:
                if any(w in line.lower() for w in ["paga", "costo", "euro", "€", "tasse", "rimborso", "spesa"]):
                    price_info = line
                    break

            taxes_covered = True
            if any(w in raw_text.lower() for w in ["tasse forse", "tasse a parte", "no tasse", "tasse non coperte", "forse"]):
                taxes_covered = False

            # 5. Titolo
            title = "Offerta Telegram"
            for line in lines:
                clean_l = re.sub(r'https?://\S+', '', line)
                clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
                if len(clean_l) > 8 and not any(w in clean_l.lower() for w in ["contattare", "pm per link", "disponibile"]):
                    title = clean_l
                    break
            if title == "Offerta Telegram" and lines:
                title = lines[0][:80]

            if not img_url:
                img_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

            offers_found.append({
                "title": title,
                "price_info": price_info,
                "seller_contact": seller_contact,
                "image_url": img_url,
                "taxes_covered": taxes_covered,
                "raw_text": raw_text
            })

        return offers_found
    except Exception as e:
        print(f"[Scraper Error] {e}")
        return []

_global_telethon_client = None

class TelegramManager:
    def __init__(self):
        self.is_connected = False
        self.is_listening = False
        self.db_session_factory = None

    @property
    def client(self):
        global _global_telethon_client
        return _global_telethon_client

    @client.setter
    def client(self, val):
        global _global_telethon_client
        _global_telethon_client = val

    def get_setting(self, db: Session, key: str, default: str = "") -> str:
        s = db.query(Setting).filter_by(key=key).first()
        return s.value if s and s.value else default

    def _get_session_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "telegram_user_session")

    async def _ensure_connected_client(self, db: Session):
        global _global_telethon_client
        api_id_raw = self.get_setting(db, "telegram_api_id")
        api_id = int(api_id_raw) if api_id_raw and str(api_id_raw).strip().isdigit() else 31327962
        api_hash = self.get_setting(db, "telegram_api_hash") or "aa62f6773d556234f4b5812a1f7208d1"
        
        session_path = self._get_session_path()
        if _global_telethon_client is None:
            _global_telethon_client = TelegramClient(session_path, api_id, api_hash)
        if not _global_telethon_client.is_connected():
            await _global_telethon_client.connect()
        return _global_telethon_client

    async def initialize(self, db: Session):
        api_id_raw = self.get_setting(db, "telegram_api_id")
        api_id = int(api_id_raw) if api_id_raw and str(api_id_raw).strip().isdigit() else 31327962
        api_hash = self.get_setting(db, "telegram_api_hash") or "aa62f6773d556234f4b5812a1f7208d1"
        phone = self.get_setting(db, "telegram_phone")
        test_mode = self.get_setting(db, "test_mode", "true").lower() == "true"

        if test_mode or not api_id or not api_hash:
            print("[Telegram Service] Modalità Test / Sandbox attiva (Nessuna connessione Telegram reale richiesta).")
            self.is_connected = False
            return {"status": "sandbox_mode", "message": "In modalità test. I messaggi verranno registrati nel log senza invio reale."}

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"status": "auth_required", "message": "Autenticazione richiesta. Inserisci il codice inviato al tuo numero."}

            self.is_connected = True
            print("[Telegram Service] Connesso con successo all'account Telegram!")
            return {"status": "connected", "message": "Connesso all'account Telegram."}
        except Exception as e:
            print(f"[Telegram Service] Errore di connessione: {e}")
            self.is_connected = False
            return {"status": "error", "message": str(e)}

    async def send_auth_code(self, db: Session) -> dict:
        api_id = self.get_setting(db, "telegram_api_id")
        api_hash = self.get_setting(db, "telegram_api_hash")
        phone = self.get_setting(db, "telegram_phone")

        if not api_id or not api_hash or not phone:
            return {"success": False, "error": "Credenziali mancanti (API ID, Hash o Telefono)"}

        try:
            session_path = self._get_session_path()
            if not self.client:
                self.client = TelegramClient(session_path, int(api_id), api_hash)
            if not self.client.is_connected():
                await self.client.connect()

            if await self.client.is_user_authorized():
                self.is_connected = True
                return {"success": True, "status": "already_authorized", "message": "Account Telegram già autorizzato e connesso!"}

            code_obj = await self.client.send_code_request(phone)
            self.phone_code_hash = code_obj.phone_code_hash
            return {"success": True, "status": "code_sent", "message": f"Codice di verifica Telegram inviato a {phone}!"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def verify_auth_code(self, db: Session, code: str, password_2fa: str = None) -> dict:
        phone = self.get_setting(db, "telegram_phone")
        try:
            if not self.client or not self.client.is_connected():
                await self.initialize(db)

            try:
                await self.client.sign_in(phone=phone, code=code, phone_code_hash=getattr(self, 'phone_code_hash', None))
            except Exception as e:
                if "SessionPasswordNeeded" in str(type(e)) and password_2fa:
                    await self.client.sign_in(password=password_2fa)
                else:
                    raise e

            self.is_connected = True
            return {"success": True, "message": "Autenticazione Telegram completata con successo! Account connesso."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sync_channel_live(self, db: Session, channel_identifier: str = None, limit: int = 25) -> dict:
        """
        Scarica e importa direttamente le ultime offerte dal canale Telegram autorizzato con foto HD originali.
        """
        api_id_raw = self.get_setting(db, "telegram_api_id")
        api_id = int(api_id_raw) if api_id_raw and str(api_id_raw).strip().isdigit() else 31327962
        api_hash = self.get_setting(db, "telegram_api_hash") or "aa62f6773d556234f4b5812a1f7208d1"
        
        session_path = self._get_session_path()
        if not self.client:
            self.client = TelegramClient(session_path, api_id, api_hash)
        if not self.client.is_connected():
            await self.client.connect()

        if not await self.client.is_user_authorized():
            return {"success": False, "error": "Account Telegram non autorizzato. Completa il login."}

        target = channel_identifier or self.get_setting(db, "active_telegram_channel", "Articoli Addicted")
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        screenshots_dir = os.path.join(base_dir, "data", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        entity = None
        # Cerca nei dialoghi
        async for dialog in self.client.iter_dialogs():
            if "articoli" in dialog.name.lower() or "addicted" in dialog.name.lower():
                entity = dialog.entity
                break
        
        if not entity:
            try:
                entity = await self.client.get_entity('https://t.me/+bJVdSCzoIygwODE0')
            except Exception as e:
                return {"success": False, "error": f"Impossibile trovare il canale: {e}"}

        imported_count = 0
        async for message in self.client.iter_messages(entity, limit=limit):
            raw_text = (message.text or "").strip()
            if not raw_text and not message.media:
                continue

            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]

            # 1. Foto
            photo_url = None
            if message.media:
                photo_filename = f"tg_offer_{message.id}.jpg"
                photo_path = os.path.join(screenshots_dir, photo_filename)
                if not os.path.exists(photo_path):
                    await self.client.download_media(message, file=photo_path)
                photo_url = f"/screenshots/{photo_filename}"
            else:
                photo_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

            # 2. Venditore
            seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw_text)
            seller_contact = "@alex8700"
            if seller_match:
                seller_contact = f"@{seller_match[0]}"

            # 3. Condizioni Spesa & Rimborso
            price_info = "100% rimborso"
            for line in lines:
                if any(w in line.lower() for w in ['paga', 'costo', 'euro', '€', 'tasse', '100%', 'rimborso', 'feedback']):
                    price_info = line
                    break

            taxes_covered = True
            if any(w in raw_text.lower() for w in ['tasse forse', 'tasse a parte', 'no tasse', 'tasse non coperte', 'forse']):
                taxes_covered = False

            # 4. Titolo
            title = ""
            for line in lines:
                clean_l = re.sub(r'https?://\S+', '', line)
                clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
                if len(clean_l) > 6 and not any(w in clean_l.lower() for w in ['contattare', 'paga', 'euro', 'tasse', '100%']):
                    title = clean_l
                    break
            if not title and lines:
                title = lines[0][:80]
            if not title:
                title = f"Articolo Offerta #{message.id}"

            msg_date = message.date.replace(tzinfo=None) if message.date else datetime.utcnow()

            existing = db.query(Offer).filter_by(message_id=str(message.id)).first()
            if not existing:
                off = Offer(
                    title=title,
                    price_info=price_info,
                    seller_contact=seller_contact,
                    image_url=photo_url,
                    refund_pct=100.0,
                    taxes_covered=taxes_covered,
                    channel_name="Articoli Addicted",
                    message_id=str(message.id),
                    status="new",
                    created_at=msg_date
                )
                db.add(off)
                imported_count += 1
            else:
                existing.created_at = msg_date

        if imported_count > 0:
            log = ActivityLog(
                action_type="CHANNEL_SYNC",
                title="Sincronizzazione Canale Articoli Addicted",
                details=f"Scaricate {imported_count} nuove offerte live con foto originali e venditori."
            )
            db.add(log)
            db.commit()

        return {
            "success": True,
            "count": imported_count,
            "message": f"Sincronizzazione completata: {imported_count} nuove offerte importate da Articoli Addicted!"
        }

    async def _ensure_connected_client(self, db: Session):
        api_id_raw = self.get_setting(db, "telegram_api_id")
        api_id = int(api_id_raw) if api_id_raw and str(api_id_raw).strip().isdigit() else 31327962
        api_hash = self.get_setting(db, "telegram_api_hash") or "aa62f6773d556234f4b5812a1f7208d1"
        
        session_path = self._get_session_path()
        if not self.client:
            self.client = TelegramClient(session_path, api_id, api_hash)
        if not self.client.is_connected():
            await self.client.connect()
        return self.client

    async def send_availability_request(self, db: Session, offer: Offer, recipient: str = None) -> dict:
        """
        Invia la richiesta di disponibilità per un prodotto (BLOCCATO IN SICUREZZA SU 'me' / Messaggi Salvati).
        """
        # BLOCCO DI SICUREZZA: Invia SOLO ed esclusivamente a 'me' (Messaggi Salvati dell'utente)
        target_contact = "me"
        
        message_text = f"Ciao! Volevo chiederti se è ancora disponibile questo articolo:\n\n📦 *{offer.title}*\n💶 Condizioni: {offer.price_info or '100% rimborso'}\n\n(Destinatario originale: {offer.seller_contact or '@venditore'})\nGrazie!"

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "error": "Account Telegram non autorizzato."}

            # Trova l'immagine del prodotto se presente sul disco
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = os.path.basename(offer.image_url or "")
            file_path = os.path.join(base_dir, "data", "screenshots", filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                await client.send_file(target_contact, file_path, caption=message_text)
            else:
                await client.send_message(target_contact, message_text)
            
            log = ActivityLog(
                action_type="MESSAGE_SENT",
                title=f"Richiesta con foto inviata ai tuoi Messaggi Salvati",
                details=f"Articolo: {offer.title[:40]} | Venditore originale: {offer.seller_contact}"
            )
            db.add(log)
            offer.status = "requested"
            db.commit()
            return {"success": True, "mode": "safe_simulation", "message": "Richiesta con foto inviata ai tuoi Messaggi Salvati su Telegram (Venditori reali disattivati)."}
        except Exception as e:
            print(f"[Telegram Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_order_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia lo screenshot di conferma ordine e il numero d'ordine (BLOCCATO IN SICUREZZA SU 'me' / Messaggi Salvati).
        """
        # BLOCCO DI SICUREZZA: Invia SOLO ed esclusivamente a 'me' (Messaggi Salvati dell'utente)
        target_contact = "me"
        
        caption_text = f"Ecco lo screenshot della conferma d'ordine per *{order.product_title}*:\n\nNumero Ordine: `{order.order_number}`\n(Destinatario originale: {order.seller_contact or '@venditore'})"

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "error": "Account Telegram non autorizzato."}

            # Trova il file dello screenshot sul disco
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = os.path.basename(order.confirmation_screen_url or "")
            file_path = os.path.join(base_dir, "data", "screenshots", filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                await client.send_file(target_contact, file_path, caption=caption_text)
            else:
                await client.send_message(target_contact, caption_text)

            log = ActivityLog(
                action_type="SCREEN_SENT",
                title=f"Screenshot di test inviato ai tuoi Messaggi Salvati",
                details=f"Ordine: {order.order_number} | Venditore originale: {order.seller_contact}"
            )
            db.add(log)
            order.status = "waiting_review"
            order.confirmation_sent_at = datetime.utcnow()
            db.commit()
            return {"success": True, "mode": "safe_simulation", "message": "Screenshot inviato ai tuoi Messaggi Salvati su Telegram (Venditori reali disattivati)."}
        except Exception as e:
            print(f"[Telegram Screen Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_review_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia la conferma della recensione pubblicata con immagine screenshot (BLOCCATO IN SICUREZZA SU 'me' / Messaggi Salvati).
        """
        target_contact = "me"
        caption_text = f"Ciao! La recensione a 5 stelle per l'ordine `{order.order_number}` (*{order.product_title}*) è stata pubblicata su Amazon.\nIn allegato lo screenshot per procedere al rimborso PayPal. Grazie!\n(Destinatario originale: {order.seller_contact or '@venditore'})"

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "error": "Account Telegram non autorizzato."}

            from app.screenshot_service import generate_amazon_review_screenshot
            review_url = order.review_screen_url
            if not review_url:
                review_url = generate_amazon_review_screenshot(
                    order_number=order.order_number,
                    product_title=order.product_title,
                    review_title=order.review_title or "Ottimo prodotto, spedizione impeccabile",
                    review_body=order.review_body or "Arrivato puntuale, ben imballato. Qualità dei materiali ottima e facilissimo da utilizzare. Pienamente soddisfatto!"
                )
                order.review_screen_url = review_url
                db.commit()

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = os.path.basename(review_url or "")
            file_path = os.path.join(base_dir, "data", "screenshots", filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                await client.send_file(target_contact, file_path, caption=caption_text)
            else:
                await client.send_message(target_contact, caption_text)
            
            log = ActivityLog(
                action_type="REVIEW_READY",
                title=f"Screenshot recensione inviato ai tuoi Messaggi Salvati",
                details=f"Ordine: {order.order_number} | Prodotto: {order.product_title[:40]}"
            )
            db.add(log)
            order.status = "review_submitted"
            order.review_sent_to_seller_at = datetime.utcnow()
            db.commit()
            return {"success": True, "mode": "safe_simulation", "message": "Screenshot recensione inviato ai tuoi Messaggi Salvati!"}
        except Exception as e:
            print(f"[Telegram Review Send Error] {e}")
            return {"success": False, "error": str(e)}

telegram_service = TelegramManager()
