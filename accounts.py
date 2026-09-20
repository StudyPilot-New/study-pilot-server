"""Account credentials and sessions. Existing access codes remain compatible."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import uuid
from access_store import AccessStore, AccessError

PASSWORD_ROUNDS = 600_000
SESSION_SECONDS = 30 * 86400


def normalized_email(value):
    if not isinstance(value,str): raise AccessError(400,'Escribe tu correo.')
    value=value.strip().casefold()
    if len(value)>254 or not re.fullmatch(r'[a-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}',value):
        raise AccessError(400,'Revisa el formato de tu correo.')
    return value


def password_digest(password, salt=None):
    if not isinstance(password,str) or not 12<=len(password)<=128:
        raise AccessError(400,'Usa una contraseña de entre 12 y 128 caracteres.')
    salt=salt or secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),PASSWORD_ROUNDS).hex()
    return f'pbkdf2_sha256${PASSWORD_ROUNDS}${salt}${digest}'


def password_matches(password, stored):
    if not isinstance(password,str) or len(password)>128: return False
    try:
        scheme,rounds,salt,expected=stored.split('$')
        if scheme!='pbkdf2_sha256' or not 100_000<=int(rounds)<=1_000_000: return False
        result=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex()
        return hmac.compare_digest(result,expected)
    except (ValueError,TypeError): return False


class AccountStore(AccessStore):
    def rate_limit(self,subject,limit,seconds=60,now=None):
        now=time.time() if now is None else now
        bucket=f'{seconds}:{int(now//seconds)}'
        subject=self.digest(subject)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT attempts FROM auth_attempts WHERE bucket=? AND subject=?',(bucket,subject)).fetchone()
            if row and row['attempts']>=limit:
                raise AccessError(429,'Demasiados intentos. Espera unos minutos antes de volver a intentar.')
            db.execute('INSERT INTO auth_attempts VALUES(?,?,1) ON CONFLICT(bucket,subject) DO UPDATE SET attempts=attempts+1',(bucket,subject))
            db.execute("DELETE FROM auth_attempts WHERE CAST(SUBSTR(bucket,INSTR(bucket,':')+1) AS INTEGER)*CAST(SUBSTR(bucket,1,INSTR(bucket,':')-1) AS INTEGER) < ?",(now-86400,))

    @staticmethod
    def public_account(row):
        active=row['status']!='blocked' and (row['access_reason'] in ('manual','paid_lifetime') or
                    row['access_reason']=='paid' and (row['paid_until'] or 0)>time.time())
        return {key:row[key] for key in ('id','email','display_name','role','status','access_reason','paid_until')} | {'active':bool(active)}

    def register(self,email,password,name):
        email=normalized_email(email)
        if not isinstance(name,str) or not name.strip() or len(name)>80 or any(ord(c)<32 for c in name):
            raise AccessError(400,'Escribe tu nombre, con un máximo de 80 caracteres.')
        hashed=password_digest(password)
        account_id=uuid.uuid4().hex
        now=time.time()
        try:
            with self.connect() as db:
                db.execute('INSERT INTO accounts(id,email,display_name,password_hash,created_at) VALUES(?,?,?,?,?)',
                           (account_id,email,name.strip(),hashed,now))
                # No usable legacy code is returned for an account.
                db.execute('INSERT INTO users(name,digest,active,daily_limit) VALUES(?,?,0,600)',
                           ('account:'+account_id,self.digest(secrets.token_urlsafe(48))))
        except sqlite3.IntegrityError:
            raise AccessError(409,'Ya existe una cuenta con ese correo. Inicia sesión.') from None
        return self.login(email,password)

    def login(self,email,password):
        email=normalized_email(email)
        with self.connect() as db:
            row=db.execute('SELECT * FROM accounts WHERE email=?',(email,)).fetchone()
        # Perform comparable password work even for unknown accounts.
        dummy='pbkdf2_sha256$600000$'+'00'*16+'$'+'00'*32
        valid=password_matches(password,row['password_hash'] if row else dummy)
        if not row or not valid: raise AccessError(401,'Correo o contraseña incorrectos.')
        if row['status']=='blocked': raise AccessError(403,'Tu acceso está bloqueado. Contacta con el administrador.')
        token='spc_'+secrets.token_urlsafe(32)
        now=time.time()
        with self.connect() as db:
            db.execute('DELETE FROM account_sessions WHERE expires_at<=?',(now,))
            db.execute('INSERT INTO account_sessions VALUES(?,?,?,?)',(self.digest(token),row['id'],now+SESSION_SECONDS,now))
            db.execute('''DELETE FROM account_sessions WHERE account_id=? AND digest NOT IN
                (SELECT digest FROM account_sessions WHERE account_id=? ORDER BY created_at DESC LIMIT 5)''',(row['id'],row['id']))
        return {'access_token':token,'account':self.public_account(row),'expires_in':SESSION_SECONDS}

    def session(self,token):
        if not isinstance(token,str) or not re.fullmatch(r'spc_[A-Za-z0-9_-]{40,100}',token):
            raise AccessError(401,'Inicia sesión para continuar.')
        with self.connect() as db:
            row=db.execute('''SELECT a.* FROM accounts a JOIN account_sessions s ON a.id=s.account_id
                WHERE s.digest=? AND s.expires_at>?''',(self.digest(token),time.time())).fetchone()
        if not row: raise AccessError(401,'Tu sesión venció. Vuelve a iniciar sesión.')
        if row['status']=='blocked': raise AccessError(403,'Tu acceso está bloqueado. Contacta con el administrador.')
        return self.public_account(row)

    def logout(self,token):
        with self.connect() as db: db.execute('DELETE FROM account_sessions WHERE digest=?',(self.digest(token),))

    def bootstrap_owner(self,session_token,legacy_code,owner_name):
        account=self.session(session_token)
        if not owner_name: raise AccessError(403,'La configuración de administrador no está habilitada.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner=db.execute('SELECT name,active FROM users WHERE digest=?',(self.digest(str(legacy_code)),)).fetchone()
            if not owner or not owner['active'] or owner['name']!=owner_name:
                raise AccessError(403,'El código de propietario no es válido.')
            if db.execute("SELECT 1 FROM accounts WHERE role='admin'").fetchone():
                raise AccessError(409,'El administrador ya está configurado.')
            db.execute("UPDATE accounts SET role='admin',status='active',access_reason='manual' WHERE id=?",(account['id'],))
            db.execute('UPDATE users SET active=1 WHERE name=?',('account:'+account['id'],))
        return self.session(session_token)

    def list_accounts(self,token):
        if self.session(token)['role']!='admin': raise AccessError(403,'Solo el administrador puede entrar aquí.')
        with self.connect() as db:
            return [self.public_account(row)|{'daily_limit':row['daily_limit'],'requests':row['requests']} for row in db.execute('''
                SELECT a.*,u.daily_limit,COALESCE(s.requests,0) AS requests FROM accounts a
                JOIN users u ON u.name='account:' || a.id
                LEFT JOIN usage s ON s.name=u.name AND s.bucket=? ORDER BY a.created_at DESC LIMIT 500''',(self.day(),))]

    def set_access(self,token,account_id,action,limit=600):
        admin=self.session(token)
        if admin['role']!='admin': raise AccessError(403,'Solo el administrador puede cambiar accesos.')
        if action not in ('approve','block') or type(limit) is not int or not 1<=limit<=10000:
            raise AccessError(400,'Acción o límite no válido.')
        if account_id==admin['id']: raise AccessError(400,'No puedes cambiar tu propio acceso desde aquí.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(account_id,)).fetchone():
                raise AccessError(404,'La cuenta no existe.')
            db.execute('UPDATE accounts SET status=?,access_reason=? WHERE id=?',
                       ('active' if action=='approve' else 'blocked','manual' if action=='approve' else None,account_id))
            db.execute('UPDATE users SET active=?,daily_limit=? WHERE name=?',(int(action=='approve'),limit,'account:'+account_id))
            if action=='block': db.execute('DELETE FROM account_sessions WHERE account_id=?',(account_id,))
