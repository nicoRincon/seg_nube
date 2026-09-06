"""
Goldilocks CTF — Script de configuración inicial
Ejecutar una sola vez: python setup_db.py

Crea: base de datos (usuarios + recetas + puntajes), archivos de flags,
archivo expuesto para el reto de dorks, imagen para esteganografía.
"""

import os
import sqlite3
import hashlib
import shutil

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'goldilocks.db')
FLAGS_DIR = os.path.join(BASE_DIR, 'flags')
IMG_DIR   = os.path.join(BASE_DIR, 'static', 'img')
DOCS_DIR  = os.path.join(BASE_DIR, 'static', 'docs')

for d in (FLAGS_DIR, IMG_DIR, DOCS_DIR):
    os.makedirs(d, exist_ok=True)

# ── Flags · 12 banderas / 3 fases ──────────────────────
FLAGS = {
    'nmap':          'CTF{osito_bosque_nmap_hosts_activos}',
    'dork':          'CTF{mama_bosque_dork_archivo_expuesto}',
    'dirb':          'CTF{papa_bosque_dirb_ruta_oculta}',
    'wireshark':     'CTF{ricitos_bosque_wireshark_credenciales}',
    'sqli_login':    'CTF{osito_casa_sqli_bypass_login}',
    'sqli_medium':   'CTF{mama_casa_sqli_burp_medium}',
    'xss_reflected': 'CTF{papa_casa_xss_reflected_cookie}',
    'xss_stored':    'CTF{ricitos_casa_xss_stored_beef_hook}',
    'webshell':      'CTF{papa_habitacion_webshell_rce}',
    'metasploit':    'CTF{mama_habitacion_metasploit_exploit}',
    'privesc':       'CTF{osito_habitacion_privesc_root}',
    'stego':         'CTF{ricitos_habitacion_steghide_final}',
}

# ── Archivos de flags leídos vía RCE / sistema ─────────
with open(os.path.join(FLAGS_DIR, 'papa_oso.txt'), 'w') as f:
    f.write(FLAGS['webshell'] + '\n')

# compatibilidad con material previo
with open(os.path.join(FLAGS_DIR, 'mama_osa.txt'), 'w') as f:
    f.write(FLAGS['webshell'] + '\n')

with open(os.path.join(FLAGS_DIR, 'mensaje_oculto.txt'), 'w') as f:
    f.write(f"Los tres osos regresan al amanecer.\nFLAG: {FLAGS['stego']}\n")

# ── Archivo expuesto para el reto de Google Dorks ──────
with open(os.path.join(DOCS_DIR, 'informe_seguridad_osos.txt'), 'w', encoding='utf-8') as f:
    f.write(
        "INFORME INTERNO DE SEGURIDAD — CASA DE LOS TRES OSOS\n"
        "Clasificación: CONFIDENCIAL · No publicar\n"
        "----------------------------------------------------\n"
        "1. La cerradura de la puerta principal sigue siendo débil.\n"
        "2. La ventana de la cocina no cierra bien.\n"
        "3. Ricitos de Oro fue vista rondando el bosque.\n\n"
        f"Token de auditoría: {FLAGS['dork']}\n"
    )

print("[+] Archivos de flags y documento expuesto escritos.")

# ── Base de datos ──────────────────────────────────────
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

db = sqlite3.connect(DB_PATH)

db.execute("""
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    UNIQUE NOT NULL,
    password TEXT    NOT NULL,
    role     TEXT    DEFAULT 'guest'
)
""")

db.execute("""
CREATE TABLE recipes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    ingredient  TEXT NOT NULL,
    description TEXT,
    secret      TEXT
)
""")

db.execute("""
CREATE TABLE scores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT,
    challenge TEXT,
    pts       INTEGER,
    UNIQUE(username, challenge)
)
""")
db.commit()

def sha(p):
    return hashlib.sha256(p.encode()).hexdigest()

users = [
    ('admin',     sha('OsoPapa2026!'),   'admin'),
    ('ricitos',   sha('rizos123'),       'guest'),
    ('mama_osa',  sha('avena_caliente'), 'guest'),
    ('osito',     sha('miel'),           'guest'),
    ('visitante', sha('1234'),           'guest'),
]
for u in users:
    db.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)', u)

