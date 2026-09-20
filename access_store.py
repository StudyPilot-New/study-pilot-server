"""Revocable access codes and atomic request quotas. Never stores raw codes."""
import hashlib
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager


class AccessError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class AccessStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                  name TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
                  active INTEGER NOT NULL DEFAULT 1, daily_limit INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS usage (
                  bucket TEXT NOT NULL, name TEXT NOT NULL,
                  requests INTEGER NOT NULL DEFAULT 0,
                  input_tokens INTEGER NOT NULL DEFAULT 0,
                  output_tokens INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(bucket,name));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def day(now=None):
        return 'D:' + datetime.fromtimestamp(time.time() if now is None else now, timezone.utc).strftime('%Y-%m-%d')

    def add(self, name, limit=600):
        if not name.strip() or len(name)>80 or name=='*' or any(ord(c)<32 for c in name):
            raise ValueError('Nombre no válido.')
        if not 1 <= limit <= 10000: raise ValueError('El límite debe estar entre 1 y 10000.')
        token = 'spc_' + secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO users(name,digest,daily_limit) VALUES(?,?,?)', (name,self.digest(token),limit))
        return token

    def revoke(self, name):
        with self.connect() as db:
            return db.execute('UPDATE users SET active=0 WHERE name=?',(name,)).rowcount

    def authenticate(self, token, db=None):
        if db is None:
            with self.connect() as connection: return self.authenticate(token,connection)
        row = db.execute('SELECT name,active,daily_limit FROM users WHERE digest=?',(self.digest(token),)).fetchone()
        if not row or not row['active']: raise AccessError(401,'Código inválido o revocado. Contacta con el administrador.')
        return dict(row)

    def reserve(self, token, global_limit, minute_limit=20, now=None):
        now = time.time() if now is None else now
        day = self.day(now)
        minute = 'M:' + str(int(now//60))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = self.authenticate(token,db)
            for bucket,name,limit in ((day,user['name'],user['daily_limit']), (day,'*',global_limit), (minute,user['name'],minute_limit)):
                count = db.execute('SELECT requests FROM usage WHERE bucket=? AND name=?',(bucket,name)).fetchone()
                if count and count['requests'] >= limit:
                    raise AccessError(429,'Límite de uso alcanzado. Espera o contacta con el administrador.')
            for bucket,name in ((day,user['name']), (day,'*'), (minute,user['name'])):
                db.execute('INSERT INTO usage(bucket,name,requests) VALUES(?,?,1) ON CONFLICT(bucket,name) DO UPDATE SET requests=requests+1',(bucket,name))
            db.execute("DELETE FROM usage WHERE bucket LIKE 'M:%' AND CAST(SUBSTR(bucket,3) AS INTEGER) < ?",(int(now//60)-2,))
        return user['name'],day

    def record_tokens(self, name, day, input_tokens, output_tokens):
        with self.connect() as db:
            for user in (name,'*'):
                db.execute('UPDATE usage SET input_tokens=input_tokens+?, output_tokens=output_tokens+? WHERE bucket=? AND name=?',
                           (max(0,input_tokens),max(0,output_tokens),day,user))

    def report(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('''SELECT u.name,u.active,u.daily_limit,
                COALESCE(s.requests,0) AS requests, COALESCE(s.input_tokens,0) AS input_tokens,
                COALESCE(s.output_tokens,0) AS output_tokens
                FROM users u LEFT JOIN usage s ON s.name=u.name AND s.bucket=? ORDER BY u.name''',(self.day(),))]
