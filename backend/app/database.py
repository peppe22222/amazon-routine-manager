import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_ROOT, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

# Supporto flessibile per PostgreSQL (Render/Neon/Supabase) e SQLite locale con persistenza
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "")
if RAW_DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql://", 1)
elif RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL
else:
    DB_PATH = os.path.join(DATA_DIR, "amazon_manager.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=True)

class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    price_info = Column(String(100), nullable=True) # es: "si paga 8 euro - 10%"
    refund_pct = Column(Float, default=100.0) # 100% rimborso
    taxes_covered = Column(Boolean, default=True)
    channel_name = Column(String(100), default="Offerte Telegram")
    seller_contact = Column(String(100), nullable=True) # @username venditore
    message_id = Column(String(255), nullable=True)
    status = Column(String(50), default="new") # new, requested, link_received, dismissed
    amazon_link = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False) # 408-1234567-1234567
    product_title = Column(String(255), nullable=False)
    product_image = Column(Text, nullable=True)
    seller_contact = Column(String(100), nullable=True)
    amazon_url = Column(Text, nullable=True)
    price_paid = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    
    # Status: pending_confirmation, confirmed_sent, waiting_review, review_ready, review_submitted, reimbursed, cancelled
    status = Column(String(50), default="pending_confirmation")
    
    order_date = Column(DateTime, default=datetime.utcnow)
    confirmation_screen_url = Column(Text, nullable=True)
    confirmation_sent_at = Column(DateTime, nullable=True)
    
    # Dati Consegna e Spedizione
    estimated_delivery_date = Column(DateTime, nullable=True) # Data stimata di arrivo articolo
    delivery_info = Column(String(100), nullable=True) # Testo estratto (es. 'In arrivo lunedì', '25 ago')
    
    # Recensione
    review_target_date = Column(DateTime, nullable=True) # Data consegna + 10 giorni
    review_title = Column(String(255), nullable=True)
    review_body = Column(Text, nullable=True)
    review_submitted_at = Column(DateTime, nullable=True)
    review_screen_url = Column(Text, nullable=True)
    review_sent_to_seller_at = Column(DateTime, nullable=True)
    
    # Rimborso PayPal
    paypal_email = Column(String(100), nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    is_test = Column(Boolean, default=False)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50)) # OFFER_RECEIVED, MESSAGE_SENT, SCREEN_SENT, REVIEW_READY, REFUNDED
    title = Column(String(255))
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrazione colonne per SQLite esistente
    try:
        with engine.connect() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("PRAGMA table_info(orders)")
            cols = [col[1] for col in cursor.fetchall()]
            if "estimated_delivery_date" not in cols:
                cursor.execute("ALTER TABLE orders ADD COLUMN estimated_delivery_date DATETIME")
            if "delivery_info" not in cols:
                cursor.execute("ALTER TABLE orders ADD COLUMN delivery_info VARCHAR(100)")
            conn.connection.commit()
    except Exception as e:
        print(f"[init_db migration note] {e}")
    
    # Inizializza impostazioni predefinite se non esistono
    db = SessionLocal()
    try:
        defaults = {
            "test_mode": "true",
            "telegram_api_id": "",
            "telegram_api_hash": "",
            "telegram_phone": "",
            "telegram_channel": "Articoli Addicted",
            "active_telegram_channel": "Articoli Addicted",
            "test_recipient": "@alex8700",
            "email_host": "imap.gmail.com",
            "email_user": "",
            "email_password": "",
            "review_days_wait": "10",
            "gemini_api_key": ""
        }
        for k, v in defaults.items():
            s = db.query(Setting).filter_by(key=k).first()
            if not s:
                db.add(Setting(key=k, value=v))
            elif k == "test_mode":
                s.value = "true"
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[init_db error] {e}")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
