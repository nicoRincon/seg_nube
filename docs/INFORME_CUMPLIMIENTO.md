# Informe de cumplimiento — Goldilocks CTF

Evaluación del proyecto contra la rúbrica del curso. `✅` cumplido y verificado
· `⚠` parcial / con huecos · `❌` falta · `❓` ambiguo, requiere definición del
equipo.

**Equipo:** Angelica Olier, Johan Martinez, Nicolas Rincon (Universidad de
Cundinamarca).

---

## 1. Docker montado + arquitectura

**Tipo de arquitectura:** *Capture The Flag* (captura de bandera) — no es
estilo "troll"/escape room. Temática: el cuento de Ricitos de Oro y los Tres
Osos (3 fases: Bosque → Casa → Habitaciones).

| Componente del rubric | Estado |
|---|---|
| Máquina atacante: Kali Linux | ✅ Configurada, probada, en red Host-Only |
| Máquina objetivo: Ubuntu/Linux en VirtualBox o Docker | ⚠ La app solo corre hoy en el equipo de desarrollo (Windows). **No se ha desplegado aún en una VM/contenedor Linux objetivo separado** — esto es justo lo que `docs/DIRECCION_PROYECTO.md` (sección K) marca como pendiente |
| Red interna de VirtualBox | ✅ Host-Only `192.168.56.0/24`, aislada, probada con tráfico real |
| Aplicación web (portal de retos) | ✅ Goldilocks CTF — 12 retos, temporizador, pistas, marcador |
| Docker (contenedor con los retos) | ⚠ `Dockerfile` + `compose.yaml` existen (PR de Nicolas), pero: le falta instalar `steghide`, correr `setup_db.py` en el build, no corre con usuario sin privilegios (root por defecto), y **nunca se ha construido/ejecutado realmente** fuera del diseño |

**Cómo se montó / por qué:** pendiente de documentar formalmente una vez se
complete el despliegue real (ver huecos arriba). Hoy solo existe el diseño.

---

## 2. Puertos habilitados

**⚠ Los puertos reales de nuestra arquitectura NO son 22/80/8080** como lista
el rubric genérico — son distintos porque la app corre en Flask, no en un
servidor web tradicional con SSH expuesto:

| Puerto | Servicio | Dónde |
|---|---|---|
| `5000/tcp` | App Flask (Goldilocks CTF) | Máquina objetivo |
| `1337/tcp` | Banner falso del reto 1 (Nmap) | Metasploitable2 |
| `21/tcp` | vsftpd 2.3.4 (backdoor, reto 10) | Metasploitable2 |
| `8080/tcp` | Receptor del beacon del reto 4 (Wireshark) | **Kali** (no el objetivo) |
| `22/tcp`, `80/tcp` | Por defecto en Metasploitable2, no usados por ningún reto propio | Metasploitable2 |

✅ Validado con `nmap -sV -p 1337` (reto 1) y conexión real (reto 10) —
**❌ falta** un escaneo formal `nmap -sV -p-` completo documentado con
captura, como evidencia, y la justificación por escrito de por qué se usan
estos puertos y no 22/80/8080.

---

## 3. Documentación de retos (nombre, categoría, objetivo, justificación, herramientas, procedimiento, resultado)

✅ Existe `SOLUCIONARIO.md` con nombre, técnica, payloads exactos y comandos
para los 12 retos.
❌ Falta estructurarlo en el formato de tabla que pide el rubric (columna
explícita de **justificación** de por qué se eligió cada vulnerabilidad, y
**evidencia** en capturas de pantalla por reto — hoy es texto, no hay
imágenes anexas).

---

## 4. Categorías de reto por relevancia

| Categoría del rubric | Reto(s) que la cubre | Estado |
|---|---|---|
| Reconocimiento | 1 — Nmap | ✅ |
| Búsqueda pasiva de información | 2 — Dork, 4 — Wireshark | ✅ |
| Enumeración web | 3 — Dirb | ✅ |
| Análisis HTTP | 4 — Wireshark, 7 — XSS reflejado | ✅ |
| Gestión de sesiones | 5 — SQLi login, 11 — PrivEsc (cookie) | ✅ |
| File upload | 9 — Webshell | ✅ |
| Inyección de comandos | 9 — Webshell (RCE vía `?cmd=`) | ✅ |
| Esteganografía | 12 — Stego | ⚠ el mecanismo existe, pero hoy no usa steghide real (ver §1) |
| XSS | 7 — Reflejado, 8 — Almacenado | ✅ |
| Linux | 10 — Metasploit, 11 — PrivEsc | ⚠ el 10 es privesc/shell real; el 11 hoy es **simulado** (cookie de sesión), no hay sudo/SUID real todavía |
| **Docker** | — ninguno | ❓ **No hay ningún reto temático sobre seguridad de contenedores.** Hace falta definir si el rubric pide esto como *infraestructura* (la app corre en Docker) o como *categoría de reto* (ej. escape de contenedor, API de Docker expuesta). Si es lo segundo, no existe todavía y habría que diseñarlo. |

