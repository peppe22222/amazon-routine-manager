import os
import re
import html
import base64
import asyncio
import requests
from datetime import datetime
from collections import OrderedDict
from PIL import Image
from telethon import TelegramClient, events
from sqlalchemy.orm import Session
from app.database import Setting, ActivityLog, Order, Offer

def create_album_collage(image_paths: list, output_path: str):
    """Unisce più foto di uno stesso album Telegram in un'unica immagine collage pulita ad alta risoluzione"""
    if not image_paths or len(image_paths) <= 1:
        return
    try:
        imgs = []
        for p in image_paths:
            if os.path.exists(p):
                try:
                    imgs.append(Image.open(p).convert("RGB"))
                except Exception:
                    pass
        if not imgs:
            return

        target_w, target_h = 450, 450
        resized = []
        for im in imgs:
            im.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            bg = Image.new("RGB", (target_w, target_h), (10, 15, 29))
            offset_x = (target_w - im.width) // 2
            offset_y = (target_h - im.height) // 2
            bg.paste(im, (offset_x, offset_y))
            resized.append(bg)

        if len(resized) == 2:
            collage = Image.new("RGB", (target_w * 2, target_h), (10, 15, 29))
            collage.paste(resized[0], (0, 0))
            collage.paste(resized[1], (target_w, 0))
        elif len(resized) == 3:
            collage = Image.new("RGB", (target_w * 3, target_h), (10, 15, 29))
            collage.paste(resized[0], (0, 0))
            collage.paste(resized[1], (target_w, 0))
            collage.paste(resized[2], (target_w * 2, 0))
        else:
            collage = Image.new("RGB", (target_w * 2, target_h * 2), (10, 15, 29))
            collage.paste(resized[0], (0, 0))
            collage.paste(resized[1], (target_w, 0))
            collage.paste(resized[2], (0, target_h))
            collage.paste(resized[3] if len(resized) > 3 else resized[0], (target_w, target_h))

        collage.save(output_path, "JPEG", quality=90)
    except Exception as e:
        print(f"[Collage create error] {e}")

def extract_title_with_ai(image_path: str, gemini_key: str) -> str:
    """Utilizza Gemini Vision per estrarre il nome esatto del prodotto visibile sulla confezione/immagine"""
    if not gemini_key or not os.path.exists(image_path):
        return ""
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Leggi l'immagine del prodotto ed estrai il nome esatto del prodotto e la marca visibili sull'oggetto o confezione (es: 'Venalux Crema Vene Varicose', 'Diffusore Aromi Ultrasuoni'). Rispondi SOLO con il nome del prodotto in italiano (max 5-7 parole), senza commenti."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        r = requests.post(url, json=payload, timeout=6)
        if r.status_code == 200:
            data = r.json()
            txt = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if txt and len(txt) > 2:
                return txt
    except Exception as e:
        print(f"[AI Vision extract error] {e}")
    return ""

