"""
RicitosFlow CTF — Prólogo «El Guardián del Cernícalo» (VULNERABLE A PROPÓSITO)

Base: cernicalo.db, exclusiva de este laboratorio y con datos ficticios.
No contiene participantes, puntuaciones ni datos de otros retos.

La consulta del Guardián concatena la entrada del jugador: es una inyección
SQL deliberada. Para que no salga del laboratorio se ejecuta así:
- conexión de solo lectura (mode=ro) y PRAGMA query_only;
- autorizador de SQLite: solo SELECT, lecturas de las tablas del laboratorio
  y una lista blanca de funciones (sin ATTACH, PRAGMA ni escrituras);
- una sola sentencia por ejecución (el driver rechaza las apiladas);
- límite de longitud de la entrada y de operaciones de la máquina virtual.
Este módulo no ejecuta comandos ni abre otros archivos.
"""

import os
import secrets
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1
FLAG           = 'CTF{cernicalo_guardian_puerta_del_bosque}'
MAX_INPUT      = 120          # caracteres por campo
MAX_ROWS       = 5            # filas que se muestran
PROGRESS_STEP  = 1000         # instrucciones de SQLite entre comprobaciones
MAX_PROGRESS   = 200          # ≈ 200 000 instrucciones como máximo

QUERY_TEMPLATE = ("SELECT vigia, rango FROM vigias "
                  "WHERE vigia = '{vigia}' AND santo_y_sena = '{santo}'")

LAB_TABLES = {'vigias', 'bitacora'}
ALLOWED_FUNCTIONS = {
    'lower', 'upper', 'length', 'substr', 'substring', 'trim', 'ltrim', 'rtrim',
    'replace', 'instr', 'abs', 'coalesce', 'ifnull', 'nullif', 'typeof',
    'count', 'min', 'max', 'sum', 'avg', 'group_concat', 'like', 'glob',
}

_SQLITE_FUNCTION = getattr(sqlite3, 'SQLITE_FUNCTION', 31)


def init_db(path):
    """Crea cernicalo.db si falta o si cambió su versión. Es desechable:
    no guarda progreso de nadie (eso vive en participants.db)."""
    if os.path.exists(path):
        db = sqlite3.connect(path)
        try:
            if db.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION:
                return
        finally:
            db.close()

    db = sqlite3.connect(path)
    try:
        db.executescript("""
            DROP TABLE IF EXISTS vigias;
            DROP TABLE IF EXISTS bitacora;
            CREATE TABLE vigias (
                id           INTEGER PRIMARY KEY,
                vigia        TEXT NOT NULL,
                rango        TEXT NOT NULL,
                santo_y_sena TEXT NOT NULL
            );
            CREATE TABLE bitacora (
                id    INTEGER PRIMARY KEY,
                vigia TEXT NOT NULL,
                nota  TEXT NOT NULL
            );
        """)
        # Santo y seña aleatorio en cada instalación: no está en el repositorio.
        vigias = [
            ('cernicalo',         'Guardián de la puerta'),
            ('lechuza',           'Vigía de la noche'),
            ('pajaro_carpintero', 'Centinela del roble'),
            ('ardilla',           'Mensajera del bosque'),
        ]
        db.executemany('INSERT INTO vigias (vigia, rango, santo_y_sena) VALUES (?,?,?)',
                       [(v, r, secrets.token_hex(16)) for v, r in vigias])
        db.executemany('INSERT INTO bitacora (vigia, nota) VALUES (?,?)', [
            ('cernicalo', 'Nadie cruza sin decir su nombre de vigía y su santo y seña.'),
            ('lechuza',   'El libro de la puerta compara las palabras tal como se escriben.'),
            ('ardilla',   'Hoy cambiaron todos los santos y señas. Nadie se los sabe.'),
        ])
        db.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        db.commit()
    finally:
        db.close()


def build_query(vigia, santo):
    """⚠ Concatenación deliberada: aquí está la vulnerabilidad del reto."""
    return QUERY_TEMPLATE.format(vigia=vigia, santo=santo)


def _authorizer(action, arg1, arg2, db_name, trigger):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        # db_name llega vacío en lecturas sin columna (p. ej. count(*)); la conexión
        # solo tiene cernicalo.db, así que basta con limitar el nombre de la tabla.
        ok = db_name in ('main', None) and arg1 in LAB_TABLES
        return sqlite3.SQLITE_OK if ok else sqlite3.SQLITE_DENY
    if action == _SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK if (arg2 or '').lower() in ALLOWED_FUNCTIONS else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY


def _friendly_error(exc):
    msg = str(exc)
    if 'interrupted' in msg:
        return 'La consulta tardó demasiado y el Guardián la interrumpió.'
    if 'not authorized' in msg or 'prohibited' in msg:
        return 'El Guardián no permite esa operación: solo atiende consultas de lectura sobre su libro.'
    if 'one statement' in msg:
        return 'El Guardián solo atiende una consulta a la vez.'
    if 'readonly' in msg or 'read-only' in msg:
        return 'El libro del Guardián es de solo lectura.'
    return f'Error SQL: {msg}'


def run_guardian_query(path, vigia, santo):
    """Ejecuta la consulta vulnerable en un entorno restringido.
    Devuelve {'query', 'columns', 'rows', 'error', 'passed'}."""
    vigia = vigia or ''
    santo = santo or ''
    result = {'query': None, 'columns': [], 'rows': [], 'error': None, 'passed': False}

    if len(vigia) > MAX_INPUT or len(santo) > MAX_INPUT:
        result['error'] = f'Cada campo admite como máximo {MAX_INPUT} caracteres.'
        return result

    query = build_query(vigia, santo)
    result['query'] = query

    uri = Path(path).resolve().as_uri() + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True, timeout=2)
    ticks = {'n': 0}

    def _progress():
        ticks['n'] += 1
        return 1 if ticks['n'] > MAX_PROGRESS else 0   # distinto de 0 = abortar

    try:
        conn.execute('PRAGMA query_only = ON')
        conn.set_authorizer(_authorizer)
        conn.set_progress_handler(_progress, PROGRESS_STEP)
        cur = conn.execute(query)
        result['columns'] = [d[0] for d in (cur.description or [])]
        result['rows'] = [list(r) for r in cur.fetchmany(MAX_ROWS)]
        # Criterio de superación: la consulta devolvió al menos una fila.
        # El santo y seña real es aleatorio y no se publica: solo se entra por inyección.
        result['passed'] = bool(result['rows'])
    except (sqlite3.Error, sqlite3.Warning) as exc:
        result['error'] = _friendly_error(exc)
    finally:
        conn.close()
    return result
