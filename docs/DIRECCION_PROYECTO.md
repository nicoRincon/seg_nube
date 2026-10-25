# Goldilocks CTF — Documento de dirección del proyecto

> **Qué es este documento:** la referencia compartida del equipo para entender el estado real del proyecto, el diseño objetivo y las reglas de trabajo. Consúltalo antes de actualizar tu rama o empezar una tarea.
>
> **Convenciones**
> - **Verificado:** comprobado en el código del repositorio.
> - **Confirmado:** decisión aprobada por el equipo.
> - **Provisional:** propuesta o hipótesis que todavía hay que validar.
> - **Pendiente:** falta información o aprobación.
>
> Este documento no contiene banderas, contraseñas, claves de sesión ni otros secretos, y no debe contenerlos nunca.
>
> **Fecha de elaboración:** 25-10-2026. **Base:** rama `angelica` con cambios locales sin commit (ver B.6).
> **Actualizaciones (25-10-2026):** se añade la sección K, sobre la arquitectura de despliegue, y se actualiza con la infraestructura real confirmada (VirtualBox con una única VM de Kali).

---

## Índice

- A. Propósito y alcance
- B. Estado actual del proyecto
- C. Diseño narrativo definitivo
- D. Reglas de diseño visual
- E. Reglas de arquitectura y desarrollo
- F. Distribución de responsabilidades
- G. Restricciones y reglas de colaboración
- H. Plan de implementación por etapas
- I. Registro de decisiones y pendientes
- J. Criterios de aceptación
- K. Arquitectura de despliegue

---

## A. Propósito y alcance

**Goldilocks CTF** es una plataforma educativa de ciberseguridad en formato *Capture The Flag*, desarrollada para la Universidad de Cundinamarca y pensada **solo para entornos controlados** (así consta en `INSTALL.md` y en el pie de todas las páginas).

- **Temática:** el cuento de Ricitos de Oro y los tres osos. Ricitos es la intrusa que explora la casa; los osos representan a los defensores. El jugador resuelve retos, captura banderas y escapa antes de que se agote el tiempo o los osos lo detecten.
- **Propósito educativo:** practicar técnicas reales de reconocimiento, explotación web, escalada de privilegios y análisis forense en un laboratorio aislado.
- **Principio rector:** cada reto debe mantener la coherencia entre **la narrativa** (el momento del cuento), **la vulnerabilidad o técnica** que enseña y **la experiencia de juego** (pistas, interfaz, ilustración).

**Fuera del alcance de este documento:** requisitos institucionales o académicos que no estén en el repositorio, y funcionalidades que no existan ni hayan sido aprobadas.

---

## B. Estado actual del proyecto

### B.1 Arquitectura (verificado)

| Capa | Tecnología | Dónde |
|---|---|---|
| Backend | Python + Flask 3.0.3 | `app.py` (rutas, sesión, retos, puntuación) |
| Dependencias | Flask, Pillow | `requirements.txt` |
| Base de datos | SQLite (`goldilocks.db`) | Tablas `users`, `recipes`, `scores`, creadas por `setup_db.py` |
| Plantillas | Jinja2 | `templates/` (base, macros, portada, mapa, marcador, derrota, 12 retos) |
| Estilos | CSS único | `static/css/style.css` |
| Recursos | Imágenes y SVG | `static/img/` |
| Archivos del laboratorio | Banderas en archivo, documento expuesto, subidas | `flags/`, `static/docs/`, `uploads/` |
| Documentación existente | Instalación y solucionario | `INSTALL.md`, `SOLUCIONARIO.md` (**contienen información sensible**, ver B.5) |

**Estado de partida:** se guarda en la **sesión de Flask** (cookie firmada): inicio, penalizaciones, banderas resueltas, pistas abiertas, rol y nivel. Solo las puntuaciones de las banderas correctas se guardan en SQLite (`scores`).

### B.2 Rutas principales (verificado)

| Ruta | Función |
|---|---|
| `/` | Portada (`index.html`). Si hay partida en curso, redirige al mapa. |
| `POST /start` | Inicia la partida como invitado con el nombre escrito y arranca el cronómetro. |
| `/dashboard` | Mapa del bosque (`dashboard.html`). |
| `POST /hint/<cid>/<n>` | Desbloquea una pista (−5 min y −25 pts). |
| `POST /submit_flag` | Valida la bandera de un reto. |
| `/scoreboard` | Marcador. |
| `/reset`, `/logout`, `/set_level/<level>` | Reiniciar, salir, cambiar nivel (`low`/`medium`/`high`). |
| `/state.json` | Estado para el cronómetro del cliente. |
| `/lose` | Pantalla de derrota (tiempo agotado o detección al 100 %). |
| `/challenges/<reto>` | Una ruta por reto (ver B.4). |

**Reglas de juego implementadas** (en `app.py`):
- Cronómetro de 120 minutos.
- Cada pista resta 5 minutos y 25 puntos.
- Cada bandera incorrecta suma +8 % de detección; la detección también crece con el tiempo.
- Cada reto vale 75 puntos.

**Valores fijos que habrá que revisar** si cambia el número de retos:
- `TOTAL_POINTS = 900`.
- `g_total_ch = len(FLAGS)`.

### B.3 Fases actuales (verificado)

El código define **3 fases de 4 retos** (`PHASES` y `CHALLENGES_META` en `app.py`):

| Fase | Nombre | Etiqueta |
|---|---|---|
| 1 | El Bosque | Reconocimiento |
| 2 | La Casa | Explotación Web |
| 3 | Las Habitaciones | Escalada |

**No existe Fase 0:** la portada solo pide un nombre (no hay contraseña ni validación) y entra directamente al mapa.

### B.4 Retos actuales y estado real (verificado en la auditoría del código)

**Leyenda de estados:**
- **Implementado:** la técnica funciona contra la aplicación.
- **Con atajo:** funciona, pero la bandera se obtiene sin aplicar la técnica.
- **Parcial:** el mecanismo está incompleto.
- **Simulado:** solo se muestra la salida esperada.
- **Externo:** depende de otra máquina.

