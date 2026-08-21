import os
import io
from datetime import datetime
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