recipes = [
    ('Avena de Papá Oso',     'avena',      'Demasiado caliente para comer.',   None),
    ('Avena de Mamá Osa',     'avena',      'Demasiado fría para comer.',       None),
    ('Avena de Osito',        'avena',      'Estaba perfecta. Ricitos la comió toda.', None),
    ('Miel del Bosque',       'miel',       'Endulzante natural de las colmenas.', None),
    ('Frambuesas Silvestres', 'frambuesas', 'Pequeñas y ácidas, perfectas para la avena.', None),
    ('REGISTRO_CONFIDENCIAL',  '***',       'Solo visible vía inyección SQL.',
     FLAGS['sqli_medium']),
]
for r in recipes:
    db.execute('INSERT INTO recipes (name, ingredient, description, secret) VALUES (?,?,?,?)', r)

db.commit()
db.close()
print("[+] Base de datos inicializada (usuarios + recetas + puntajes).")

# ── Imagen para esteganografía ─────────────────────────
img_path = os.path.join(IMG_DIR, 'cuadro_del_pasillo.png')
try:
    from PIL import Image, ImageDraw

    W, H = 400, 300
    img  = Image.new('RGB', (W, H), color='#2c1a0e')
    d    = ImageDraw.Draw(img)
    for i in range(5):
        x = 40 + i * 70
        d.rectangle([x, 80, x + 20, 240], fill='#1a3a1a')
        d.ellipse([x - 15, 60, x + 35, 110], fill='#2d5a2d')
    d.rectangle([140, 160, 260, 240], fill='#8b4513')
    d.polygon([(130, 160), (200, 110), (270, 160)], fill='#5a2d0c')
    d.rectangle([175, 195, 205, 240], fill='#4a2000')
    d.ellipse([220, 170, 250, 200], fill='#d4a017')
    d.ellipse([320, 20, 370, 70], fill='#f0e68c')
    d.rectangle([0, 0, W - 1, H - 1], outline='#8b6914', width=8)
    d.rectangle([8, 8, W - 9, H - 9], outline='#d4a017', width=2)
    d.text((10, H - 30), "Casa de los Tres Osos - 2026", fill='#8a7255')
    img.save(img_path)
    print(f"[+] Imagen creada: {img_path}")
except ImportError:
    import struct, zlib

    def make_minimal_png(path, w=200, h=150):
        def chunk(name, data):
            c = struct.pack('>I', len(data)) + name + data
            return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
        sig  = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
        raw  = b''
        for y in range(h):
            raw += b'\x00' + b''.join(
                bytes([int(44 + 150 * x / w), int(26 + 80 * y / h), 14]) for x in range(w))
        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        with open(path, 'wb') as fh:
            fh.write(sig + ihdr + idat + iend)

    make_minimal_png(img_path)
    print(f"[+] PNG mínimo creado: {img_path}")

# ── Embeber flag con steghide si está disponible ───────
flag_txt = os.path.join(FLAGS_DIR, 'mensaje_oculto.txt')
jpg_path = img_path.replace('.png', '_stego.jpg')

if shutil.which('steghide'):
    try:
        try:
            from PIL import Image as PILImage
            PILImage.open(img_path).convert('RGB').save(jpg_path, 'JPEG', quality=95)
            base_img = jpg_path
        except ImportError:
            base_img = img_path
        import subprocess
        r = subprocess.run(
            ['steghide', 'embed', '-cf', base_img, '-sf', flag_txt,
             '-p', 'ricitos', '-f'], capture_output=True, text=True)
        if r.returncode == 0:
            shutil.copy(base_img, img_path.replace('.png', '_con_flag.jpg'))
            print("[+] Flag embebida con steghide. Contraseña: ricitos")
        else:
            print(f"[!] steghide falló: {r.stderr.strip()}")
    except Exception as e:
        print(f"[!] Error con steghide: {e}")
else:
    with open(img_path, 'ab') as fh:
        fh.write(b'\n# ' + FLAGS['stego'].encode() + b'\n')
    print("[!] steghide no encontrado. Flag añadida al final del PNG.")
    print("    Alternativa: strings cuadro_del_pasillo.png | grep CTF")

print("\n" + "=" * 52)
print("  Goldilocks CTF - Setup completado")
print("=" * 52)
print("  Ejecutar: python app.py  ->  http://localhost:5000\n")
print("  Credenciales de prueba:")
print("    ricitos / rizos123   |   admin / OsoPapa2026!")
print("    Bypass SQLi (login):  usuario = admin'--   password = (cualquiera)\n")
print("  Flags:")
for k, v in FLAGS.items():
    print(f"    {k:14s}: {v}")
print()