| # | id | Ruta y plantilla | Técnica | Estado | Notas técnicas |
|---|---|---|---|---|---|
| 1 | `nmap` | `/challenges/nmap` · `nmap.html` | Escaneo de puertos y servicios | **Simulado** | La página muestra el banner con la bandera. El escaneo real requiere el host del laboratorio. |
| 2 | `dork` | `/challenges/dork` · `dork.html` | `robots.txt` y documento expuesto | Implementado, **con atajo** | La página enlaza directamente el documento. Depende de `setup_db.py`. |
| 3 | `dirb` | `/challenges/dirb` + `/despensa_secreta` | Enumeración de rutas ocultas | Implementado | `/despensa_secreta` no exige partida iniciada. |
| 4 | `wireshark` | `/challenges/wireshark` + `/…/captura.pcap` | Credenciales Basic en claro | **Parcial** | El archivo es texto con extensión `.pcap`: Wireshark no lo abre. |
| 5 | `sqli_login` | `/challenges/sqli-login` | SQLi para saltar el login | Implementado | Consulta concatenada contra `users`. |
| 6 | `sqli_medium` | `/challenges/sqli-medium` | SQLi con filtro débil | Implementado | Solo filtra la comilla simple. **Por validar:** la documentación dice que el nivel afecta a este reto, pero la ruta no lee el nivel. |
| 7 | `xss_reflected` | `/challenges/xss-reflected` | XSS reflejado y robo de cookie | Implementado, **con atajo** | La cookie se pone al cargar la página y no es HttpOnly: se lee sin hacer el XSS. |
| 8 | `xss_stored` | `/challenges/xss-stored` + `/admin-bot` | XSS almacenado | **Parcial** | Comentarios en una lista global en memoria, compartida entre jugadores y borrada al reiniciar. El «bot» solo busca `<script`. |
| 9 | `webshell` | `/challenges/webshell` + `/uploads/<f>` | Subida de archivos y ejecución remota | Implementado (**riesgo crítico**) | Ejecuta comandos **en el servidor que aloja la app**. `uploads/shell.py` está versionado. El nivel controla los filtros. |
| 10 | `metasploit` | `/challenges/metasploit` | Exploit de un servicio vulnerable | **Externo** | Requiere la VM Metasploitable 2 del laboratorio con la bandera preparada. |
| 11 | `privesc` | `/challenges/privesc` + `/admin/config` | Falsificar la sesión para escalar privilegios | Implementado | `/admin/config` expone sin autenticación la configuración necesaria para firmar sesiones. |
| 12 | `stego` | `/challenges/stego` + `/download` | Esteganografía | Implementado, **con atajo** | La plantilla muestra los datos para extraer el mensaje. Depende de las imágenes que genera `setup_db.py`. |

### B.5 Riesgos técnicos detectados

| Riesgo | Gravedad | Detalle |
|---|---|---|
| Ejecución de comandos en el equipo anfitrión | **Crítica** | El reto `webshell` ejecuta comandos con los permisos del proceso Flask. Debe ejecutarse **solo** en el entorno de laboratorio autorizado (ver K.5 y K.6). |
| Secretos en la documentación | Alta | `INSTALL.md` y `SOLUCIONARIO.md` contienen credenciales y soluciones. No deben distribuirse a los jugadores ni copiarse en documentos compartidos. |
| Retos con atajos | Media | `nmap`, `dork`, `xss_reflected` y `stego` permiten obtener la bandera sin aplicar la técnica. |
| Estado compartido entre jugadores | Media | `xss_stored` usa una lista global en memoria. |
| Rutas sin control de partida | Baja (probablemente intencionado) | `/despensa_secreta`, `/admin`, `/admin/config`. |
| Dependencias externas | Media | VMs en 192.168.56.12 y .13, `steghide` opcional, ejecución previa de `setup_db.py`, rutas absolutas en algunas pistas. |
| Estructura de fases fija | Alta para el rediseño | Ver E.4: hay diccionarios cerrados de 3 fases en los macros y en varias plantillas. |

### B.6 Estado de Git y archivos compartidos (verificado)

**Ramas:**
- `main` (y `origin/main`).
- `angelica` (rama de trabajo visual, activa).
- `origin/feature/Johan`. Tiene un commit (`cd0e0d2`) que modifica `_macros.html`, `base.html`, `style.css`, `dashboard.html`, `index.html`, `lose.html` y `scoreboard.html`. **No modifica** `app.py` ni las plantillas de los retos.

**Cambios locales sin commit en `angelica`:**
- Modificados: `static/css/style.css`, `templates/base.html`, `templates/dashboard.html`, `templates/index.html`, `templates/challenges/nmap.html`.
- Nuevos: `static/img/icons/`, `static/img/storybook/`, `static/img/mapa_bosque.png`, `static/img/libro.png`.

**Archivos con riesgo de conflicto:** `base.html`, `_macros.html`, `style.css` y `dashboard.html`. Los modifican tanto `angelica` como `feature/Johan`.

### B.7 Interfaz visual implementada (verificado en `angelica`, sin commit)

| Pieza | Estado | Archivos |
|---|---|---|
| HUD ilustrado: logotipo, jugador, puntos, tiempo, banderas, nivel y accesos | Implementado | `base.html`, sección `HUD ILUSTRADO` de `style.css`, `static/img/icons/` |
| Accesos del HUD | Implementado | Mapa → `dashboard`, Inventario → panel de banderas capturadas (sin ruta nueva), Pistas → bloque de pistas del reto, Diario → `scoreboard`, Ajustes → nivel y reinicio, Salir → `logout` |
| Mapa ilustrado con 12 marcadores, ficha contextual, letreros de fase y estados pendiente/superado | Implementado | `dashboard.html` (`MAP_SPOTS`), `static/img/mapa_bosque.png`, iconos `map-lock.svg` y `map-check.svg` |
| Libro ilustrado para retos | **Piloto solo en `nmap`** | `nmap.html`, sección `STORYBOOK - NMAP` de `style.css`, `static/img/libro.png` |
| Ilustración del capítulo «La Sopa de Osito» | **Pendiente** | Prevista en `static/img/capitulos/sopa_osito.png`; el archivo **no existe todavía** |
| SVG decorativos del libro | Disponibles, parte sin uso | `static/img/storybook/` (se conservan por decisión del equipo) |
| Resto de retos (11) | Diseño anterior | `templates/challenges/*.html` |

