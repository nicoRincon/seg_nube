"""
RicitosFlow CTF — Cuentas de participantes (operaciones SEGURAS)

Base: participants.db, independiente de goldilocks.db (retos y puntuaciones)
y de cernicalo.db (laboratorio SQL Injection del Guardián).

Reglas de este módulo:
- Solo consultas parametrizadas. Ningún reto vulnerable usa esta base.
- Contraseñas con hash scrypt con sal (werkzeug.security, incluido en Flask).
- Las sesiones se guardan como hash SHA-256 del token: la cookie lleva el
  token y la base solo su huella.
"""

import hashlib
import re
import secrets
import sqlite3
import time

from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA_VERSION = 1
SESSION_TTL    = 12 * 3600                     # 12 h
USERNAME_RE    = re.compile(r'^[A-Za-z0-9_.-]{3,24}$')
PASSWORD_MIN   = 8
PASSWORD_MAX   = 128

# Hash de relleno: igualamos el coste de la verificación cuando el usuario no existe
_DUMMY_HASH = generate_password_hash('ricitosflow-relleno')


def _connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def _token_hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def init_db(path):
    """Crea el esquema si falta. Idempotente; no borra datos."""
    db = _connect(path)
    try:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version < 1:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS participants (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT    NOT NULL,
                    created_at    REAL    NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash     TEXT    PRIMARY KEY,
                    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                    created_at     REAL    NOT NULL,
                    expires_at     REAL    NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prologue (
                    participant_id INTEGER PRIMARY KEY REFERENCES participants(id) ON DELETE CASCADE,
                    attempts       INTEGER NOT NULL DEFAULT 0,
                    cleared_at     REAL
                );
                PRAGMA user_version = 1;
            """)
    finally:
        db.close()


# ── Registro ───────────────────────────────────────────
def validate_registration(username, password, confirm):
    """Devuelve un mensaje de error o None si los datos son válidos."""
    if not USERNAME_RE.match(username or ''):
        return ('El nombre debe tener entre 3 y 24 caracteres: letras sin tildes, '
                'números, punto, guion o guion bajo.')
    if len(password or '') < PASSWORD_MIN:
        return f'La contraseña debe tener al menos {PASSWORD_MIN} caracteres.'
    if len(password) > PASSWORD_MAX:
        return f'La contraseña no puede superar {PASSWORD_MAX} caracteres.'
    if password != confirm:
        return 'Las contraseñas no coinciden.'
    return None


def create_participant(path, username, password):
    """Crea la cuenta. Devuelve (id, None) o (None, mensaje de error)."""
    db = _connect(path)
    try:
        cur = db.execute(
            'INSERT INTO participants (username, password_hash, created_at) VALUES (?,?,?)',
            (username, generate_password_hash(password), time.time()))
        db.commit()
        return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, 'Ese nombre de explorador ya está registrado.'
    finally:
        db.close()


def username_exists(path, username):
    db = _connect(path)
    try:
        return db.execute('SELECT 1 FROM participants WHERE username = ?',
                          (username,)).fetchone() is not None
    finally:
        db.close()


# ── Inicio de sesión ───────────────────────────────────
def authenticate(path, username, password):
    """Devuelve el participante si las credenciales son válidas; si no, None."""
    db = _connect(path)
    try:
        row = db.execute('SELECT id, username, password_hash FROM participants WHERE username = ?',
                         (username or '',)).fetchone()
    finally:
        db.close()
    if row is None:
        check_password_hash(_DUMMY_HASH, password or '')
        return None
    if not check_password_hash(row['password_hash'], password or ''):
        return None
    return {'id': row['id'], 'username': row['username']}


def create_session(path, participant_id):
    """Crea una sesión nueva y devuelve el token en claro (solo para la cookie)."""
    token = secrets.token_urlsafe(32)
    now = time.time()
    db = _connect(path)
    try:
        db.execute('DELETE FROM auth_sessions WHERE expires_at < ?', (now,))
        db.execute('INSERT INTO auth_sessions (token_hash, participant_id, created_at, expires_at) '
                   'VALUES (?,?,?,?)', (_token_hash(token), participant_id, now, now + SESSION_TTL))
        db.commit()
    finally:
        db.close()
    return token


def get_session_participant(path, token):
    """Participante dueño de un token vigente, con su estado del prólogo."""
    if not token:
        return None
    db = _connect(path)
    try:
        row = db.execute(
            'SELECT p.id, p.username, pr.cleared_at '
            'FROM auth_sessions s '
            'JOIN participants p ON p.id = s.participant_id '
            'LEFT JOIN prologue pr ON pr.participant_id = p.id '
            'WHERE s.token_hash = ? AND s.expires_at > ?',
            (_token_hash(token), time.time())).fetchone()
    finally:
        db.close()
    if row is None:
        return None
    return {'id': row['id'], 'username': row['username'],
            'prologue_cleared': row['cleared_at'] is not None}


def revoke_session(path, token):
    if not token:
        return
    db = _connect(path)
    try:
        db.execute('DELETE FROM auth_sessions WHERE token_hash = ?', (_token_hash(token),))
        db.commit()
    finally:
        db.close()


# ── Prólogo del Guardián ───────────────────────────────
def record_prologue_attempt(path, participant_id):
    db = _connect(path)
    try:
        db.execute('INSERT INTO prologue (participant_id, attempts) VALUES (?, 1) '
                   'ON CONFLICT(participant_id) DO UPDATE SET attempts = attempts + 1',
                   (participant_id,))
        db.commit()
    finally:
        db.close()


def prologue_cleared(path, participant_id):
    db = _connect(path)
    try:
        row = db.execute('SELECT cleared_at FROM prologue WHERE participant_id = ?',
                         (participant_id,)).fetchone()
    finally:
        db.close()
    return bool(row and row['cleared_at'] is not None)


def mark_prologue_cleared(path, participant_id):
    """Registra la superación del Guardián (solo la primera vez)."""
    db = _connect(path)
    try:
        db.execute('INSERT INTO prologue (participant_id, attempts, cleared_at) VALUES (?, 0, ?) '
                   'ON CONFLICT(participant_id) DO UPDATE SET '
                   'cleared_at = COALESCE(cleared_at, excluded.cleared_at)',
                   (participant_id, time.time()))
        db.commit()
    finally:
        db.close()
