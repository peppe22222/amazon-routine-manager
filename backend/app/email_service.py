import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import Setting, Order, ActivityLog
from app.screenshot_service import generate_amazon_order_screenshot
from app.review_generator import generate_review

def extract_amazon_order_data(email_subject: str, email_body: str) -> dict:
    """
    Estrae numero d'ordine, importo e titolo prodotto dal corpo o oggetto della mail Amazon.
    """
    # Regex standard numero ordine Amazon: 3 cifre - 7 cifre - 7 cifre
    order_regex = r"\b(\d{3}-\d{7}-\d{7})\b"
    order_match = re.search(order_regex, email_subject + " " + email_body)
    order_number = order_match.group(1) if order_match else None

    # Regex prezzo
    price_regex = r"EUR\s*([\d,.]+)|([\d,.]+)\s*€"
    price_match = re.search(price_regex, email_body)
    price = 0.0
    if price_match:
        price_str = (price_match.group(1) or price_match.group(2)).replace(",", ".")
        try:
            price = float(price_str)
        except:
            price = 0.0

    return {
        "order_number": order_number,
        "price": price,
        "subject": email_subject
    }

def create_order_from_data(db: Session, order_number: str, product_title: str, price: float, seller_contact: str = None, is_test: bool = False, product_image: str = None) -> Order:
    """
    Crea un nuovo ordine nel database, genera lo screenshot della conferma e pre-genera la recensione a 5 stelle.
    """
    # Verifica se esiste già
    existing = db.query(Order).filter_by(order_number=order_number).first()
    if existing:
        return existing

    # Nessuno screenshot fittizio pre-generato
    order_date = datetime.utcnow()
    screen_url = None
    
    # Pre-genera recensione 5 stelle
    review_data = generate_review(product_title)
    
    # Data target recensione (+10 giorni)
    review_target_date = order_date + timedelta(days=10)

    order = Order(
        order_number=order_number,
        product_title=product_title,
        product_image=product_image,
        price_paid=price,
        refund_amount=price,
        seller_contact=seller_contact or "@venditore_telegram",
        status="pending_confirmation", # In attesa che l'utente prema il Tasto di Conferma!
        order_date=order_date,
        confirmation_screen_url=screen_url,
        review_target_date=review_target_date,
        review_title=review_data["title"],
        review_body=review_data["body"],
        is_test=is_test
    )
    
    db.add(order)
    
    # Log attività
    log = ActivityLog(
        action_type="OFFER_RECEIVED",
        title=f"Nuovo Ordine Ricevuto: {order_number}",
        details=f"Prodotto: {product_title} | Importo: €{price:.2f} | Screenshot pronto per la conferma."
    )
    db.add(log)
    db.commit()
    db.refresh(order)
    return order