---

## C. Diseño narrativo definitivo

### C.1 Estructura confirmada

El diseño objetivo tiene **15 retos conceptuales**:

| Fase | Nombre | Retos | Ubicación |
|---|---|---|---|
| 0 | La Entrada | 3 subretos | **Antes del mapa** (acceso inicial). **No cuentan** entre los 12 del mapa. |
| 1 | La Cocina | 3 | Mapa |
| 2 | La Sala de Estar | 3 | Mapa |
| 3 | Las Habitaciones | 3 | Mapa |
| 4 | La Fuga | 3 | Mapa |

Las fases 1 a 4 contienen **los 12 retos del mapa**.

### C.2 Matriz de retos

> **Pendiente de confirmación.** La matriz completa (códigos oficiales, nombres narrativos, vulnerabilidades, técnicas y objetivos técnicos) **no está disponible en el repositorio ni en el contexto de trabajo**. La tabla siguiente usa identificadores de casilla (`F0·1`…`F4·3`) que **no son los códigos oficiales**.
>
> Las columnas «Posible reto reutilizable» y «Encaje» son una **hipótesis basada solo en la narrativa del cuento**: sopas → cocina, sillas → sala, camas → habitaciones, regreso de los osos → fuga. Hay que verificarla con la matriz y en el código antes de usarla.

| Casilla | Código oficial | Nombre narrativo | Fase | Objetivo técnico | Estado de implementación | Posible reto reutilizable (provisional) | Encaje |
|---|---|---|---|---|---|---|---|
| F0·1 | Pendiente | Pendiente | 0 · La Entrada | Pendiente (reconocimiento o autenticación) | No existe | `wireshark` («El Camino al Bosque», credenciales en claro) | Por validar |
| F0·2 | Pendiente | Pendiente | 0 · La Entrada | Pendiente | No existe | `sqli_login` (barrera de login) **o** `dork` (`robots.txt`) | Por validar |
| F0·3 | Pendiente | Pendiente | 0 · La Entrada | Pendiente | No existe | Ninguno identificado | — |
| F1·1 | Pendiente | Pendiente | 1 · La Cocina | Pendiente | Por determinar | `nmap` («La Sopa de Osito») | Narrativo alto |
| F1·2 | Pendiente | Pendiente | 1 · La Cocina | Pendiente | Por determinar | `dork` («La Sopa de Mamá Osa») | Narrativo alto |
| F1·3 | Pendiente | Pendiente | 1 · La Cocina | Pendiente | Por determinar | `dirb` («La Sopa de Papá Oso») | Narrativo alto |
| F2·1 | Pendiente | Pendiente | 2 · La Sala de Estar | Pendiente | Por determinar | `xss_stored` («La Silla Rota») | Narrativo alto |
| F2·2 | Pendiente | Pendiente | 2 · La Sala de Estar | Pendiente | No existe (probable) | Ninguno identificado | — |
| F2·3 | Pendiente | Pendiente | 2 · La Sala de Estar | Pendiente | No existe (probable) | Ninguno identificado | — |
| F3·1 | Pendiente | Pendiente | 3 · Las Habitaciones | Pendiente | Por determinar | `sqli_login` («La Cama de Osito»), si no pasa a la Fase 0 | Narrativo alto |
| F3·2 | Pendiente | Pendiente | 3 · Las Habitaciones | Pendiente | Por determinar | `sqli_medium` («La Cama de Mamá Osa») | Narrativo alto |
| F3·3 | Pendiente | Pendiente | 3 · Las Habitaciones | Pendiente | Por determinar | `xss_reflected` («La Cama de Papá Oso») | Narrativo alto |
| F4·1 | Pendiente | Pendiente | 4 · La Fuga | Pendiente | Por determinar | `webshell` / `metasploit` / `privesc` («… Despierta») | Medio |
| F4·2 | Pendiente | Pendiente | 4 · La Fuga | Pendiente | Por determinar | (uno de los tres anteriores) | Medio |
| F4·3 | Pendiente | Pendiente | 4 · La Fuga | Pendiente | Por determinar | `stego` («¡Ricitos de Oro Escapa!») | Narrativo alto (final) |

**Consecuencias de la hipótesis, que hay que validar:**
- Sobra un reto de la familia «… Despierta» para la Fase 4.
- Faltan dos retos en la Sala de Estar.
- La Fase 0 necesita uno o dos subretos nuevos y todo el flujo previo al mapa.

---

## D. Reglas de diseño visual

### D.1 Decisiones confirmadas

1. **El mapa ilustrado** (`static/img/mapa_bosque.png`) es el escenario principal del dashboard.
2. **El libro ilustrado** (`static/img/libro.png`) es el escenario para presentar los retos.
3. **Fondos de imagen real:** el libro no se reconstruye con CSS (gradientes, bordes o formas).
4. **HTML real superpuesto:** textos, botones, formularios, indicadores y controles son HTML encima del escenario, nunca texto incrustado en una imagen. La consola y las banderas son texto seleccionable.
5. **Posiciones relativas:** sobre las imágenes se usan posiciones relativas al contenedor (en %), que se adaptan al tamaño de pantalla. Nada en píxeles respecto a la ventana.
6. **Escritorio:** se conserva el libro abierto, con la narración en la página izquierda y la interacción en la derecha. Si el contenido no cabe, primero se compacta y después se permite desplazamiento vertical **dentro** de la página, con una barra discreta.
7. **Móvil:** la imagen ilustrada va como cabecera y el contenido se organiza en bloques legibles debajo (en el piloto, con la textura real del pergamino de `libro.png`).
8. **Legibilidad:** no se reduce el texto hasta volverlo ilegible para que quepa en la ilustración.
9. **Coherencia:** el cuento, los nombres de los retos, las pistas, los objetivos y los gráficos deben contar lo mismo.
10. **Ilustraciones propias:** cada ilustración corresponde a su reto. No se reutilizan imágenes de otro desafío sin aprobación; por ejemplo, `cuadro_del_pasillo.png` pertenece a `stego`.
11. **Nada tapa lo funcional:** los adornos no ocultan formularios, mensajes de error o éxito ni controles.
12. **Placa del libro:** solo `{{ ch.name }}`; la fase y la categoría van debajo.
13. **HUD sin duplicados:** la puntuación y el tiempo no se repiten fuera de él.
14. **Marcadores del mapa:** pendiente = placa con candado, número, nombre y categoría; superado = insignia verde con ✓. El estado sale de los datos reales de la partida.
15. **Accesibilidad:** foco visible, contraste suficiente y respeto por `prefers-reduced-motion`.

