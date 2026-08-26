import os
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_ROOT, "data"))
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def generate_amazon_order_screenshot(order_number: str, product_title: str, price: float, order_date: datetime = None) -> str:
    """
    Genera un'immagine nitida e professionale che simula la schermata dei 'Dettagli dell'ordine' di Amazon.it,
    completa di intestazione Amazon, numero ordine, data, stato 'Confermato', totale e dettagli articolo.
    Ritorna il percorso del file salvato.
    """
    if order_date is None:
        order_date = datetime.now()
        
    date_str = order_date.strftime("%d %B %Y").replace("January", "Gennaio").replace("February", "Febbraio").replace("March", "Marzo").replace("April", "Aprile").replace("May", "Maggio").replace("June", "Giugno").replace("July", "Luglio").replace("August", "Agosto").replace("September", "Settembre").replace("October", "Ottobre").replace("November", "Novembre").replace("December", "Dicembre")

    # Dimensioni immagine tipica mobile/web Amazon order page
    width = 750
    height = 920
    
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    # Intestazione Amazon
    draw.rectangle([0, 0, width, 85], fill='#232F3E')
    
    # Logo Amazon text
    try:
        font_logo = ImageFont.truetype("arialbd.ttf", 32)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_title = ImageFont.truetype("arialbd.ttf", 26)
        font_regular = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        font_logo = ImageFont.load_default()
        font_sub = font_logo
        font_bold = font_logo
        font_title = font_logo
        font_regular = font_logo
        font_small = font_logo

    draw.text((25, 25), "amazon.it", fill='#FF9900', font=font_logo)
    draw.text((width - 190, 32), "I miei ordini", fill='#FFFFFF', font=font_sub)

    # Titolo pagina
    draw.text((25, 110), "Dettagli dell'ordine", fill='#0F1111', font=font_title)
    
    # Box riepilogo ordine
    box_top = 160
    box_bottom = 270
    draw.rectangle([20, box_top, width - 20, box_bottom], fill='#F0F2F2', outline='#D5D9D9', width=1)
    
    draw.text((40, box_top + 18), "Data dell'ordine:", fill='#565959', font=font_small)
    draw.text((40, box_top + 40), date_str, fill='#0F1111', font=font_bold)
    
    draw.text((260, box_top + 18), "Totale:", fill='#565959', font=font_small)
    draw.text((260, box_top + 40), f"EUR {price:.2f}", fill='#0F1111', font=font_bold)
    
    draw.text((460, box_top + 18), "Numero ordine:", fill='#565959', font=font_small)
    draw.text((460, box_top + 40), order_number, fill='#0F1111', font=font_bold)

    # Sezione Spedizione / Consegna
    ship_box_top = 290
    ship_box_bottom = 760
    draw.rectangle([20, ship_box_top, width - 20, ship_box_bottom], fill='#FFFFFF', outline='#D5D9D9', width=1)
    
    # Barra verde 'Confermato'
    draw.rectangle([20, ship_box_top, width - 20, ship_box_top + 60], fill='#F0FFF4')
    draw.text((40, ship_box_top + 18), "✓ Ordine confermato", fill='#007600', font=font_bold)

    # Indirizzo di spedizione (anonimizzato)
    draw.text((40, ship_box_top + 80), "Indirizzo di consegna:", fill='#565959', font=font_small)
    draw.text((40, ship_box_top + 105), "Cliente Amazon Prime", fill='#0F1111', font=font_bold)
    draw.text((40, ship_box_top + 135), "Via Roma 12, 00100 Roma (RM)", fill='#565959', font=font_regular)

    # Linea separatrice
    draw.line([40, ship_box_top + 180, width - 40, ship_box_top + 180], fill='#E7E7E7', width=1)

    # Dettagli Articolo
    art_y = ship_box_top + 205
    # Simula riquadro immagine prodotto
    draw.rectangle([40, art_y, 160, art_y + 120], fill='#F7F8F8', outline='#D5D9D9')
    draw.text((70, art_y + 50), "[ FOTO ]", fill='#888C8C', font=font_small)

    # Titolo prodotto (a capo su 2 righe se lungo)
    title_short = (product_title[:55] + '...') if len(product_title) > 55 else product_title
    draw.text((180, art_y), title_short, fill='#007185', font=font_bold)
    draw.text((180, art_y + 35), "Venduto da: Venditore Partner Amazon", fill='#565959', font=font_small)
    draw.text((180, art_y + 60), "Condizione: Nuovo", fill='#565959', font=font_small)
    draw.text((180, art_y + 90), f"EUR {price:.2f}", fill='#B12704', font=font_bold)

    # Bottone 'Visualizza o modifica ordine'
    draw.rectangle([40, ship_box_bottom - 85, width - 40, ship_box_bottom - 30], fill='#FFD814', outline='#FCD200', width=1)
    draw.text((width // 2 - 130, ship_box_bottom - 65), "Visualizza i dettagli della ricevuta", fill='#0F1111', font=font_bold)

    # Footer
    draw.text((width // 2 - 110, height - 50), "Amazon.it Servizio Clienti", fill='#565959', font=font_small)

    filename = f"screen_{order_number.replace('-', '_')}.jpg"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    img.save(filepath, 'JPEG', quality=95)
    
    return f"/screenshots/{filename}"

def generate_amazon_review_screenshot(order_number: str, product_title: str, review_title: str, review_body: str) -> str:
    """
    Genera un'immagine nitida e professionale che simula la recensione a 5 stelle pubblicata su Amazon.it,
    completa di 5 stelle d'oro, badge 'Acquisto verificato', titolo recensione, testo e dettagli prodotto.
    """
    width = 750
    height = 920
    
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)

    # Intestazione Amazon
    draw.rectangle([0, 0, width, 85], fill='#232F3E')
    
    try:
        font_logo = ImageFont.truetype("arialbd.ttf", 32)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_title = ImageFont.truetype("arialbd.ttf", 24)
        font_regular = ImageFont.truetype("arial.ttf", 19)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_stars = ImageFont.truetype("arialbd.ttf", 28)
    except:
        font_logo = ImageFont.load_default()
        font_sub = font_logo
        font_bold = font_logo
        font_title = font_logo
        font_regular = font_logo
        font_small = font_logo
        font_stars = font_logo

    draw.text((25, 25), "amazon.it", fill='#FF9900', font=font_logo)
    draw.text((width - 230, 32), "Le tue recensioni", fill='#FFFFFF', font=font_sub)

    # Titolo Pagina
    draw.text((25, 110), "Recensione inviata con successo", fill='#007600', font=font_title)
    draw.text((25, 145), f"Grazie per aver condiviso la tua opinione su questo articolo!", fill='#565959', font=font_small)

    # Box Recensione Pubblicata
    box_top = 185
    box_bottom = 850
    draw.rectangle([20, box_top, width - 20, box_bottom], fill='#FAFAFA', outline='#D5D9D9', width=1)

    # Prodotto recensito
    draw.text((45, box_top + 25), "Articolo recensito:", fill='#565959', font=font_small)
    short_title = product_title if len(product_title) <= 55 else product_title[:55] + "..."
    draw.text((45, box_top + 48), short_title, fill='#0F1111', font=font_bold)

    # Separatore
    draw.line([(45, box_top + 85), (width - 45, box_top + 85)], fill='#E7E7E7', width=1)

    # Stelle e badge
    draw.text((45, box_top + 105), "★★★★★", fill='#FFA41C', font=font_stars)
    draw.text((165, box_top + 110), "5,0 su 5 stelle", fill='#0F1111', font=font_bold)
    
    # Badge Acquisto Verificato
    draw.rectangle([45, box_top + 155, 230, box_top + 185], fill='#FFF4E5', outline='#F3A847', width=1)
    draw.text((55, box_top + 160), "✓ Acquisto verificato", fill='#B12704', font=font_small)

    # Titolo Recensione
    draw.text((45, box_top + 205), review_title or "Ottimo prodotto, spedizione impeccabile", fill='#0F1111', font=font_title)
    
    # Data e ordine
    now_str = datetime.now().strftime("%d %B %Y").replace("January", "Gennaio").replace("February", "Febbraio").replace("March", "Marzo").replace("April", "Aprile").replace("May", "Maggio").replace("June", "Giugno").replace("July", "Luglio").replace("August", "Agosto").replace("September", "Settembre").replace("October", "Ottobre").replace("November", "Novembre").replace("December", "Dicembre")
    draw.text((45, box_top + 245), f"Recensito in Italia il {now_str} • Ordine #{order_number}", fill='#565959', font=font_small)

    # Testo Recensione (a capo automatico)
    import textwrap
    lines = textwrap.wrap(review_body or "Prodotto eccezionale, esattamente conforme alla descrizione. Arrivato nei tempi stabiliti con un ottimo imballaggio. Funziona alla perfezione e i materiali sono di ottima qualità. Consigliatissimo!", width=58)
    y_text = box_top + 285
    for line in lines[:10]:
        draw.text((45, y_text), line, fill='#0F1111', font=font_regular)
        y_text += 32

    # Salva immagine su disco
    filename = f"review_{order_number.replace('-', '_')}.jpg"
    file_path = os.path.join(SCREENSHOTS_DIR, filename)
    img.save(file_path, "JPEG", quality=95)
    
    return f"/screenshots/{filename}"


def parse_delivery_date_text(ocr_text: str, base_date: datetime = None) -> tuple:
    """
    Estrapola la data stimata di consegna e la descrizione dal testo dello screenshot.
    Riconosce espressioni come 'In arrivo lunedì', 'Consegna prevista: 25 agosto', 'In consegna domani', ecc.
    Ritorna una tupla (datetime_consegna, descrizione_consegna).
    """
    import re
    if not ocr_text:
        return None, None
    if base_date is None:
        base_date = datetime.utcnow()

    weekdays_map = {
        'lunedì': 0, 'lunedi': 0, 'monday': 0, 'lun': 0,
        'martedì': 1, 'martedi': 1, 'tuesday': 1, 'mar': 1,
        'mercoledì': 2, 'mercoledi': 2, 'wednesday': 2, 'mer': 2,
        'giovedì': 3, 'giovedi': 3, 'thursday': 3, 'gio': 3,
        'venerdì': 4, 'venerdi': 4, 'friday': 4, 'ven': 4,
        'sabato': 5, 'saturday': 5, 'sab': 5,
        'domenica': 6, 'sunday': 6, 'dom': 6
    }

    months_map = {
        'gen': 1, 'gennaio': 1, 'jan': 1,
        'feb': 2, 'febbraio': 2,
        'mar': 3, 'marzo': 3,
        'apr': 4, 'aprile': 4,
        'mag': 5, 'maggio': 5, 'may': 5,
        'giu': 6, 'giugno': 6, 'jun': 6,
        'lug': 7, 'luglio': 7, 'jul': 7,
        'ago': 8, 'agosto': 8, 'aug': 8,
        'set': 9, 'settembre': 9, 'sep': 9,
        'ott': 10, 'ottobre': 10, 'oct': 10,
        'nov': 11, 'novembre': 11,
        'dic': 12, 'dicembre': 12, 'dec': 12
    }

    ref_date = base_date

    # Cerca data dell'ordine se presente nell'intestazione email (es. "21 ago - 10:47")
    order_dt_m = re.search(r'(\d{1,2})\s*(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)[a-z]*(?:\s*-\s*(\d{1,2}):(\d{2}))?', ocr_text, re.IGNORECASE)
    if order_dt_m:
        try:
            d = int(order_dt_m.group(1))
            m_str = order_dt_m.group(2).lower()
            m = months_map.get(m_str, ref_date.month)
            h = int(order_dt_m.group(3)) if order_dt_m.group(3) else ref_date.hour
            mn = int(order_dt_m.group(4)) if order_dt_m.group(4) else ref_date.minute
            order_dt = datetime(ref_date.year, m, d, h, mn)
            ref_date = order_dt
        except Exception:
            pass

    # Ignora linee che sono solo la barra di stato/stepper Amazon (Ordinato Spedito In consegna Consegnato)
    cleaned_lines = []
    for line in ocr_text.splitlines():
        l_str = line.strip()
        if re.search(r'ordinato.*spedito.*consegn', l_str, re.IGNORECASE):
            continue
        if l_str.lower() in ['in consegna consegnato', 'spedito in consegna', 'ordinato spedito']:
            continue
        cleaned_lines.append(l_str)

    cleaned_text = '\n'.join(cleaned_lines)

    # Trova tutti i possibili match di arrivo/consegna
    delivery_matches = re.finditer(r'(?:in arrivo|consegna(?: prevista)?|arriver[àa]|consegna stimata)[\s:]*([^\n\r\.\,]+)', cleaned_text, re.IGNORECASE)
    
    candidates = []
    for dm in delivery_matches:
        raw_val = dm.group(1).strip()
        candidates.append(raw_val)

    for raw in candidates:
        raw_lower = raw.lower()
        if 'domani' in raw_lower or 'tomorrow' in raw_lower:
            dt = ref_date + timedelta(days=1)
            return dt, 'Domani'
        if 'oggi' in raw_lower or 'today' in raw_lower:
            dt = ref_date
            return dt, 'Oggi'

        for w_name, w_idx in weekdays_map.items():
            if re.search(r'\b' + re.escape(w_name) + r'\b', raw_lower):
                cur_w = ref_date.weekday()
                days_ahead = (w_idx - cur_w) % 7
                if days_ahead == 0:
                    days_ahead = 7
                dt = ref_date + timedelta(days=days_ahead)
                return dt, f'{w_name.capitalize()}'

        m_num = re.search(r'\b([0-9]{1,2})\s*([a-zàèìòù]+)\b', raw_lower)
        if m_num:
            try:
                day = int(m_num.group(1))
                m_str = m_num.group(2).lower()
                for name_prefix, idx in months_map.items():
                    if m_str.startswith(name_prefix):
                        dt = datetime(ref_date.year, idx, day, ref_date.hour, ref_date.minute)
                        if dt < ref_date - timedelta(days=30):
                            dt = datetime(ref_date.year + 1, idx, day, ref_date.hour, ref_date.minute)
                        return dt, f'{day} {name_prefix.capitalize()}'
            except Exception:
                pass

    if candidates:
        return None, candidates[0]

    return None, None


def extract_amazon_order_from_screenshot(image_bytes: bytes, gemini_api_key: str = None) -> dict:
    """
    Analizza uno screenshot di un ordine Amazon (ricevuta, conferma app, email)
    ed estrae automaticamente:
    - Numero Ordine Amazon (formato xxx-xxxxxxx-xxxxxxx)
    - Totale Pagato (€)
    - Titolo Prodotto
    - Giorno / Data di Consegna / Arrivo stimata
    """
    import re
    import base64
    import json
    import requests

    result = {
        "order_number": None,
        "price_paid": None,
        "product_title": None,
        "estimated_delivery_date": None,
        "delivery_info": None,
        "method": "none"
    }

    if not image_bytes:
        return result

    # 1. TENTATIVO CON GEMINI VISION AI (Se API Key disponibile in Impostazioni o ENV)
    api_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if api_key:
        try:
            # Rileva dinamicamente il formato dell'immagine (JPEG, PNG, WEBP)
            mime_type = "image/jpeg"
            if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                mime_type = "image/png"
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:16]:
                mime_type = "image/webp"

            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            prompt = (
                "Sei un assistente specializzato nell'analisi di schermate e ricevute di ordini Amazon.it.\n"
                "Analizza questa immagine con la massima attenzione ed estrai in formato JSON valido:\n"
                "1. 'order_number': il numero d'ordine Amazon a 17 cifre 'xxx-xxxxxxx-xxxxxxx' (es. '408-1234567-8901234'). Se non presente scrivi null.\n"
                "2. 'price_paid': il totale complessivo pagato/speso su Amazon in euro come numero decimale (es. 24.99 o 99.00). Cerca diciture come 'Totale', 'Totale ordine', 'EUR', '€', 'Importo'. Se presente il prezzo dell'articolo o il totale, estrailo come float. Se assente scrivi null.\n"
                "3. 'product_title': il titolo o descrizione del prodotto/articolo ordinato. Se non presente scrivi null.\n"
                "4. 'delivery_info': la data, giorno o indicazione di consegna/arrivo (es. 'In arrivo lunedì', 'Consegna: 28 agosto', 'Consegnato', 'Domani'). Se non presente scrivi null.\n"
                "5. 'raw_text': breve riepilogo del testo letto.\n"
                "Rispondi ESCLUSIVAMENTE con il blocco JSON puro, senza spiegazioni."
            )
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data
                            }
                        }
                    ]
                }],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                raw_text_content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Pulisci eventuale markdown backticks ```json ... ```
                if raw_text_content.startswith("```"):
                    raw_text_content = re.sub(r'^```(?:json)?\s*', '', raw_text_content)
                    raw_text_content = re.sub(r'\s*```$', '', raw_text_content)
                parsed = json.loads(raw_text_content)
                if parsed.get("order_number"):
                    result["order_number"] = str(parsed["order_number"]).strip()
                if parsed.get("price_paid") is not None:
                    try:
                        clean_p = str(parsed["price_paid"]).replace('€', '').replace('EUR', '').replace(',', '.').strip()
                        p_val = float(clean_p)
                        if p_val > 0:
                            result["price_paid"] = p_val
                    except (ValueError, TypeError):
                        pass
                if parsed.get("product_title"):
                    result["product_title"] = str(parsed["product_title"]).strip()
                
                delivery_raw = parsed.get("delivery_info")
                if delivery_raw:
                    dt, d_info = parse_delivery_date_text(str(delivery_raw) + " " + str(parsed.get("raw_text", "")))
                    if dt:
                        result["estimated_delivery_date"] = dt.isoformat()
                    result["delivery_info"] = d_info or str(delivery_raw).strip()

                result["method"] = "gemini_vision"
                return result
        except Exception as e:
            print(f"[OCR Gemini Vision Error] {e}")

    # 2. TENTATIVO CON MOTORE OCR CLOUD ALTA PRECISIONE (OCR.space - Zero installazione, ultra preciso)
    try:
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        ocr_payload = {
            "base64Image": "data:image/jpeg;base64," + b64_img,
            "language": "ita",
            "isOverlayRequired": False,
            "apikey": "K88728994588957"
        }
        ocr_resp = requests.post("https://api.ocr.space/parse/image", data=ocr_payload, timeout=10)
        if ocr_resp.status_code == 200:
            ocr_data = ocr_resp.json()
            parsed_res = ocr_data.get("ParsedResults", [])
            ocr_text = parsed_res[0].get("ParsedText", "") if parsed_res else ""
            
            # Cerca numero d'ordine Amazon (es. 404-1867984-8717122 o 408 1234567 8901234)
            order_m = re.search(r'([0-9]{3}[-\s][0-9]{7}[-\s][0-9]{7})', ocr_text)
            if order_m:
                result["order_number"] = re.sub(r'\s+', '-', order_m.group(0)).strip()
                result["method"] = "cloud_ocr"

            # Cerca importo totale pagato (supporta EUR 29,99, € 29,99, 29,99 €, Totale: 29,99)
            price_patterns = [
                r'(?:totale|importo|pagato|totale ordine|prezzo)[\s:\n\r]*(?:€|eur)?\s*([0-9]+(?:[.,][0-9]{2}))',
                r'(?:€|eur)\s*([0-9]+(?:[.,][0-9]{2}))',
                r'([0-9]+(?:[.,][0-9]{2}))\s*(?:€|eur)\b',
                r'(?:totale|eur|€)[\s\S]{1,30}?([0-9]+[.,][0-9]{2})'
            ]
            for pat in price_patterns:
                price_m = re.search(pat, ocr_text, re.IGNORECASE)
                if price_m:
                    try:
                        val = float(price_m.group(1).replace(',', '.'))
                        if val > 0:
                            result["price_paid"] = val
                            break
                    except ValueError:
                        pass

            # Cerca giorno/data di consegna
            dt, d_info = parse_delivery_date_text(ocr_text)
            if dt:
                result["estimated_delivery_date"] = dt.isoformat()
            if d_info:
                result["delivery_info"] = d_info

            if result["order_number"]:
                return result
    except Exception as e:
        print(f"[Cloud OCR Error] {e}")

    # 3. TENTATIVO CON PYTESSERACT OCR NATIVO (se disponibile su sistema)
    try:
        import pytesseract
        image = Image.open(io.BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(image, lang="ita+eng")
        
        # Cerca numero ordine Amazon (es. 404-1867984-8717122 o 408-1234567-8901234)
        order_match = re.search(r'\b([0-9]{3}[-\s][0-9]{7}[-\s][0-9]{7})\b', ocr_text)
        if order_match:
            result["order_number"] = re.sub(r'\s+', '-', order_match.group(1)).strip()
            result["method"] = "tesseract_ocr"

        # Cerca prezzo pagato
        price_patterns = [
            r'(?:totale|totale ordine|importo|pagato|totale da pagare|prezzo)[\s:\n\r]*(?:€|eur)?\s*([0-9]+(?:[.,][0-9]{2}))',
            r'(?:€|eur)\s*([0-9]+(?:[.,][0-9]{2}))',
            r'([0-9]+(?:[.,][0-9]{2}))\s*(?:€|eur)\b'
        ]
        for p in price_patterns:
            pm = re.search(p, ocr_text, re.IGNORECASE)
            if pm:
                try:
                    val = float(pm.group(1).replace(',', '.'))
                    if val > 0:
                        result["price_paid"] = val
                        break
                except ValueError:
                    pass

        # Cerca giorno/data di consegna
        dt, d_info = parse_delivery_date_text(ocr_text)
        if dt:
            result["estimated_delivery_date"] = dt.isoformat()
        if d_info:
            result["delivery_info"] = d_info
    except Exception as e:
        print(f"[OCR Tesseract Error] {e}")

    return result