def clean_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def scrape_telegram_channel_offers(channel_identifier: str, limit: int = 20) -> list:
    """
    Scarica e analizza i post più recenti da un canale pubblico Telegram tramite l'anteprima web (https://t.me/s/...)
    Ignora messaggi/foto orfane senza testo per evitare duplicati da album.
    """
    clean = channel_identifier.strip().lstrip('@')
    clean = clean.replace("https://t.me/s/", "").replace("https://t.me/", "").strip("/")
    
    if not clean or clean.startswith("+"):
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
        message_blocks = re.findall(r'<div class="tgme_widget_message\b[^>]*>(.*?)<div class="tgme_widget_message_footer\b', page_html, re.DOTALL)
        
        offers_found = []
        for block in message_blocks[-limit:]:
            # 1. Estrazione Testo
            text_match = re.search(r'<div class="tgme_widget_message_text\b[^>]*>(.*?)</div>', block, re.DOTALL)
            raw_text = clean_html_text(text_match.group(1)) if text_match else ""

            # FILTRO CRITICO ALBUM: Se un messaggio non ha testo, è una foto secondaria di un album -> NON creare una card separata!
            if not raw_text or len(raw_text.strip()) < 3:
                continue

            # 2. Estrazione Foto
            img_match = re.search(r'background-image:url\([\'"]?(https?://[^\'")]+)[\'"]?\)', block)
            if not img_match:
                img_match = re.search(r'src=[\'"]?(https?://[^\'">\s]+)[\'"]?', block)
            img_url = img_match.group(1) if img_match else None

            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

            # 3. Estrazione Contatto Venditore
            seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw_text)
            seller_contact = "@alex8700"
            if seller_match:
                for cand in seller_match:
                    if cand.lower() != clean.lower():
                        seller_contact = f"@{cand}"
                        break

            # 4. Estrazione Intelligente di Tutti i Prodotti e delle Condizioni
            item_lines = []
            condition_lines = []
            
            for line in lines:
                clean_l = re.sub(r'https?://\S+', '', line)
                clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
                if not clean_l:
                    continue
                l_lower = clean_l.lower()
                is_condition = any(w in l_lower for w in ['paga', 'costo', 'euro', '€', 'tasse', '100%', 'rimborso', 'feedback', 'recensione', 'contattare', 'disponibilit', 'pm per link'])
                if is_condition:
                    condition_lines.append(clean_l)
                else:
                    if len(clean_l) >= 2:
                        item_lines.append(clean_l)

            # Titolo: unione di tutti i prodotti elencati
            if len(item_lines) > 1:
                title = " • ".join(item_lines)
            elif len(item_lines) == 1:
                title = item_lines[0]
            else:
                continue # Salta i blocchi senza prodotti

            # Condizioni di spesa e rimborso
            if condition_lines:
                price_info = " • ".join(condition_lines)
            else:
                price_info = "100% rimborso"

            taxes_covered = True
            if any(w in raw_text.lower() for w in ["tasse forse", "tasse a parte", "no tasse", "tasse non coperte", "forse"]):
                taxes_covered = False

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

        # Pulisci le vecchie offerte 'new' non ancora elaborate per sostituirle con quelle unificate
        db.query(Offer).filter(Offer.status == "new").delete()
        db.commit()

        # Raccogli tutti i messaggi recenti
        raw_messages = []
        async for message in self.client.iter_messages(entity, limit=limit):
            raw_messages.append(message)

        # Raggruppa i messaggi per album (grouped_id) in modo che 4 foto con 1 testo diventino 1 singola offerta
        album_groups = OrderedDict()
        for m in raw_messages:
            key = f"album_{m.grouped_id}" if m.grouped_id else f"single_{m.id}"
            if key not in album_groups:
                album_groups[key] = []
            album_groups[key].append(m)

        imported_count = 0
        for key, msgs in album_groups.items():
            # Trova il messaggio che contiene il testo con i nomi dei prodotti e condizioni
            raw_text = ""
            primary_msg = msgs[0]
            for m in msgs:
                if m.text and m.text.strip():
                    raw_text = m.text.strip()
                    primary_msg = m
                    break

            if not raw_text and not any(m.media for m in msgs):
                continue

            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]

            # Scarica tutte le foto dell'album/post
            downloaded_photos = []
            for m in msgs:
                if m.media:
                    fn = f"tg_offer_{m.id}.jpg"
                    fp = os.path.join(screenshots_dir, fn)
                    if not os.path.exists(fp):
                        try:
                            await self.client.download_media(m, file=fp)
                        except Exception:
                            pass
                    if os.path.exists(fp):
                        downloaded_photos.append(fp)

            photo_url = None
            if len(downloaded_photos) > 1:
                collage_fn = f"tg_album_{key}.jpg"
                collage_fp = os.path.join(screenshots_dir, collage_fn)
                create_album_collage(downloaded_photos, collage_fp)
                if os.path.exists(collage_fp):
                    photo_url = f"/screenshots/{collage_fn}"
                else:
                    photo_url = f"/screenshots/{os.path.basename(downloaded_photos[0])}"
            elif len(downloaded_photos) == 1:
                photo_url = f"/screenshots/{os.path.basename(downloaded_photos[0])}"
            else:
                photo_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

            # Venditore
            seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw_text)
            seller_contact = "@alex8700"
            if seller_match:
                seller_contact = f"@{seller_match[0]}"

            # Estrazione Prodotti & Condizioni
            item_lines = []
            condition_lines = []
            
            for line in lines:
                clean_l = re.sub(r'https?://\S+', '', line)
                clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
                if not clean_l:
                    continue
                l_lower = clean_l.lower()
                is_condition = any(w in l_lower for w in ['paga', 'costo', 'euro', '€', 'tasse', '100%', 'rimborso', 'feedback', 'recensione', 'contattare', 'disponibilit', 'pm per link'])
                if is_condition:
                    condition_lines.append(clean_l)
                else:
                    if len(clean_l) >= 2:
                        item_lines.append(clean_l)

            # Titolo: unione di tutti i prodotti elencati (es: Shampoo solido • Fondotinta • Rossetto • Siero effetto lifting)
            if len(item_lines) > 1:
                title = " • ".join(item_lines)
            elif len(item_lines) == 1:
                title = item_lines[0]
            else:
                continue # Salta i messaggi senza elenco prodotti per evitare doppioni

            # Condizioni di spesa e rimborso
            if condition_lines:
                price_info = " • ".join(condition_lines)
            else:
                price_info = "100% rimborso"

            taxes_covered = True
            if any(w in raw_text.lower() for w in ['tasse forse', 'tasse a parte', 'no tasse', 'tasse non coperte', 'forse']):
                taxes_covered = False

            msg_date = primary_msg.date.replace(tzinfo=None) if primary_msg.date else datetime.utcnow()

            off = Offer(
                title=title,
                price_info=price_info,
                seller_contact=seller_contact,
                image_url=photo_url,
                refund_pct=100.0,
                taxes_covered=taxes_covered,
                channel_name="Articoli Addicted",
                message_id=str(primary_msg.id),
                status="new",
                created_at=msg_date
            )
            db.add(off)
            imported_count += 1

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
        
        message_text = f"Ciao Alex! Volevo chiederti se è ancora disponibile questo articolo:\n\n📦 *{offer.title}*\n💶 Condizioni: {offer.price_info or '100% rimborso'}\n\nGrazie!"

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
                details=f"Articolo: {offer.title[:40]}"
            )
            db.add(log)
            offer.status = "requested"
            db.commit()
            return {"success": True, "mode": "safe_simulation", "message": "Richiesta con foto inviata ai tuoi Messaggi Salvati su Telegram."}
        except Exception as e:
            print(f"[Telegram Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_order_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia lo screenshot di conferma ordine e il numero d'ordine (BLOCCATO IN SICUREZZA SU 'me' / Messaggi Salvati).
        """
        # BLOCCO DI SICUREZZA: Invia SOLO ed esclusivamente a 'me' (Messaggi Salvati dell'utente)
        target_contact = "me"
        
        caption_text = f"Ciao Alex, ecco lo screenshot della conferma d'ordine per *{order.product_title}*:\n\nNumero Ordine: `{order.order_number}`\nGrazie!"

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
                title=f"Screenshot inviato ai tuoi Messaggi Salvati",
                details=f"Ordine: {order.order_number}"
            )
            db.add(log)
            order.status = "waiting_review"
            order.confirmation_sent_at = datetime.utcnow()
            db.commit()
            return {"success": True, "mode": "safe_simulation", "message": "Screenshot inviato ai tuoi Messaggi Salvati su Telegram."}
        except Exception as e:
            print(f"[Telegram Screen Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_review_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia la conferma della recensione pubblicata con immagine screenshot (BLOCCATO IN SICUREZZA SU 'me' / Messaggi Salvati).
        """
        target_contact = "me"
        caption_text = f"Ciao Alex! La recensione a 5 stelle per l'ordine `{order.order_number}` (*{order.product_title}*) è stata pubblicata su Amazon.\nIn allegato lo screenshot per procedere al rimborso PayPal. Grazie!"

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