### D.2 Propuestas pendientes de revisión visual

| Propuesta | Estado |
|---|---|
| Piloto del libro en `nmap` (composición y tamaños) | Pendiente de aprobación antes de replicarlo |
| Desplazamiento interno en la página derecha a 1440 px | Implementado en el piloto, pendiente de validar con usuarios |
| Nombres largos en la placa (por ejemplo, «¡Ricitos de Oro Escapa!») | Pendiente: puede requerir letra más pequeña |
| Candado en los retos pendientes (no existe bloqueo real) | Implementado; revisar si confunde a los jugadores |
| Emojis de los macros (🍜 📜 🚩 📖) en lugar de iconos ilustrados | Pendiente para la fase de integración |
| Etiquetas, letreros e iconos del mapa para una fase 4 | Pendiente de la nueva estructura |

---

## E. Reglas de arquitectura y desarrollo

1. **No duplicar** lógica, macros, estilos ni componentes compartidos sin necesidad. Antes de crear algo, buscar si ya existe.
2. **Separar capas:**
   - presentación → plantillas y CSS;
   - lógica de los retos → funciones de `app.py`;
   - rutas → decoradores de Flask;
   - persistencia → SQLite y sesión.
3. **Contratos estables.** No cambiar sin evaluar las dependencias:
   - identificadores de reto (`id`) y *endpoints*;
   - nombres de campos (`challenge`, `flag`, `username`, `password`, `ingredient`, `comment`, `file`, `nombre`, `cmd`);
   - variables de plantilla (`ch`, `banner`, `g_*`, `hint_cost_*`, `CHALLENGES`, `PHASES`);
   - estructura de las tablas.
4. **Cambiar el número o la distribución de fases** obliga a revisar a la vez:
   - `PHASES`, `CHALLENGES_META` y su orden (que define la navegación con `challenge_nav`), `CH_BY_ID` y `FLAGS` en `app.py`;
   - `TOTAL_POINTS` y `g_total_ch`;
   - `_macros.html` (`challenge_header` y `briefing` usan diccionarios cerrados `{1, 2, 3}`: **una fase 4 rompe el renderizado**);
   - `scoreboard.html` (colores por fase);
   - `dashboard.html` (`MAP_SPOTS`, `PHASE_LABELS`, iconos de los letreros);
   - la tabla `scores`, indexada por `(username, challenge)`: renombrar ids deja huérfanas las puntuaciones.
5. **Totales coherentes** con los datos reales. Valores fijos que hay que revisar (no se han cambiado): `TOTAL_POINTS = 900` y los textos «12 banderas · 3 fases · 900 puntos» de `INSTALL.md`.
6. **En tareas visuales no se tocan** banderas ni mecanismos de validación.
7. **Tras cualquier cambio de presentación** siguen funcionando: formularios, rutas, pistas, puntuación, estado de resolución y mensajes flash.
8. **Sin dependencias nuevas** sin justificar su necesidad y su compatibilidad.
9. **No eliminar recursos** gráficos o archivos sin confirmar que ya no se usan.
10. **No afirmar que una vulnerabilidad funciona** sin comprobarlo en su implementación.

---

## F. Distribución de responsabilidades

Las responsabilidades se definen **por área**. La asignación de personas la confirma el equipo.

| Área | Incluye |
|---|---|
| **Interfaz visual** | Estructura HTML de las páginas; CSS, composición y adaptación a pantallas; mapa, marcadores y libro ilustrado; presentación de narrativas, indicadores, formularios y mensajes; integración visual con los componentes existentes. |
| **Backend** | Rutas y controladores Flask; mecánicas de vulnerabilidad; sesiones y autenticación (incluida la Fase 0); banderas, validación y puntuación; base de datos y estado de la partida; dependencias con VMs y servicios externos (`setup_db.py`, Metasploitable, `steghide`). |
| **Componentes compartidos** (cambios coordinados y revisados antes de integrar) | `templates/base.html` (HUD, avisos flash, cronómetro); `templates/_macros.html` (misión, pistas, bandera, detección, navegación); `static/css/style.css` (secciones por vista: mapa, HUD, libro); `templates/dashboard.html` (depende de los ids de los retos y de las fases); `CHALLENGES_META` y `PHASES` en `app.py`, que alimentan tanto la lógica como la interfaz. |

---

## G. Restricciones y reglas de colaboración

**Git y trabajo ajeno**
- No borrar ni sobrescribir trabajo local de otros integrantes.
- No ejecutar `git reset --hard`, `git clean` ni comandos destructivos equivalentes.
- No hacer commits, merges, rebases, pushes ni cambios de rama sin autorización expresa.
- Antes de editar, revisar `git status` y los cambios existentes.
- No revertir cambios de otra persona para resolver un conflicto sin consultar al equipo.
- No tratar los componentes compartidos como si fueran exclusivos de una rama.

**Alcance de los cambios**
- No meter cambios de backend en una tarea visual sin autorización.
- No cambiar rutas, identificadores, banderas o esquemas de datos de forma incidental.

**Pruebas y seguridad**
- Probar sin usar datos reales que puedan dañarse: copias de la base de datos o estado solo en la sesión.
- Las vulnerabilidades deliberadas se quedan dentro del laboratorio aislado. La ejecución de comandos no debe poder comprometer el equipo anfitrión.
- No exponer secretos, credenciales, banderas ni información sensible en documentos compartidos.

