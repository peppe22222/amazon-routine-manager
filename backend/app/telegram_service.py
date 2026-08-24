import os
import re
import html
import base64
import asyncio
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import OrderedDict
from PIL import Image
from telethon import TelegramClient, events, errors
from sqlalchemy.orm import Session
from sqlalchemy import or_
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

def normalize_text_key(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = [w for w in clean.split() if len(w) > 1 and w not in [
        'per', 'con', 'del', 'della', 'delle', 'dei', 'degli', 'in', 'da', 'su', 'il', 'la', 'le', 'lo', 'gli', 
        'un', 'una', 'uno', 'euro', 'tasse', 'forse', 'coperte', 'rimborso', 'feedback', 'recensione', 'prodotto', 'articolo', 'offerta'
    ]]
    return " ".join(words)

def get_product_dedup_key(title: str) -> str:
    """Restituisce una chiave univoca normalizzata per raggruppare lo stesso identico prodotto"""
    if not title:
        return ""
    norm = normalize_text_key(title)
    words = norm.split()
    if not words:
        return re.sub(r'[^a-z0-9]', '', title.lower())
    return "_".join(words[:5])

def is_title_duplicate(title1: str, title2: str) -> bool:
    if not title1 or not title2:
        return False
    t1 = title1.strip().lower()
    t2 = title2.strip().lower()
    if t1 == t2:
        return True
    k1 = normalize_text_key(title1)
    k2 = normalize_text_key(title2)
    if k1 and k2 and k1 == k2:
        return True
    return False

def clean_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def scrape_telegram_channel_offers(channel_identifier: str, limit: int = 300) -> list:
    """
    Scarica e analizza tutti i post recenti da un canale pubblico Telegram tramite l'anteprima web (https://t.me/s/...)
    Supporta la paginazione all'indietro per estrarre fino a 'limit' messaggi completi con foto e contatti.
    """
    clean = channel_identifier.strip().lstrip('@')
    clean = clean.replace("https://t.me/s/", "").replace("https://t.me/", "").strip("/")
    
    if not clean or clean.startswith("+"):
        return []

    base_url = f"https://t.me/s/{clean}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    all_message_blocks = []
    seen_post_ids = set()
    current_url = base_url
    max_pages = 15 # Fino a 15 pagine di ~20 messaggi = ~300 messaggi

    for page in range(max_pages):
        try:
            resp = requests.get(current_url, headers=headers, timeout=12)
            if resp.status_code != 200:
                break
                
            page_html = resp.text
            blocks = re.findall(r'(<div class="tgme_widget_message\b[^>]*>.*?<div class="tgme_widget_message_footer\b)', page_html, re.DOTALL)
            if not blocks:
                break
                
            new_blocks_in_page = 0
            min_post_id = None
            
            for b in blocks:
                dp = re.search(r'data-post=[\'"][^/\'"]+/(\d+)[\'"]', b)
                if dp:
                    pid = int(dp.group(1))
                    if min_post_id is None or pid < min_post_id:
                        min_post_id = pid
                    if pid not in seen_post_ids:
                        seen_post_ids.add(pid)
                        all_message_blocks.append(b)
                        new_blocks_in_page += 1
                else:
                    all_message_blocks.append(b)
                    new_blocks_in_page += 1

            if len(all_message_blocks) >= limit or new_blocks_in_page == 0 or min_post_id is None:
                break
                
            # Pagina successiva verso i messaggi precedenti
            current_url = f"{base_url}?before={min_post_id}"
        except Exception as e:
            print(f"[Scraper Page {page} Error] {e}")
            break

    if not all_message_blocks:
        return []

    offers_found = []
    seen_msg_ids = set()
    
    # Processa i blocchi dal più recente al più vecchio
    for block in all_message_blocks:
        # Estrazione message_id da data-post
        msg_id = None
        data_post_match = re.search(r'data-post=[\'"][^/\'"]+/(\d+)[\'"]', block)
        if data_post_match:
            msg_id = data_post_match.group(1)

        # 1. Estrazione Testo
        text_match = re.search(r'<div class="tgme_widget_message_text\b[^>]*>(.*?)</div>', block, re.DOTALL)
        raw_text = clean_html_text(text_match.group(1)) if text_match else ""

        # 2. Estrazione Foto
        img_match = re.search(r'background-image:url\([\'"]?(https?://[^\'")]+)[\'"]?\)', block)
        if not img_match:
            img_match = re.search(r'src=[\'"]?(https?://[^\'">\s]+)[\'"]?', block)
        img_url = img_match.group(1) if img_match else None

        # Se non c'è né testo né foto valida, salta
        if not raw_text and not img_url:
            continue

        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

        # 3. Estrazione Contatto Venditore
        seller_match = re.findall(r'@([a-zA-Z0-9_]{3,32})', raw_text)
        seller_contact = "@alex8700"
        if seller_match:
            for cand in seller_match:
                if cand.lower() not in [clean.lower(), "articoliaddicted", "channel", "canale"]:
                    seller_contact = f"@{cand}"
                    break

        # 4. Estrazione Intelligente di Titolo e Condizioni
        item_lines = []
        condition_lines = []
        
        for line in lines:
            clean_l = re.sub(r'https?://\S+', '', line)
            clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
            if not clean_l:
                continue
            l_lower = clean_l.lower()
            is_condition = bool(
                re.search(r'(?:si paga|paga|paghi|costo|spesa|rimborso|tasse|feedback|recensione|contattare|disponibilit|pm per|per link)\b', l_lower)
                or re.search(r'^\s*\d+\s*(?:€|euro|%)\b', l_lower)
            )
            if is_condition:
                condition_lines.append(clean_l)
            else:
                if len(clean_l) >= 2:
                    item_lines.append(clean_l)

        # Titolo robusto
        if len(item_lines) > 1:
            title = " • ".join(item_lines)
        elif len(item_lines) == 1:
            title = item_lines[0]
        elif lines:
            first_clean = re.sub(r'https?://\S+', '', lines[0])
            first_clean = re.sub(r'@[a-zA-Z0-9_]+', '', first_clean).strip()
            title = first_clean if len(first_clean) >= 4 else (f"Offerta Canale Telegram #{msg_id}" if msg_id else "Prodotto in Offerta")
        else:
            title = f"Offerta Canale Telegram #{msg_id}" if msg_id else "Prodotto in Offerta"

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

        # Evita duplicati solo se lo stesso identico message_id è già stato visto nel batch
        if msg_id and msg_id in seen_msg_ids:
            continue
        if msg_id:
            seen_msg_ids.add(msg_id)

        offers_found.append({
            "title": title,
            "price_info": price_info,
            "seller_contact": seller_contact,
            "image_url": img_url,
            "taxes_covered": taxes_covered,
            "raw_text": raw_text,
            "message_id": msg_id
        })

    return offers_found

from telethon.sessions import StringSession

_global_telethon_client = None

class TelegramManager:
    def __init__(self):
        self.is_connected = False
        self.phone_code_hash = None
        self.last_auth_phone = None

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

    def _cleanup_session(self, db: Session = None):
        global _global_telethon_client
        if _global_telethon_client:
            try:
                if _global_telethon_client.is_connected():
                    _global_telethon_client.disconnect()
            except Exception:
                pass
        _global_telethon_client = None
        self.is_connected = False
        if db:
            s = db.query(Setting).filter_by(key="telegram_session_string").first()
            if s:
                s.value = ""
                db.commit()

    async def _ensure_connected_client(self, db: Session):
        global _global_telethon_client
        current_loop = asyncio.get_running_loop()
        
        # Se il client globale appartiene a un loop asyncio precedente o chiuso, resettalo
        if _global_telethon_client is not None:
            client_loop = getattr(_global_telethon_client, '_loop', None) or getattr(_global_telethon_client, 'loop', None)
            if client_loop != current_loop or (client_loop and client_loop.is_closed()):
                _global_telethon_client = None

        api_id_raw = self.get_setting(db, "telegram_api_id")
        api_id = int(api_id_raw) if api_id_raw and str(api_id_raw).strip().isdigit() else 31327962
        api_hash = self.get_setting(db, "telegram_api_hash") or "aa62f6773d556234f4b5812a1f7208d1"
        
        # Recupera la sessione permanente salvata (da Env o da Database)
        env_session = os.getenv("TELEGRAM_SESSION_STRING", "").strip()
        db_session = self.get_setting(db, "telegram_session_string", "").strip()
        session_str = env_session or db_session or ""
        
        if _global_telethon_client is None:
            string_session = StringSession(session_str)
            _global_telethon_client = TelegramClient(string_session, api_id, api_hash, loop=current_loop)
            
        if not _global_telethon_client.is_connected():
            try:
                await _global_telethon_client.connect()
            except (errors.AuthKeyDuplicatedError, errors.AuthKeyUnregisteredError, errors.SessionRevokedError) as e:
                print(f"[Telethon Session Error] {e} - Reset sessione non valida.")
                self._cleanup_session(db)
                _global_telethon_client = TelegramClient(StringSession(""), api_id, api_hash, loop=current_loop)
                await _global_telethon_client.connect()
        return _global_telethon_client

    async def initialize(self, db: Session):
        try:
            client = await self._ensure_connected_client(db)
            if await client.is_user_authorized():
                self.is_connected = True
                print("[Telegram Service] Connesso con successo all'account Telegram!")
                return {"status": "connected", "message": "Connesso all'account Telegram."}
            else:
                self.is_connected = False
                return {"status": "auth_required", "message": "Autenticazione richiesta. Collega il tuo account Telegram con il tuo numero di telefono."}
        except Exception as e:
            print(f"[Telegram Service] Errore di connessione: {e}")
            self.is_connected = False
            return {"status": "error", "message": str(e)}

    async def get_auth_status(self, db: Session) -> dict:
        try:
            client = await self._ensure_connected_client(db)
            if not client or not client.is_connected():
                return {"success": True, "is_authorized": False, "status": "disconnected", "message": "Non connesso"}
            
            is_auth = await client.is_user_authorized()
            if is_auth:
                me = await client.get_me()
                phone = getattr(me, 'phone', '') or self.get_setting(db, 'telegram_phone', '')
                first_name = getattr(me, 'first_name', '') or ''
                username = getattr(me, 'username', '') or ''
                
                # Assicura che la stringa sia salvata nel db
                saved_str = self.get_setting(db, 'telegram_session_string', '')
                if not saved_str:
                    try:
                        saved_str = client.session.save()
                        s = db.query(Setting).filter_by(key="telegram_session_string").first()
                        if s:
                            s.value = saved_str
                        else:
                            db.add(Setting(key="telegram_session_string", value=saved_str))
                        db.commit()
                    except Exception:
                        pass

                return {
                    "success": True,
                    "is_authorized": True,
                    "status": "connected",
                    "session_string": saved_str,
                    "user": {
                        "first_name": first_name,
                        "username": f"@{username}" if username else "",
                        "phone": f"+{phone}" if phone and not phone.startswith("+") else phone
                    }
                }
            else:
                return {
                    "success": True,
                    "is_authorized": False,
                    "status": "auth_required",
                    "phone": self.get_setting(db, 'telegram_phone', ''),
                    "message": "Autenticazione richiesta"
                }
        except Exception as e:
            print(f"[Telegram Status Error] {e}")
            return {
                "success": False,
                "is_authorized": False,
                "status": "error",
                "error": str(e)
            }

    async def send_auth_code(self, db: Session, phone: str = None) -> dict:
        if phone:
            phone = phone.strip()
            s = db.query(Setting).filter_by(key="telegram_phone").first()
            if s:
                s.value = phone
            else:
                db.add(Setting(key="telegram_phone", value=phone))
            db.commit()
        else:
            phone = self.get_setting(db, "telegram_phone")

        if not phone:
            return {"success": False, "error": "Inserisci il tuo numero di telefono Telegram (es. +393331234567)"}

        try:
            client = await self._ensure_connected_client(db)
            if await client.is_user_authorized():
                self.is_connected = True
                return {"success": True, "status": "already_authorized", "message": "Account Telegram già autorizzato e connesso!"}

            code_obj = await client.send_code_request(phone)
            self.phone_code_hash = code_obj.phone_code_hash
            self.last_auth_phone = phone
            return {
                "success": True,
                "status": "code_sent",
                "phone": phone,
                "message": f"Codice di verifica Telegram inviato a {phone}! Controlla l'app Telegram o gli SMS."
            }
        except Exception as e:
            print(f"[Telegram Send Code Error] {e}")
            return {"success": False, "error": str(e)}

    async def verify_auth_code(self, db: Session, code: str, password_2fa: str = None) -> dict:
        phone = getattr(self, 'last_auth_phone', None) or self.get_setting(db, "telegram_phone")
        phone_code_hash = getattr(self, 'phone_code_hash', None)
        try:
            client = await self._ensure_connected_client(db)
            try:
                await client.sign_in(phone=phone, code=code.strip(), phone_code_hash=phone_code_hash)
            except Exception as e:
                if "SessionPasswordNeeded" in str(type(e)) or "2FA" in str(e):
                    if password_2fa:
                        await client.sign_in(password=password_2fa.strip())
                    else:
                        return {"success": False, "requires_2fa": True, "error": "Questo account richiede la Password 2FA di Telegram."}
                else:
                    raise e

            self.is_connected = True
            
            # Salva la chiave di sessione permanente nel database
            try:
                saved_str = client.session.save()
                s = db.query(Setting).filter_by(key="telegram_session_string").first()
                if s:
                    s.value = saved_str
                else:
                    db.add(Setting(key="telegram_session_string", value=saved_str))
                db.commit()
                print(f"[Telegram Service] StringSession permanente salvata con successo!")
            except Exception as se:
                print(f"[Telegram Session Save Error] {se}")

            me = await client.get_me()
            name = getattr(me, 'first_name', '')
            user_handle = f"@{me.username}" if getattr(me, 'username', '') else phone
            return {
                "success": True,
                "message": f"Accesso Telegram completato con successo! Connesso come {name} ({user_handle}).",
                "session_string": saved_str if 'saved_str' in locals() else "",
                "user": {"name": name, "handle": user_handle}
            }
        except Exception as e:
            print(f"[Telegram Verify Code Error] {e}")
            return {"success": False, "error": str(e)}

    async def logout(self, db: Session) -> dict:
        try:
            if self.client and self.client.is_connected():
                try:
                    await self.client.log_out()
                except Exception:
                    pass
        except Exception:
            pass
        self._cleanup_session()
        return {"success": True, "message": "Account Telegram disconnesso con successo."}

    async def sync_channel_live(self, db: Session, channel_identifier: str = None, limit: int = 500) -> dict:
        """
        Scarica e importa direttamente TUTTE le offerte dal canale Telegram autorizzato con foto HD originali.
        """
        client = await self._ensure_connected_client(db)
        if not await client.is_user_authorized():
            return {
                "success": False,
                "auth_required": True,
                "error": "Account Telegram non collegato. Accedi con il tuo numero di telefono nelle Impostazioni per sincronizzare il canale."
            }

        target = channel_identifier or self.get_setting(db, "active_telegram_channel", "Articoli Addicted")
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        screenshots_dir = os.path.join(base_dir, "data", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        entity = None
        raw_target = (target or "").strip()
        clean_target = re.sub(r'[^a-zA-Z0-9]', '', raw_target).lower()

        # 1. Cerca nei dialoghi/canali dell'utente
        dialog_entities = []
        try:
            async for dialog in client.iter_dialogs():
                dialog_entities.append((dialog.name, dialog.entity))
        except Exception as e:
            print(f"[iter_dialogs error] {e}")

        for d_name, d_ent in dialog_entities:
            d_clean = re.sub(r'[^a-zA-Z0-9]', '', d_name).lower()
            if clean_target and clean_target not in ["canaleoffertetest", "test"] and (clean_target in d_clean or d_clean in clean_target):
                entity = d_ent
                break

        if not entity:
            for d_name, d_ent in dialog_entities:
                d_lower = d_name.lower()
                if "articoli" in d_lower and "addicted" in d_lower:
                    entity = d_ent
                    break
                elif "articoli" in d_lower or "addicted" in d_lower:
                    entity = d_ent
                    break

        if not entity:
            # Check by known IDs or invite links
            for cand in [-1001273415420, 'https://t.me/+bJVdSCzoIygwODE0', '+bJVdSCzoIygwODE0', 'https://t.me/joinchat/bJVdSCzoIygwODE0']:
                try:
                    entity = await client.get_entity(cand)
                    if entity:
                        break
                except Exception:
                    pass

        if not entity:
            if raw_target.startswith("@") or "t.me/" in raw_target:
                try:
                    entity = await client.get_entity(raw_target)
                except Exception:
                    pass

        if not entity:
            return {
                "success": False,
                "error": f"Impossibile trovare il canale Telegram '{target}' tra i tuoi canali. Assicurati di essere iscritto al canale sul tuo account Telegram."
            }

        channel_title = getattr(entity, 'title', getattr(entity, 'username', 'Articoli Addicted'))

        # Raccogli tutti i messaggi recenti fino al limite
        raw_messages = []
        async for message in client.iter_messages(entity, limit=limit):
            raw_messages.append(message)

        if not raw_messages:
            return {
                "success": True,
                "count": 0,
                "message": f"Nessun messaggio recente rilevato nel canale '{channel_title}'."
            }

        # Raggruppa i messaggi per album (grouped_id) o per messaggio singolo
        # Inoltre accoppia messaggi adiacenti senza grouped_id (foto inviata subito prima o dopo il testo)
        album_groups = OrderedDict()
        
        # Ordina per ID crescente per raggruppamento temporale
        sorted_msgs = sorted(raw_messages, key=lambda m: m.id)
        
        i = 0
        while i < len(sorted_msgs):
            m = sorted_msgs[i]
            if m.grouped_id:
                key = f"album_{m.grouped_id}"
                if key not in album_groups:
                    album_groups[key] = []
                album_groups[key].append(m)
                i += 1
            else:
                # Controlla se il messaggio successivo è accoppiato (es. foto + testo o testo + foto entro 120s)
                has_next = (i + 1 < len(sorted_msgs))
                next_m = sorted_msgs[i + 1] if has_next else None
                
                is_paired = False
                if next_m and not next_m.grouped_id and m.date and next_m.date:
                    time_diff = abs((next_m.date - m.date).total_seconds())
                    if time_diff <= 120:
                        # Uno ha foto e l'altro ha testo
                        if (m.media and not m.text and next_m.text and not next_m.media) or \
                           (not m.media and m.text and next_m.media and not next_m.text):
                            key = f"pair_{m.id}_{next_m.id}"
                            album_groups[key] = [m, next_m]
                            is_paired = True
                            i += 2
                
                if not is_paired:
                    key = f"single_{m.id}"
                    album_groups[key] = [m]
                    i += 1

        # Carica tutte le offerte attive già presenti nel DB
        existing_active = db.query(Offer).filter(Offer.status != "dismissed").all()
        existing_active_msg_ids = set()
        for o in existing_active:
            if o.message_id:
                for mid in str(o.message_id).split(','):
                    if mid.strip():
                        existing_active_msg_ids.add(mid.strip())

        imported_count = 0
        batch_seen_msg_ids = set()
        
        for key, msgs in album_groups.items():
            all_msg_ids = [str(m.id) for m in msgs]
            
            # Salta solo se TUTTI i messaggi di questo post sono già presenti e ATTIVI nel DB
            if all(m_id in existing_active_msg_ids for m_id in all_msg_ids):
                continue

            # Estrai testo completo controllando raw_text, message e text
            raw_text = ""
            primary_msg = msgs[0]
            for m in msgs:
                txt = (getattr(m, 'raw_text', '') or getattr(m, 'message', '') or getattr(m, 'text', '') or "").strip()
                if txt:
                    raw_text = txt
                    primary_msg = m
                    break

            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]

            # Scarica tutte le foto dell'album/post
            downloaded_photos = []
            for m in msgs:
                if m.media:
                    fn = f"tg_offer_{m.id}.jpg"
                    fp = os.path.join(screenshots_dir, fn)
                    if not os.path.exists(fp) or os.path.getsize(fp) == 0:
                        try:
                            await client.download_media(m, file=fp)
                        except Exception:
                            pass
                    if os.path.exists(fp) and os.path.getsize(fp) > 0:
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
                for cand in seller_match:
                    if cand.lower() not in ["articoliaddicted", "articoli", "addicted", "channel", "canale"]:
                        seller_contact = f"@{cand}"
                        break

            # Estrazione Prodotti & Condizioni
            item_lines = []
            condition_lines = []
            
            for line in lines:
                clean_l = re.sub(r'https?://\S+', '', line)
                clean_l = re.sub(r'@[a-zA-Z0-9_]+', '', clean_l).strip()
                if not clean_l:
                    continue
                l_lower = clean_l.lower()
                is_condition = bool(
                    re.search(r'(?:si paga|paga|paghi|costo|spesa|rimborso|tasse|feedback|recensione|contattare|disponibilit|pm per|per link)\b', l_lower)
                    or re.search(r'^\s*\d+\s*(?:€|euro|%)\b', l_lower)
                )
                if is_condition:
                    condition_lines.append(clean_l)
                else:
                    if len(clean_l) >= 2:
                        item_lines.append(clean_l)

            # Titolo robusto
            if len(item_lines) > 1:
                title = " • ".join(item_lines)
            elif len(item_lines) == 1:
                title = item_lines[0]
            elif lines:
                first_clean = re.sub(r'https?://\S+', '', lines[0])
                first_clean = re.sub(r'@[a-zA-Z0-9_]+', '', first_clean).strip()
                title = first_clean if len(first_clean) >= 4 else f"Offerta Canale Telegram #{primary_msg.id}"
            else:
                title = f"Offerta Canale Telegram #{primary_msg.id}"

            # Condizioni di spesa e rimborso
            if condition_lines:
                price_info = " • ".join(condition_lines)
            else:
                price_info = "100% rimborso"

            taxes_covered = True
            if any(w in raw_text.lower() for w in ['tasse forse', 'tasse a parte', 'no tasse', 'tasse non coperte', 'forse']):
                taxes_covered = False

            msg_date = primary_msg.date.replace(tzinfo=None) if primary_msg.date else datetime.utcnow()

            # Evita duplicazione dello stesso messaggio nello stesso ciclo
            if any(mid in batch_seen_msg_ids for mid in all_msg_ids):
                continue
            for mid in all_msg_ids:
                batch_seen_msg_ids.add(mid)
                existing_active_msg_ids.add(mid)

            all_ids_str = ",".join(all_msg_ids)
            off = Offer(
                title=title,
                price_info=price_info,
                seller_contact=seller_contact,
                image_url=photo_url,
                refund_pct=100.0,
                taxes_covered=taxes_covered,
                channel_name=channel_title,
                message_id=all_ids_str,
                status="new",
                created_at=msg_date
            )
            db.add(off)
            imported_count += 1

        if imported_count > 0:
            log = ActivityLog(
                action_type="CHANNEL_SYNC",
                title=f"Sincronizzazione Canale {channel_title}",
                details=f"Scaricate con successo {imported_count} offerte complete con foto e contatti."
            )
            db.add(log)
            db.commit()
            self.prune_old_offers(db)

        return {
            "success": True,
            "count": imported_count,
            "message": f"Sincronizzazione completata: {imported_count} nuove offerte importate da {channel_title}!"
        }

    def prune_old_offers(self, db: Session, max_new_offers: int = 50):
        """
        Rimuove automaticamente gli articoli più vecchi in fondo alla lista con stato 'new'
        quando arrivano nuovi post, proteggendo sempre ordini e articoli già richiesti/acquistati.
        """
        try:
            s = db.query(Setting).filter_by(key="max_feed_offers").first()
            if s and s.value and s.value.isdigit():
                max_new_offers = max(20, int(s.value))
                
            orders = db.query(Order).filter(Order.status != "cancelled").all()
            unrequested = (
                db.query(Offer)
                .filter(Offer.status == "new")
                .order_by(desc(Offer.created_at), desc(Offer.id))
                .all()
            )
            
            to_keep = []
            to_prune = []
            for off in unrequested:
                if any(o.product_title and is_title_duplicate(off.title, o.product_title) for o in orders):
                    continue
                if len(to_keep) < max_new_offers:
                    to_keep.append(off)
                else:
                    to_prune.append(off)
                    
            if to_prune:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                screenshots_dir = os.path.join(base_dir, "data", "screenshots")
                for old_off in to_prune:
                    if old_off.image_url and old_off.image_url.startswith("/screenshots/tg_"):
                        fn = os.path.basename(old_off.image_url)
                        fp = os.path.join(screenshots_dir, fn)
                        if os.path.exists(fp):
                            try:
                                os.remove(fp)
                            except Exception:
                                pass
                    db.delete(old_off)
                db.commit()
        except Exception as e:
            print(f"[Prune Offers Error] {e}")

        return {
            "success": True,
            "count": imported_count,
            "message": f"Sincronizzazione completata: {imported_count} nuove offerte importate da {channel_title}!"
        }

    def _find_screenshot_file(self, screen_url_or_path: str) -> Optional[str]:
        if not screen_url_or_path:
            return None
        filename = os.path.basename(screen_url_or_path)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(base_dir, "data", "screenshots", filename),
            os.path.join(base_dir, "backend", "data", "screenshots", filename),
            os.path.join(os.getcwd(), "data", "screenshots", filename),
            os.path.join(os.getcwd(), "backend", "data", "screenshots", filename),
            screen_url_or_path
        ]
        for c in candidates:
            if os.path.exists(c) and os.path.isfile(c):
                return c
        return None

    async def send_availability_request(self, db: Session, offer: Offer, recipient: str = None) -> dict:
        """
        Invia la richiesta di disponibilità per un prodotto ad Alex (@alex8700 o contatto venditore).
        In modalità Sandbox (test_mode=true) invia il messaggio di prova a te stesso (Messaggi Salvati / 'me').
        """
        is_test = self.get_setting(db, "test_mode", "false").lower() == "true"
        target_contact = (recipient or offer.seller_contact or "@alex8700").strip()
        message_text = f"Ciao Alex! Volevo chiederti se è ancora disponibile questo articolo:\n\n📦 *{offer.title}*\n💶 Condizioni: {offer.price_info or '100% rimborso'}\n\nGrazie!"

        if is_test:
            try:
                client = await self._ensure_connected_client(db)
                if client and await client.is_user_authorized():
                    file_to_send = self._find_screenshot_file(offer.image_url) or (offer.image_url if offer.image_url and offer.image_url.startswith('http') else None)
                    test_notice = f"🧪 *[TEST SANDBOX - Copia per te]*\n(Nessun messaggio inviato ad Alex)\n\n{message_text}"
                    if file_to_send:
                        try:
                            await client.send_file('me', file_to_send, caption=test_notice)
                        except Exception:
                            await client.send_message('me', test_notice)
                    else:
                        await client.send_message('me', test_notice)
            except Exception as e:
                print(f"[Sandbox Send 'me' Error] {e}")

            log = ActivityLog(
                action_type="MESSAGE_SENT",
                title=f"Richiesta test inviata a me (Messaggi Salvati) [SANDBOX]",
                details=f"Articolo: {offer.title[:50]} (Inviato ai tuoi Messaggi Salvati Telegram per verifica)"
            )
            db.add(log)
            offer.status = "requested"
            db.commit()
            return {"success": True, "message": f"🧪 [SANDBOX] Messaggio di test inviato ai tuoi 'Messaggi Salvati' su Telegram (nessun messaggio inviato ad Alex)!"}

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "auth_required": True, "error": "Account Telegram non autorizzato. Collega il tuo numero in Impostazioni."}

            file_path = self._find_screenshot_file(offer.image_url)

            if file_path:
                await client.send_file(target_contact, file_path, caption=message_text)
            else:
                await client.send_message(target_contact, message_text)
            
            log = ActivityLog(
                action_type="MESSAGE_SENT",
                title=f"Richiesta inviata ad Alex ({target_contact})",
                details=f"Articolo: {offer.title[:50]}"
            )
            db.add(log)
            offer.status = "requested"
            db.commit()
            return {"success": True, "message": f"Richiesta inviata con successo ad Alex ({target_contact}) su Telegram!"}
        except Exception as e:
            print(f"[Telegram Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_order_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia lo screenshot di conferma ordine e il numero d'ordine ad Alex (@alex8700 o contatto venditore).
        In modalità Sandbox (test_mode=true) invia il messaggio di prova a te stesso (Messaggi Salvati / 'me').
        """
        is_test = self.get_setting(db, "test_mode", "false").lower() == "true"
        target_contact = (recipient or order.seller_contact or "@alex8700").strip()
        caption_text = f"Ciao Alex, ecco lo screenshot della conferma d'ordine per *{order.product_title}*:\n\nNumero Ordine: `{order.order_number}`\nGrazie!"

        if is_test:
            try:
                client = await self._ensure_connected_client(db)
                if client and await client.is_user_authorized():
                    file_to_send = self._find_screenshot_file(order.confirmation_screen_url) or (order.confirmation_screen_url if order.confirmation_screen_url and order.confirmation_screen_url.startswith('http') else None)
                    test_notice = f"🧪 *[TEST SANDBOX - Screenshot per te]*\n(Nessun messaggio inviato ad Alex)\n\n{caption_text}"
                    if file_to_send:
                        try:
                            await client.send_file('me', file_to_send, caption=test_notice)
                        except Exception:
                            await client.send_message('me', test_notice)
                    else:
                        await client.send_message('me', test_notice)
            except Exception as e:
                print(f"[Sandbox Send 'me' Error] {e}")

            log = ActivityLog(
                action_type="SCREEN_SENT",
                title=f"Screenshot ordine inviato a me (Messaggi Salvati) [SANDBOX]",
                details=f"Ordine: {order.order_number} ({order.product_title})"
            )
            db.add(log)
            order.status = "waiting_review"
            order.confirmation_sent_at = datetime.utcnow()
            db.commit()
            return {"success": True, "message": f"🧪 [SANDBOX] Screenshot ordine inviato ai tuoi 'Messaggi Salvati' su Telegram!"}

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "auth_required": True, "error": "Account Telegram non autorizzato. Collega il tuo numero in Impostazioni."}

            file_path = self._find_screenshot_file(order.confirmation_screen_url)

            if file_path:
                await client.send_file(target_contact, file_path, caption=caption_text)
            else:
                await client.send_message(target_contact, caption_text)

            log = ActivityLog(
                action_type="SCREEN_SENT",
                title=f"Screenshot ordine inviato ad Alex ({target_contact})",
                details=f"Ordine: {order.order_number} ({order.product_title})"
            )
            db.add(log)
            order.status = "waiting_review"
            order.confirmation_sent_at = datetime.utcnow()
            db.commit()
            return {"success": True, "message": f"Screenshot inviato con successo ad Alex ({target_contact}) su Telegram!"}
        except Exception as e:
            print(f"[Telegram Screen Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def send_review_confirmation(self, db: Session, order: Order, recipient: str = None) -> dict:
        """
        Invia la conferma della recensione pubblicata con screenshot ad Alex (@alex8700 o contatto venditore).
        In modalità Sandbox (test_mode=true) invia il messaggio di prova a te stesso (Messaggi Salvati / 'me').
        """
        is_test = self.get_setting(db, "test_mode", "false").lower() == "true"
        target_contact = (recipient or order.seller_contact or "@alex8700").strip()
        caption_text = f"Ciao Alex! La recensione a 5 stelle per l'ordine `{order.order_number}` (*{order.product_title}*) è stata pubblicata su Amazon.\nIn allegato lo screenshot per procedere al rimborso PayPal. Grazie!"

        if is_test:
            try:
                client = await self._ensure_connected_client(db)
                if client and await client.is_user_authorized():
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

                    file_to_send = self._find_screenshot_file(review_url) or (review_url if review_url and review_url.startswith('http') else None)
                    test_notice = f"🧪 *[TEST SANDBOX - Recensione per te]*\n(Nessun messaggio inviato ad Alex)\n\n{caption_text}"
                    if file_to_send:
                        try:
                            await client.send_file('me', file_to_send, caption=test_notice)
                        except Exception:
                            await client.send_message('me', test_notice)
                    else:
                        await client.send_message('me', test_notice)
            except Exception as e:
                print(f"[Sandbox Send 'me' Error] {e}")

            log = ActivityLog(
                action_type="REVIEW_SENT",
                title=f"Screenshot recensione 5★ inviato a me (Messaggi Salvati) [SANDBOX]",
                details=f"Ordine: {order.order_number} ({order.product_title})"
            )
            db.add(log)
            order.status = "waiting_refund"
            order.review_submitted_at = datetime.utcnow()
            db.commit()
            return {"success": True, "message": f"🧪 [SANDBOX] Screenshot recensione 5★ inviato ai tuoi 'Messaggi Salvati' su Telegram!"}

        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "auth_required": True, "error": "Account Telegram non autorizzato. Collega il tuo numero in Impostazioni."}

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

            file_path = self._find_screenshot_file(review_url)

            if file_path:
                await client.send_file(target_contact, file_path, caption=caption_text)
            else:
                await client.send_message(target_contact, caption_text)
            
            log = ActivityLog(
                action_type="REVIEW_SENT",
                title=f"Screenshot recensione 5★ inviato ad Alex ({target_contact})",
                details=f"Ordine: {order.order_number} ({order.product_title})"
            )
            db.add(log)
            order.status = "waiting_refund"
            order.review_submitted_at = datetime.utcnow()
            db.commit()
            return {"success": True, "message": f"Screenshot recensione inviato con successo ad Alex ({target_contact})!"}
        except Exception as e:
            print(f"[Telegram Review Send Error] {e}")
            return {"success": False, "error": str(e)}

    async def sync_seller_replies(self, db: Session, seller_handle: str = "@alex8700") -> dict:
        """
        Controlla i messaggi privati ricevuti da Alex/venditore DOPO l'invio della richiesta
        per estrarre il link Amazon inviato specificamente per quell'articolo.
        NON assegna MAI link storici o vecchi.
        """
        try:
            client = await self._ensure_connected_client(db)
            if not await client.is_user_authorized():
                return {"success": False, "auth_required": True, "error": "Telegram non autorizzato"}

            test_mode = self.get_setting(db, "test_mode", "false").lower() == "true"
            target = "me" if test_mode else (seller_handle or "@alex8700").strip()
            entity = await client.get_entity(target)
            
            # Cerca SOLO gli ordini in stato 'waiting_link' che NON hanno già un link impostato
            pending_orders = db.query(Order).filter(
                Order.status == "waiting_link",
                or_(Order.amazon_url == None, Order.amazon_url == "")
            ).order_by(Order.order_date.asc()).all()
            
            if not pending_orders:
                return {"success": True, "updated_count": 0, "message": "Nessun ordine in attesa di link."}

            # Troviamo la data della richiesta più vecchia in attesa
            oldest_order_date = min((o.order_date for o in pending_orders if o.order_date), default=None)
            if not oldest_order_date:
                return {"success": True, "updated_count": 0, "message": "Nessuna data di richiesta valida."}

            # Preleva i messaggi inviati DOPO la richiesta (in Sandbox 'me' i messaggi hanno m.out=True)
            messages = []
            async for m in client.iter_messages(entity, limit=25):
                is_valid_sender = (target == "me") or (not m.out)
                if is_valid_sender and m.text and m.date:
                    msg_date_utc = m.date.replace(tzinfo=None) if hasattr(m.date, 'tzinfo') and m.date.tzinfo else m.date
                    if msg_date_utc >= oldest_order_date:
                        messages.append((msg_date_utc, m))

            # Ordina cronologicamente (dal più vecchio al più recente)
            messages.sort(key=lambda x: x[0])

            updated = 0
            for msg_date_utc, m in messages:
                text = m.text or ""
                urls = re.findall(r'https?://[^\s]+', text)
                amz_urls = [u for u in urls if 'amazon' in u.lower() or 'amzn' in u.lower()]
                if amz_urls:
                    best_url = amz_urls[0]
                    # Trova il primo ordine la cui richiesta è avvenuta PRIMA di questo messaggio
                    target_order = None
                    for o in pending_orders:
                        if o.order_date and o.order_date <= msg_date_utc and (not o.amazon_url):
                            target_order = o
                            break
                    
                    if target_order:
                        pending_orders.remove(target_order)
                        target_order.amazon_url = best_url
                        target_order.status = "link_approved"
                        
                        match_offer = db.query(Offer).filter_by(title=target_order.product_title).first()
                        if match_offer:
                            match_offer.amazon_link = best_url
                            match_offer.status = "link_received"

                        log = ActivityLog(
                            action_type="LINK_RECEIVED",
                            title=f"Link Amazon Ricevuto da Alex ({target})!",
                            details=f"Articolo: {target_order.product_title} | Link: {best_url}"
                        )
                        db.add(log)
                        db.commit()
                        updated += 1

            return {
                "success": True,
                "updated_count": updated,
                "message": f"Sincronizzazione completata: {updated} nuovi link ricevuti da Alex!"
            }
        except Exception as e:
            print(f"[Telegram Sync Replies Error] {e}")
            return {"success": False, "error": str(e)}

telegram_service = TelegramManager()

