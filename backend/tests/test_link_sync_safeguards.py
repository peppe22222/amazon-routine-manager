"""
Suite di Test e Schermatura (Regression & Safeguard Tests)
Modulo di verifica per impedire la riapparizione del bug di approvazione anticipata dei link Amazon in "Da Comprare".
"""
import sys
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Aggiunge il path del backend per le importazioni
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base, Order, Offer, Setting, ActivityLog
from app.telegram_service import telegram_service


class TestLinkSyncSafeguards(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Database in-memory isolato per ogni test
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Mock del client Telegram
        self.mock_client = AsyncMock()
        self.mock_client.is_user_authorized = AsyncMock(return_value=True)

        # Dialogs mock
        self.dialog_mock = MagicMock()
        self.dialog_mock.entity = MagicMock()
        self.dialog_mock.entity.username = 'alex8700'
        self.dialog_mock.name = 'Alex Seller'

        async def iter_dialogs_mock(limit=50):
            yield self.dialog_mock
        self.mock_client.iter_dialogs = iter_dialogs_mock
        self.mock_client.get_entity = AsyncMock(return_value=self.dialog_mock.entity)

        # Inietta il mock nel servizio
        telegram_service._ensure_connected_client = AsyncMock(return_value=self.mock_client)
        telegram_service._save_orders_backup = MagicMock()

    def tearDown(self):
        self.db.close()

    async def test_guard_1_past_messages_never_matched(self):
        """SCHERMATURA 1: I messaggi inviati prima della richiesta non devono MAI essere accettati."""
        self.db.add(Setting(key='test_mode', value='false'))
        self.db.commit()

        req_time = datetime.utcnow()
        order = Order(
            order_number='In attesa #1',
            product_title='Smartphone X',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=req_time
        )
        self.db.add(order)
        self.db.commit()

        # Messaggio arrivato 1 minuto PRIMA della richiesta con un link Amazon valido
        past_msg = MagicMock()
        past_msg.out = False
        past_msg.text = 'Ecco il link: https://www.amazon.it/dp/B0PAST1234'
        past_msg.date = req_time - timedelta(minutes=1)
        past_msg.entities = []
        past_msg.reply_to_msg_id = None

        async def iter_msgs(entity, limit=50):
            yield past_msg
        self.mock_client.iter_messages = iter_msgs

        res = await telegram_service.sync_seller_replies(self.db)
        self.db.refresh(order)

        self.assertEqual(order.status, 'waiting_link')
        self.assertIsNone(order.amazon_url)
        self.assertEqual(res['updated_count'], 0)

    async def test_guard_2_already_used_urls_never_assigned(self):
        """SCHERMATURA 2: Un link Amazon già presente su un altro ordine nel DB non può MAI essere riassegnato."""
        self.db.add(Setting(key='test_mode', value='false'))
        used_url = 'https://www.amazon.it/dp/B0ALREADYUSED'
        
        # Ordine pre-esistente con questo link
        old_order = Order(
            order_number='ORD-OLD-999',
            product_title='Prodotto Vecchio',
            amazon_url=used_url,
            status='review_ready',
            order_date=datetime.utcnow() - timedelta(days=2)
        )
        self.db.add(old_order)

        req_time = datetime.utcnow()
        new_order = Order(
            order_number='In attesa #2',
            product_title='Cuffie Wireless',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=req_time
        )
        self.db.add(new_order)
        self.db.commit()

        # Messaggio arrivato dopo la richiesta, ma contenente il link già usato
        dup_msg = MagicMock()
        dup_msg.out = False
        dup_msg.text = f'Ecco il link: {used_url}'
        dup_msg.date = req_time + timedelta(minutes=2)
        dup_msg.entities = []
        dup_msg.reply_to_msg_id = None

        async def iter_msgs(entity, limit=50):
            yield dup_msg
        self.mock_client.iter_messages = iter_msgs

        res = await telegram_service.sync_seller_replies(self.db)
        self.db.refresh(new_order)

        self.assertEqual(new_order.status, 'waiting_link')
        self.assertIsNone(new_order.amazon_url)
        self.assertEqual(res['updated_count'], 0)

    async def test_guard_3_live_mode_never_checks_saved_messages_me(self):
        """SCHERMATURA 3: In modalità Live, 'me' (Messaggi Salvati) non deve MAI comparire nei target."""
        self.db.add(Setting(key='test_mode', value='false'))
        order = Order(
            order_number='In attesa #3',
            product_title='Tablet Pro',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=datetime.utcnow()
        )
        self.db.add(order)
        self.db.commit()

        targets_called = []
        async def fake_get_entity(t):
            targets_called.append(t)
            m = MagicMock()
            m.username = t
            return m
        self.mock_client.get_entity = fake_get_entity

        async def empty_iter(*args, **kwargs):
            if False: yield None
        self.mock_client.iter_dialogs = empty_iter
        self.mock_client.iter_messages = empty_iter

        await telegram_service.sync_seller_replies(self.db)

        self.assertNotIn('me', targets_called, "VIOLAZIONE: 'me' è stato controllato in modalità Live!")
        self.assertIn('@alex8700', targets_called)

    async def test_guard_4_sandbox_mode_never_checks_live_seller(self):
        """SCHERMATURA 4: In modalità Sandbox, le chat reali dei venditori non devono MAI essere scansionate."""
        self.db.add(Setting(key='test_mode', value='true'))
        order = Order(
            order_number='In attesa #4',
            product_title='Test Item',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=datetime.utcnow()
        )
        self.db.add(order)
        self.db.commit()

        targets_called = []
        async def fake_get_entity(t):
            targets_called.append(t)
            m = MagicMock()
            m.username = t
            return m
        self.mock_client.get_entity = fake_get_entity

        async def empty_iter(*args, **kwargs):
            if False: yield None
        self.mock_client.iter_dialogs = empty_iter
        self.mock_client.iter_messages = empty_iter

        await telegram_service.sync_seller_replies(self.db)

        self.assertNotIn('@alex8700', targets_called, "VIOLAZIONE: la chat reale di Alex è stata controllata in Sandbox!")
        self.assertIn('me', targets_called)

    async def test_guard_5_outbound_messages_never_accepted_in_live(self):
        """SCHERMATURA 5: In modalità Live, i messaggi inviati dall'utente (m.out=True) non devono MAI essere considerati."""
        self.db.add(Setting(key='test_mode', value='false'))
        req_time = datetime.utcnow()
        order = Order(
            order_number='In attesa #5',
            product_title='Monitor 27"',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=req_time
        )
        self.db.add(order)
        self.db.commit()

        out_msg = MagicMock()
        out_msg.out = True  # Inviato dall'utente
        out_msg.text = 'Ti mando io il link: https://www.amazon.it/dp/B0USEROUT123'
        out_msg.date = req_time + timedelta(minutes=1)
        out_msg.entities = []
        out_msg.reply_to_msg_id = None

        async def iter_msgs(entity, limit=50):
            yield out_msg
        self.mock_client.iter_messages = iter_msgs

        res = await telegram_service.sync_seller_replies(self.db)
        self.db.refresh(order)

        self.assertEqual(order.status, 'waiting_link')
        self.assertIsNone(order.amazon_url)
        self.assertEqual(res['updated_count'], 0)

    async def test_guard_6_legitimate_seller_reply_accepted(self):
        """SCHERMATURA 6: Solo un messaggio legittimo successivo alla richiesta deve approvare l'ordine."""
        self.db.add(Setting(key='test_mode', value='false'))
        req_time = datetime.utcnow()
        order = Order(
            order_number='In attesa #6',
            product_title='Friggitrice ad Aria',
            seller_contact='@alex8700',
            amazon_url=None,
            status='waiting_link',
            order_date=req_time,
            notes='tg_req_id:5555'
        )
        self.db.add(order)
        self.db.commit()

        valid_msg = MagicMock()
        valid_msg.out = False
        valid_msg.text = 'Perfetto, disponibile! Ecco il link: https://www.amazon.it/dp/B0AIRFRYER77'
        valid_msg.date = req_time + timedelta(minutes=3)
        valid_msg.entities = []
        valid_msg.reply_to_msg_id = 5555  # Reply diretta

        async def iter_msgs(entity, limit=50):
            yield valid_msg
        self.mock_client.iter_messages = iter_msgs

        res = await telegram_service.sync_seller_replies(self.db)
        self.db.refresh(order)

        self.assertEqual(order.status, 'link_approved')
        self.assertEqual(order.amazon_url, 'https://www.amazon.it/dp/B0AIRFRYER77')
        self.assertEqual(res['updated_count'], 1)


if __name__ == '__main__':
    unittest.main()
