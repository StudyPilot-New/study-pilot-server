"""Manual commercial payment reports. Only an administrator grants entitlement."""
import calendar
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from accounts import AccountStore
from access_store import AccessError
from plans import PLANS


def next_month(timestamp):
    date = datetime.fromtimestamp(timestamp, timezone.utc)
    year, month = (date.year + 1, 1) if date.month == 12 else (date.year, date.month + 1)
    return date.replace(year=year, month=month, day=min(date.day, calendar.monthrange(year, month)[1])).timestamp()


def short_text(value, label, minimum=1, maximum=120):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum or any(ord(c) < 32 for c in value):
        raise AccessError(400, f'Revisa {label}.')
    return value.strip()


class PaymentStore(AccountStore):
    def __init__(self, path):
        super().__init__(path)
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS payment_settings (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS payment_orders (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL, plan TEXT NOT NULL,
                amount_cents INTEGER NOT NULL, recipient TEXT NOT NULL,
                status TEXT NOT NULL, payer TEXT, reported_reference TEXT,
                verified_reference TEXT UNIQUE, reviewer TEXT, review_note TEXT,
                created_at REAL NOT NULL, reported_at REAL, reviewed_at REAL);
              CREATE UNIQUE INDEX IF NOT EXISTS payment_open_order
                ON payment_orders(account_id) WHERE status IN ('awaiting_payment','pending_review');
            ''')

    def admin(self, token):
        account = self.session(token)
        if account['role'] != 'admin': raise AccessError(403, 'Solo el administrador puede revisar pagos.')
        return account

    def settings(self):
        with self.connect() as db: row = db.execute('SELECT data FROM payment_settings WHERE id=1').fetchone()
        return json.loads(row['data']) if row else {'enabled': False, 'cashtag': '$Carluchad', 'recipient_name': 'Carluchad'}

    def configure(self, token, data):
        self.admin(token)
        if type(data.get('enabled')) is not bool: raise AccessError(400, 'Estado de cobros no válido.')
        tag = short_text(data.get('cashtag'), 'el $Cashtag').lstrip('$')
        if not re.fullmatch(r'[A-Za-z0-9]{1,20}', tag) or not re.search('[A-Za-z]', tag):
            raise AccessError(400, 'Escribe un $Cashtag válido, sin enlaces ni espacios.')
        config = {'enabled': data['enabled'], 'cashtag': '$' + tag,
                  'recipient_name': short_text(data.get('recipient_name'), 'el nombre del destinatario')}
        with self.connect() as db:
            db.execute('INSERT INTO payment_settings VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (json.dumps(config),))
        return config

    def catalog(self):
        config = self.settings()
        return config | {'payment_url': 'https://cash.app/' + config['cashtag'] if config['cashtag'] else None,
            'verification': 'manual', 'automatic_renewal': False,
            'plans': [dict(id=key, **value) for key, value in PLANS.items()]}

    def create_order(self, token, plan):
        account = self.session(token)
        if not isinstance(plan, str) or plan not in PLANS: raise AccessError(400, 'Plan no válido.')
        config = self.settings()
        if not config['enabled']: raise AccessError(409, 'Los cobros todavía no están habilitados.')
        if account['access_reason'] in ('manual', 'paid_lifetime'):
            raise AccessError(409, 'Ya tienes acceso permanente; no necesitas pagar.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute("SELECT * FROM payment_orders WHERE account_id=? AND status IN ('awaiting_payment','pending_review')", (account['id'],)).fetchone()
            if old:
                if old['plan'] != plan: raise AccessError(409, 'Ya tienes una solicitud abierta. Resuélvela antes de cambiar de plan.')
                return dict(old)
            identifier = uuid.uuid4().hex
            db.execute('INSERT INTO payment_orders(id,account_id,plan,amount_cents,recipient,status,created_at) VALUES(?,?,?,?,?,?,?)',
                (identifier, account['id'], plan, PLANS[plan]['amount_cents'], config['cashtag'], 'awaiting_payment', time.time()))
            return dict(db.execute('SELECT * FROM payment_orders WHERE id=?', (identifier,)).fetchone())

    def orders(self, token, admin=False):
        account = self.admin(token) if admin else self.session(token)
        with self.connect() as db:
            sql = '''SELECT o.*,a.email,a.display_name FROM payment_orders o JOIN accounts a ON a.id=o.account_id'''
            return [dict(row) for row in db.execute(sql + ('' if admin else ' WHERE o.account_id=?') + ' ORDER BY o.created_at DESC LIMIT 200',
                () if admin else (account['id'],))]

    def report(self, token, identifier, payer, reference):
        account = self.session(token)
        payer = short_text(payer, 'el nombre del remitente')
        reference = short_text(reference, 'la referencia de la transferencia')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM payment_orders WHERE id=? AND account_id=?', (identifier, account['id'])).fetchone()
            if not row: raise AccessError(404, 'Solicitud no encontrada.')
            if row['status'] == 'pending_review': return {'status': 'pending_review'}
            if row['status'] != 'awaiting_payment': raise AccessError(409, 'Esta solicitud ya fue resuelta.')
            db.execute("UPDATE payment_orders SET status='pending_review',payer=?,reported_reference=?,reported_at=? WHERE id=?",
                       (payer, reference, time.time(), identifier))
        return {'status': 'pending_review'}

    def cancel(self, token, identifier):
        account = self.session(token)
        with self.connect() as db:
            row = db.execute('SELECT status FROM payment_orders WHERE id=? AND account_id=?', (identifier, account['id'])).fetchone()
            if not row: raise AccessError(404, 'Solicitud no encontrada.')
            if row['status'] == 'cancelled': return {'status': 'cancelled'}
            if row['status'] != 'awaiting_payment': raise AccessError(409, 'Una transferencia reportada debe ser revisada por el administrador.')
            changed = db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=? AND status='awaiting_payment'", (identifier,)).rowcount
            if not changed: raise AccessError(409, 'La solicitud cambió. Actualiza el estado.')
        return {'status': 'cancelled'}

    def review(self, token, identifier, action, reference='', note='', received_cents=None):
        admin = self.admin(token)
        if action not in ('approve', 'reject'): raise AccessError(400, 'Acción no válida.')
        note = short_text(note, 'la nota', minimum=0, maximum=500)
        if action == 'approve':
            reference = short_text(reference, 'el identificador real de la transferencia').casefold()
            if type(received_cents) is not int: raise AccessError(400, 'Confirma el importe recibido en centavos.')
        else:
            if not note: raise AccessError(400, 'Indica el motivo del rechazo.')
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM payment_orders WHERE id=?', (identifier,)).fetchone()
                if not row: raise AccessError(404, 'Solicitud no encontrada.')
                target = 'approved' if action == 'approve' else 'rejected'
                if row['status'] == target: return {'status': target}
                if row['status'] != 'pending_review': raise AccessError(409, 'Esta solicitud no está pendiente de revisión.')
                if row['account_id'] == admin['id']: raise AccessError(403, 'No puedes revisar tus propios pagos.')
                account = db.execute('SELECT * FROM accounts WHERE id=?', (row['account_id'],)).fetchone()
                if action == 'approve':
                    if account['status'] == 'blocked': raise AccessError(409, 'La cuenta está bloqueada. No se activará mediante un pago.')
                    if received_cents != row['amount_cents']: raise AccessError(400, 'El importe recibido no coincide con el plan.')
                    if account['access_reason'] not in ('manual', 'paid_lifetime'):
                        lifetime = row['plan'] == 'one_time'
                        until = None if lifetime else next_month(max(time.time(), account['paid_until'] or 0))
                        db.execute("UPDATE accounts SET status='active',access_reason=?,paid_until=? WHERE id=?",
                            ('paid_lifetime' if lifetime else 'paid', until, account['id']))
                    db.execute('UPDATE users SET active=1 WHERE name=?', ('account:' + account['id'],))
                db.execute('UPDATE payment_orders SET status=?,verified_reference=?,reviewer=?,review_note=?,reviewed_at=? WHERE id=?',
                    (target, reference if action == 'approve' else None, admin['id'], note, time.time(), identifier))
        except sqlite3.IntegrityError:
            raise AccessError(409, 'Esta transferencia ya fue utilizada para aprobar otro pago.') from None
        return {'status': target}