**Regla de parada:** ante una ambigüedad que pueda afectar a otro integrante o romper funcionalidad, **detenerse y pedir confirmación** en lugar de suponer.

---

## H. Plan de implementación por etapas

No hay fechas ni asignaciones personales; ver la sección I.

| # | Etapa | Depende de | Criterio de finalización | Decisiones pendientes |
|---|---|---|---|---|
| 1 | Confirmar la matriz narrativa y los objetivos técnicos | — | La matriz de 15 retos está escrita en `docs/` y aprobada (códigos, nombres, técnica y objetivo de cada uno) | Contenido completo de la matriz |
| 2 | Auditar las correspondencias y decidir qué se reutiliza | 1 | Cada casilla de C.2 tiene asignado «reutilizar `id`», «adaptar» o «crear nuevo» | Qué reto «Despierta» sale; si `sqli_login` pasa a la Fase 0 |
| 3 | Acordar los cambios de arquitectura para las cinco fases | 2 | Diseño escrito de: `PHASES` con 4 fases de mapa, representación de la Fase 0, política de ids, totales calculados y estado de sesión previo al mapa | Ver I: Fase 0, cronómetro, puntuación, ids |
| 4 | Coordinar los archivos compartidos e integrar ramas | 3 | `feature/Johan` y `angelica` integradas sin conflictos pendientes, con la aplicación funcionando | Orden de la integración y quién la revisa |
| 5 | Reorganizar el backend | 4 | Fases y retos reasignados en `app.py`; navegación y totales correctos; ninguna ruta rota | Ninguna nueva si se cumplen 1 a 3 |
| 6 | Implementar o adaptar los retos que faltan | 5 | Cada reto nuevo o adaptado se resuelve en el laboratorio con la técnica prevista y sin atajos no deseados | Qué atajos actuales hay que eliminar |
| 7 | Adaptar la interfaz a la estructura definitiva | 5 (y 6 por cada reto) | Macros sin diccionarios cerrados; mapa con 4 fases; libro replicado en los retos estabilizados; ilustraciones propias | Aprobación del piloto del libro e ilustraciones de cada capítulo |
| 8 | Probar todo | 6 y 7 | Se cumplen los criterios de la sección J, con evidencias | Entorno de pruebas aislado |
| 9 | Integrar y validar el trabajo del equipo | 8 | Rama principal estable y documentación (`INSTALL.md`, este documento) actualizada | Responsable de la validación final |

---

## I. Registro de decisiones y pendientes

| Decisión o pregunta | Estado | Impacto | Aprueba (rol) |
|---|---|---|---|
| Estructura de 15 retos: Fase 0 (3, antes del mapa) + fases 1 a 4 (3 cada una, en el mapa) | Confirmada | Alto: cambia `PHASES`, macros, mapa, totales | Equipo completo |
| Contenido detallado de la matriz (códigos, nombres, técnicas, objetivos) | **Pendiente** | Bloquea las etapas 2 a 7 | Diseño narrativo y técnico (equipo) |
| Tratamiento de la Fase 0: retos independientes, pasos de un único login o mecánica nueva; si da banderas o puntos | **Pendiente** | Alto: sesión, rutas, `play_required`, portada | Backend + interfaz |
| Inicio del cronómetro (¿Fase 0 o entrada al mapa?) | **Pendiente** | Medio: `start_game`, HUD | Equipo |
| Reglas de puntuación (75 por reto; ¿la Fase 0 puntúa?; total calculado en vez de 900) | **Pendiente** | Medio: `TOTAL_POINTS`, HUD, marcador | Backend |
| Reutilizar o crear cada reto (tabla C.2) | Provisional | Alto | Equipo |
| Cambios de ids y rutas (recomendado: conservar ids y cambiar solo `name` y `phase`) | Provisional | Alto: `scores`, `FLAGS`, mapa, enlaces | Backend + interfaz |
| Responsable de cada archivo compartido (`base.html`, `_macros.html`, `style.css`, `dashboard.html`) | **Pendiente** | Alto: conflictos de integración | Equipo |
| Orden de integración de `feature/Johan` y `angelica` | **Pendiente** | Alto | Equipo |
| Infraestructura actual: VirtualBox con una única VM de Kali Linux (K.1) | Confirmada | Crítico | — |
| Arquitectura objetivo: Kali como atacante y una segunda VM objetivo, más Metasploitable 2 (K.2) | Provisional (propuesta) | Crítico | Equipo + docente responsable |
| Medidas de aislamiento y del reto `webshell` antes del despliegue (K.5, K.6) | **Pendiente** de aprobación | Crítico | Equipo + docente responsable |
| Docker como alternativa de instalación (K.4) | **Pendiente** de evaluación y pruebas | Medio | Equipo |
| Eliminar o mantener los atajos de `nmap`, `dork`, `xss_reflected` y `stego` | **Pendiente** | Medio: valor educativo | Backend |
| Distribución de `INSTALL.md` y `SOLUCIONARIO.md` (contienen secretos) | **Pendiente** | Alto | Equipo + docente |
| Libro ilustrado como escenario de los retos | Confirmada | Alto | Interfaz (aprobado) |
| Aprobación del piloto del libro en `nmap` antes de replicarlo | **Pendiente** | Medio | Equipo |
| Ilustración de cada capítulo (la primera: `static/img/capitulos/sopa_osito.png`, todavía no está) | Pendiente | Medio | Interfaz |
| Adaptar el mapa a 4 fases (coordenadas, letreros, etiquetas) | Pendiente (depende de la matriz) | Medio | Interfaz |
| Sustituir los emojis de los macros por iconos | Pendiente (fase de integración) | Bajo | Interfaz + responsable de los macros |

---

## J. Criterios de aceptación

El proyecto se considerará terminado cuando se compruebe, **con evidencias**, lo siguiente. A la fecha de este documento **ninguno de estos criterios está verificado** para la estructura definitiva.