No listada en el rubric pero presente en el proyecto: **SQL Injection**
(retos 5 y 6) — vale la pena mencionarlo aparte en el informe aunque no
tenga casilla propia en la rúbrica.

---

## 5. Demostración práctica de cada reto

| Reto | Demostrado con evidencia real en esta sesión |
|---|---|
| 1 — Nmap | ✅ (captura `nmap -sV`, banner con flag) |
| 4 — Wireshark | ✅ (captura Follow HTTP Stream, Base64 decodificado) |
| 10 — Metasploit | ✅ (sesión meterpreter real, flag plantada y leída) |
| 2, 3, 5, 6, 7, 8, 9, 11, 12 | ⚠ verificados funcionalmente por HTTP (`curl`) durante el desarrollo, pero **sin capturas de "jugador" resolviéndolos** como evidencia formal |

---

## 6-8. Planteamiento / Resolución / Validación

✅ Cada reto tiene, en su propia página: "Misión" (planteamiento), pistas con
pasos (resolución) y un formulario de envío de bandera (validación) — está
en el diseño de la app, pero **no está consolidado en un documento de
informe único**; hoy vive repartido entre el código y `SOLUCIONARIO.md`.

---

## 9. Sistema de pistas

✅ Implementado: "Páginas del Cuento Perdido", 2 pistas por reto, cada una
cuesta −5 min / −25 pts, se descuenta del cronómetro y del puntaje en vivo.

---

## Preguntas de arquitectura

| Pregunta | Respuesta |
|---|---|
| ¿Cada reto tiene bandera independiente? | ✅ Sí, 12 banderas, 75 pts cada una |
| ¿Las banderas permiten avanzar de nivel? | ❓ No hay bloqueo real entre fases — los 12 retos están disponibles desde el inicio, sin progresión obligatoria. Si el rubric exige gating secuencial, **falta implementarlo** |
| ¿Existe una bandera final? | ❌ No hay una bandera "maestra" que combine las 12; el cierre es completar todas y ver el marcador final |
| ¿Cómo se valida que una bandera es correcta? | ✅ Comparación exacta contra un diccionario de banderas en el backend (`submit_flag`) |
| ¿Qué sucede si el jugador introduce una incorrecta? | ✅ Sube el "nivel de detección de los osos" (+8%), mensaje de error; si detección llega a 100% o se acaba el tiempo → pantalla de derrota |

---

## Seguridad y aislamiento

| Regla | Estado |
|---|---|
| Red de laboratorio aislada | ✅ Host-Only, nunca bridged, confirmado funcionando |
| Vulnerabilidades solo en el entorno CTF | ⚠ Hoy la app corre en el equipo de desarrollo (Windows) para programar — **falta moverla a la VM/contenedor objetivo** antes de considerarlo cumplido |
| Contenedores con permisos limitados | ❌ El `Dockerfile` corre como root (falta `USER` no-root) |
| No exponer servicios vulnerables a Internet | ✅ Todo en red interna, nunca público |
| No usar datos/credenciales reales | ✅ Todas las credenciales son ficticias del laboratorio |
| Snapshot/backup para restaurar | ✅ Metasploitable2 (instantánea tomada); ❌ Docker (sin volumen/snapshot documentado aún) |
| Nombres del equipo visibles | ⚠ Están en los commits de git; falta confirmarlos explícitamente en la entrega/documentación final |

---

## Resumen de lo que falta (acción concreta)

1. Desplegar realmente la app en una VM o contenedor Linux objetivo (hoy solo corre en el equipo de desarrollo).
2. Completar el `Dockerfile`: `steghide` + `setup_db.py` en el build + usuario no-root.
3. Decidir y documentar el reto/sección de **Docker** del rubric (infraestructura vs. reto temático).
4. Captura de evidencia (capturas de pantalla) para los 9 retos que faltan.
5. Definir si debe existir progresión entre fases y/o una bandera final, o justificar por qué el diseño actual (12 banderas independientes) cumple igual.
6. Escaneo `nmap -sV -p-` completo documentado como evidencia de puertos.
7. Reestructurar `SOLUCIONARIO.md` al formato de tabla pedido (añadiendo justificación).