| # | Criterio | Cómo se verifica |
|---|---|---|
| 1 | Correspondencia con la matriz | Cada uno de los 15 retos existe con el nombre, la fase, la técnica y el objetivo aprobados (tabla C.2 completa y revisada). |
| 2 | Fase 0 antes del mapa | No se puede llegar a `/dashboard` ni a los retos del mapa sin superar el acceso inicial definido. |
| 3 | Navegación completa | Desde el mapa se llega a los 12 retos; anterior y siguiente siguen el orden aprobado; el marcador, el panel y la salida funcionan. |
| 4 | Sin enlaces rotos | Todas las rutas enlazadas responden correctamente (prueba automatizada sobre las plantillas). |
| 5 | Formularios y pistas | En cada reto: bandera incorrecta (aviso y +detección), bandera correcta (estado capturado y enlace al siguiente) y pista (penalización y contenido visible). |
| 6 | Puntuación coherente | Los totales del HUD, del mapa y del marcador coinciden con el número real de retos y sus puntos; las penalizaciones se aplican una sola vez. |
| 7 | Legibilidad | Revisión a 1440 px y 400 px de ancho: sin desplazamiento horizontal, texto legible, controles usables y escenario alineado. |
| 8 | Accesibilidad básica | Navegación con teclado, foco visible, contraste suficiente y `prefers-reduced-motion` respetado. |
| 9 | Vulnerabilidades auténticas | Cada reto se resuelve con la técnica prevista y no con atajos no aprobados. |
| 10 | Seguridad del laboratorio | Las pruebas se hacen solo en el entorno autorizado (la VM objetivo de K.2 una vez validada, o la alternativa aprobada de K.4); la ejecución de comandos no afecta al anfitrión; ningún secreto aparece en documentos compartidos (detalle en K.9). |
| 11 | Integración | La rama principal integra el trabajo del equipo sin regresiones respecto a los criterios 3 a 7. |

---

## K. Arquitectura de despliegue

> **Contexto confirmado:** proyecto académico de seguridad en la nube y *hacking* ético. Las vulnerabilidades de los retos son **deliberadas** y forman parte de los objetivos educativos: no se eliminan indiscriminadamente; se **aíslan**.
>
> **Alcance de esta sección:** documenta decisiones, propuestas y criterios. **No** se ha creado ningún Dockerfile, máquina virtual ni archivo de despliegue, y no se ha cambiado código ni configuración.
>
> **Leyenda de esta sección:**
> - **Confirmado:** estado real comunicado por el equipo.
> - **Propuesto:** diseño objetivo pendiente de aprobación.
> - **No probado:** todavía no se ha verificado en ningún entorno.

### K.1 Infraestructura actual (confirmada, 25-10-2026)

| Elemento | Estado |
|---|---|
| Equipo anfitrión | Equipo personal de desarrollo (Windows), donde se edita el código. **No es un entorno autorizado para ejecutar las vulnerabilidades.** |
| Virtualización | **VirtualBox** |
| Máquinas virtuales | **Una sola VM: Kali Linux** |
| VM dedicada al servidor objetivo | **No existe todavía** |
| VM Metasploitable 2 | **No existe todavía** |
| Red *Host-Only* `192.168.56.0/24` (descrita en `INSTALL.md`) | **No configurada ni probada** en la infraestructura actual |
| Docker | **No implementado** (alternativa por evaluar, ver K.4) |

> **Consecuencia:** hoy no existe un entorno que reproduzca la topología de `INSTALL.md`. Dónde se ejecuta la aplicación con sus vulnerabilidades **mientras no exista la segunda VM** está **pendiente de decisión** (ver K.10). En cualquier caso, nunca en el equipo anfitrión ni en una red compartida.

### K.2 Arquitectura objetivo (propuesta)

Separar el **atacante** del **objetivo**, siguiendo la topología de referencia de `INSTALL.md`:

| Rol | Máquina | IP de referencia (`INSTALL.md`) | Estado |
|---|---|---|---|
| Atacante | VM **Kali Linux** (la existente) | `192.168.56.10` | La VM existe; la IP y la red están sin configurar |
| Objetivo principal | **Segunda VM** dedicada a Goldilocks CTF (Flask, SQLite, archivos generados) y a los servicios vulnerables que se decida alojar allí | `192.168.56.12` | **Propuesta; no existe** |
| Objetivo externo | VM **Metasploitable 2**, solo para el reto `metasploit` | `192.168.56.13` | **Propuesta; no existe** |
| Red | *Host-Only* (o red interna de VirtualBox) aislada de otras redes | `192.168.56.0/24` | **Propuesta; no configurada** |

**Principios de la propuesta:**
- No se asume que todos los servicios deban ejecutarse en la misma VM. Cada dependencia se aloja donde tenga sentido técnico (ver K.3).
- El sistema operativo de la segunda VM está **sin decidir**. Debe ser Linux, porque los comandos de las pistas de `webshell` y las rutas de los retos asumen un sistema tipo Unix.
- Las IP son las de referencia de la documentación existente. Si cambian, hay que actualizar los textos y pistas de los retos que las mencionan (K.3).

### K.3 Dependencias por reto (verificado en el código)

La columna «Alojamiento propuesto» es una **propuesta** para la arquitectura de K.2, **no probada**.

| Reto | Servicios o máquinas adicionales | Archivos generados o de estado | IP mencionadas | Herramientas del jugador (Kali) | Alojamiento propuesto |
|---|---|---|---|---|---|
| `nmap` | Escaneo real contra el servidor objetivo. En la app está simulado. | — | `192.168.56.0/24`, `.12` | `nmap` | VM objetivo |
| `dork` | — | `static/docs/informe_seguridad_osos.txt` (`setup_db.py`) | — | Navegador o `curl` | VM objetivo |
| `dirb` | — | Ruta interna de la app | — | `dirb` y un diccionario | VM objetivo |
| `wireshark` | — | Se genera en la ruta (texto con extensión `.pcap`) | `.20` y `.12` (en el contenido) | Wireshark o `base64` | VM objetivo |
| `sqli_login` | — | `goldilocks.db`, tabla `users` (`setup_db.py`) | — | Navegador, Burp | VM objetivo |
| `sqli_medium` | — | `goldilocks.db`, tabla `recipes` (`setup_db.py`) | — | Navegador, Burp | VM objetivo |
| `xss_reflected` | — | Cookie generada en la ruta | — | Navegador | VM objetivo |
| `xss_stored` | — | **Estado en memoria del proceso** | — | Navegador (BeEF, opcional) | VM objetivo (un solo proceso) |
| `webshell` | — | `uploads/`, `flags/` (`setup_db.py`) | Pista con ruta absoluta (`/flags/…`) | Navegador, `curl` | VM objetivo, con las medidas de K.6 |
| `metasploit` | **VM Metasploitable 2** con la bandera preparada | Archivo de bandera en esa VM (`flags/` lo genera `setup_db.py`) | `192.168.56.13` | Metasploit | **VM aparte** (Metasploitable) |
| `privesc` | — | Sesión de Flask; `/admin/config` | — | Herramienta para firmar cookies de Flask | VM objetivo |
| `stego` | `steghide` en el servidor (opcional, para incrustar la bandera al instalar) | Imágenes en `static/img/` (`setup_db.py`) | — | `steghide`, `strings` | VM objetivo |
| *Global* | — | `goldilocks.db` (puntuaciones), `uploads/`, `flags/` | Escucha en `0.0.0.0:5000` | — | VM objetivo |

**Resumen:** solo `metasploit` requiere una máquina adicional. `nmap` y `wireshark` mencionan IP concretas en su contenido. El resto depende de los archivos que genera `setup_db.py` y de la propia aplicación.

### K.4 Docker (alternativa pendiente de evaluación)

- **Estado:** **no implementado y no evaluado.** No se afirma compatibilidad.
- **Objetivo de la evaluación:** facilitar la instalación de la VM objetivo y hacerla reproducible. Docker **no sustituye** a la VM Metasploitable 2.
- **La compatibilidad debe probarse reto por reto y dependencia por dependencia.** Aspectos a comprobar (deducidos del código, **no probados**):

| Dependencia o aspecto | Qué hay que comprobar |
|---|---|
| Archivos generados (`setup_db.py`) | Si se generan al construir la imagen o al iniciar el contenedor, y que existan todos. |
| Persistencia (`goldilocks.db`, `uploads/`) | Volumen o recreación al arrancar; qué estado debe sobrevivir a un reinicio. |
| Estado en memoria (`xss_stored`) | Que se ejecute un solo proceso, o documentar el comportamiento con varios. |
| IP fijas en textos y pistas | Cómo encaja la red de Docker con la topología `192.168.56.x`. |
| `steghide` y Pillow | Disponibles en la imagen. |
| `webshell` | Que la ejecución de comandos quede contenida en el contenedor con las medidas de K.5 y K.6. |
| Dirección de escucha (`0.0.0.0:5000`) | A qué red se publica el puerto (solo a la del laboratorio). |
| `metasploit` | Fuera de Docker: depende de la VM Metasploitable 2. |

### K.5 Aislamiento (reglas confirmadas)

1. Las vulnerabilidades deliberadas se ejecutan **solo en un entorno controlado**: la VM objetivo de K.2 una vez validada, o la alternativa que se apruebe en K.4.
2. **No montar directorios personales del anfitrión** en las VMs ni en contenedores: sin carpetas compartidas con datos personales ni volúmenes del directorio de usuario.
3. **No compartir credenciales personales**: ni claves SSH, ni configuración de Git o de la nube, ni sesiones del navegador dentro del laboratorio.
4. **No conceder privilegios innecesarios**: nada de contenedores privilegiados, capacidades extra o el socket de Docker montado; procesos con usuario sin privilegios.
5. La red del laboratorio se mantiene **aislada** (*Host-Only* o red interna), sin exponer los servicios a redes ajenas.
6. Cada entorno debe poder **restaurarse** a un estado limpio (instantánea de VirtualBox o recreación del contenedor).

### K.6 Reto `webshell`: ejecución de comandos

- **Mecánica educativa (se conserva):** la ruta `/uploads/<archivo>.py?cmd=` ejecuta comandos en el sistema donde corre Flask. **No se desactiva ni se elimina** como parte de esta documentación.
- **Regla confirmada:** esa ejecución debe quedar **limitada al entorno de laboratorio** (la VM objetivo). Nunca debe ejecutarse en el equipo anfitrión ni en una red compartida.
- **Medidas pendientes de aprobación antes del despliegue** (no implementadas):

| Medida | Tipo de cambio |
|---|---|
| Ejecutar la aplicación solo dentro de la VM objetivo o del contenedor aislado (K.5) | Operativa |
| Dirección de escucha configurable: `127.0.0.1` para desarrollo y la interfaz del laboratorio en la VM objetivo, en vez de `0.0.0.0` fijo | Backend |
| Interruptor explícito de «modo laboratorio» para activar la ruta de ejecución | Backend |
| No versionar `uploads/shell.py`: que lo genere la instalación del laboratorio; limpiar `uploads/` al reiniciar | Repositorio + backend |
| Usuario del sistema dedicado y sin privilegios para el proceso Flask; banderas en archivos de solo lectura | Operativa |
| Límite de tiempo y de recursos para los comandos ejecutados | Backend |
| Instantánea limpia de la VM objetivo antes de cada sesión | Operativa |

### K.7 Configuración de despliegue

Estos parámetros deben poder **documentarse sin publicar valores reales**, con valores de ejemplo en la documentación y los reales en un mecanismo local fuera de Git:

| Parámetro | Situación actual (verificada) | Documentación prevista |
|---|---|---|
| Dirección y puerto de escucha | Fijos en `app.py` (`0.0.0.0:5000`) | Valor de ejemplo y uso recomendado por entorno |
| Clave de sesión de Flask | Fija en `app.py` | Marcador de ejemplo; valor real local |
| Banderas | Fijas en `app.py` y duplicadas en `setup_db.py` | Marcador `CTF{…}`; una sola fuente local |
| Contraseñas de los usuarios del laboratorio | En `setup_db.py`, `INSTALL.md` y `SOLUCIONARIO.md` | Marcadores en la documentación compartida |
| Frase de paso de `steghide` | En `setup_db.py` (y visible a propósito en `stego.html`) | Marcador en la documentación compartida |
| Ruta de la base de datos, `uploads/` y `flags/` | Relativas al proyecto | Documentar las rutas de cada entorno |
| IP del laboratorio (`.10`, `.12`, `.13`) | En `INSTALL.md` y en textos o pistas de retos | Tabla de topología por entorno, una vez configurada la red |

> El **mecanismo concreto** (variables de entorno o un archivo local excluido de Git, con una plantilla de ejemplo versionada) está **pendiente de aprobación**: requiere cambios de backend.

### K.8 Plan de transición a la segunda VM

Pasos previos al despliegue. **Ninguno se ha ejecutado.**

| # | Paso | Tipo | Criterio para darlo por hecho |
|---|---|---|---|
| 1 | Decidir dónde se ejecuta la app mientras no exista la segunda VM | Decisión | Acuerdo del equipo registrado en K.10 |
| 2 | Elegir el sistema operativo de la VM objetivo (Linux) y sus recursos | Decisión | Distribución, CPU, RAM y disco acordados |
| 3 | Aprobar las medidas de aislamiento (K.5) y de `webshell` (K.6) | Decisión | Aprobación del equipo y del docente responsable |
| 4 | Definir el mecanismo de configuración sin secretos (K.7) | Decisión + backend | Mecanismo aprobado; cambios de backend autorizados y hechos por el área responsable |
| 5 | Diseñar la red: *Host-Only* o red interna, rango e IP fijas de cada VM | Decisión | Tabla de topología aprobada; textos y pistas con IP revisados si cambian |
| 6 | Crear la VM objetivo y la red en VirtualBox, sin carpetas compartidas | Infraestructura | VM arrancada, en la red aislada, sin acceso a datos personales |
| 7 | Instalar la aplicación en la VM objetivo (`requirements.txt`, `setup_db.py`) | Infraestructura | Criterio de instalación de K.9 cumplido |
| 8 | Hacer una instantánea limpia de la VM objetivo | Infraestructura | Instantánea creada y restauración probada |
| 9 | Obtener y configurar la VM Metasploitable 2 con su bandera | Infraestructura | Accesible desde Kali en la red del laboratorio |
| 10 | Ejecutar los criterios de prueba (K.9) desde Kali | Validación | Todos los criterios cumplidos, con evidencias |
| 11 | (Opcional) Evaluar Docker para la VM objetivo (K.4) | Evaluación | Informe por reto y por dependencia |
| 12 | Actualizar `INSTALL.md` con la topología real, sin secretos | Documentación | Documento revisado por el equipo |

### K.9 Criterios de prueba en el entorno autorizado

Todas las pruebas se hacen **dentro del entorno autorizado**, **nunca en el equipo anfitrión**. **Ninguno de estos criterios se ha ejecutado aún.**

| Ámbito | Criterio verificable |
|---|---|
| Instalación | En la VM objetivo, desde cero, `pip install -r requirements.txt` y `setup_db.py` terminan sin errores, y la base de datos, los documentos, las imágenes y los archivos de banderas quedan generados. |
| Conectividad | Desde Kali se alcanza la aplicación en la dirección y el puerto acordados. Metasploitable 2 responde en su IP. Los servicios **no** son accesibles desde fuera de la red del laboratorio ni desde otras redes del anfitrión. |
| Aislamiento | No hay carpetas compartidas ni credenciales personales en las VMs; el proceso Flask no corre como administrador; la instantánea restaura un estado limpio. |
| Persistencia | Las puntuaciones se guardan y siguen tras reiniciar el servicio. Queda documentado qué estado se pierde a propósito (`xss_stored`) y qué ocurre con `uploads/`. |
| Navegación | Desde Kali: portada → mapa → los 12 retos → marcador → reiniciar o salir, sin enlaces rotos. |
| Funcionamiento de los retos | Cada reto se resuelve desde Kali con su técnica prevista; las banderas correctas e incorrectas, las pistas y sus penalizaciones se comportan como en la sección J. |
| `webshell` | La ejecución de comandos ocurre solo dentro de la VM objetivo y no alcanza el anfitrión ni la VM de Kali. |
| Docker (si se evalúa) | Los mismos criterios, más la lista de K.4, con un informe de qué retos y dependencias funcionan y cuáles no. |

### K.10 Estado de validación

| Cuestión | Estado | Requiere |
|---|---|---|
| VirtualBox con una única VM de Kali Linux | **Confirmado** | — |
| No existen todavía la VM objetivo ni la VM Metasploitable 2 | **Confirmado** | — |
| Las vulnerabilidades se conservan y se aíslan; no se eliminan | **Confirmado** | — |
| Reglas de aislamiento de K.5 | **Confirmadas** como regla; **no probadas** | Comprobarlas en el entorno (K.9) |
| Docker | **Propuesto** como alternativa; **no probado** | Evaluación por reto y por dependencia (K.4) |
| Arquitectura objetivo con atacante y objetivo separados (K.2) | **Propuesta** | Aprobación del equipo |
| Red *Host-Only* `192.168.56.0/24` e IP de referencia | **Propuesta**; **no configurada ni probada** | Pasos 5 y 6 de K.8 |
| Dónde se ejecuta la app mientras no exista la segunda VM | **Pendiente** | Decisión del equipo (nunca en el anfitrión) |
| Sistema operativo y recursos de la VM objetivo | **Pendiente** | Decisión del equipo |
| Medidas del reto `webshell` (K.6) | **Pendiente** | Aprobación del equipo y del docente responsable; cambios de backend autorizados |
| Mecanismo de configuración sin secretos (K.7) | **Pendiente** | Aprobación; cambio de backend |
| Persistencia de `goldilocks.db` y tratamiento de `uploads/` | **Pendiente** | Decisión del equipo |
| Adaptar las IP fijas de textos y pistas a la topología definitiva | **Pendiente** | Depende del paso 5 de K.8 |
| Quién crea y mantiene la VM objetivo y la VM Metasploitable 2 | **Pendiente** | Asignación del equipo |
| Instalación, conectividad y funcionamiento de los retos en el laboratorio | **No probado** | Criterios de K.9 |
