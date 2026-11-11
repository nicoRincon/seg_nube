# Sonidos de RicitosFlow

Todos los audios del juego viven en esta carpeta. Respetan el interruptor de
sonido compartido (`static/js/sound-pref.js`, clave `rf-sound` en localStorage).

| Archivo | Momento | Quién lo reproduce |
|---|---|---|
| `cuento_de_hadas.mp3` | Registro e inicio de sesión (bucle, volumen bajo) | `js/rf-audio.js` (escena `login`) |
| `bosque_medio_12s.mp3` | Mapa y diario (bucle, volumen bajo) | `js/rf-audio.js` (escena `forest`) |
| `puerta_vieja.mp3` | Apertura de la puerta al entrar al bosque — **pendiente de la animación** | `RFAudio.door()` (ver `templates/guardian.html`) |
| `sonido_de_oso.mp3` | Al pedir una pista (fragmento de 3 s desde el segundo 14, con fundido) | `js/rf-audio.js` (formularios `data-rf-hint`) |
| `reloj_suave_muestra.mp3` | Tic-tac: 3 s al entrar a un reto, aviso cada 15 min, último minuto acelerado | `js/rf-audio.js` (`RFAudio.timer`) |
| `oso_enojado.mp3` → `game_over_triste.mp3` | Tiempo agotado: rugido y, al terminar, derrota + sonido triste | `js/rf-audio.js` (`RFAudio.defeat`) |
| `magic_suave_40-43s.mp3` | Reto completado: la tarjeta sale del libro (0,0 s) | `js/reward-card.js` (etapa `libro_abrir`) |
| `hadas_medio_3-5s.mp3` | La tarjeta gira y revela la viñeta (3,4 s) | `js/reward-card.js` (etapa `recompensa`) |
| `victoria_sonic.mp3` | Victoria final — **pendiente del rompecabezas** | `RFAudio.victory()` (`templates/victoria.html`) |

El mapeo de etapas de la tarjeta a archivos está en `REWARD_SOUNDS` (`app.py`).

## Recomendaciones técnicas

- Mono, 44.1 kHz. OGG Vorbis calidad ~4 o MP3 96–128 kbps (< 60 KB cada uno).
- Sin silencio inicial (recortar el arranque) para que coincida con la animación.
- Fundido de salida corto al final; picos alrededor de −3 dBFS y volumen parecido
  entre los cuatro (el script ya baja el giro y la salida respecto a la recompensa).
- Nada de música continua ni sonidos electrónicos/arcade.

## Fuentes con licencia apta para un proyecto académico publicado

Priorizar **CC0 (dominio público)**: permite usar, modificar y publicar los archivos
en el repositorio sin atribución obligatoria.

- **Freesound.org** — filtrar por licencia *Creative Commons 0*. Búsquedas útiles:
  `page flip soft`, `book pages magic`, `fairy chime`, `wind whoosh soft`,
  `recorder flute short`, `glockenspiel ascending`, `magic sparkle`, `chime reveal`.
  (Requiere cuenta gratuita para descargar. Evitar "Attribution NonCommercial".)
- **Kenney.nl** — packs de audio CC0 (p. ej. *Interface Sounds*, *RPG Audio*).
- **OpenGameArt.org** — filtrar por licencia CC0.

Con cuidado:
- *CC BY* (Freesound/OpenGameArt): válido, pero hay que acreditar al autor
  (anotarlo abajo y en la documentación del proyecto).
- *Pixabay* y *Zapsplat*: se pueden usar dentro de un proyecto, pero sus licencias
  restringen redistribuir los archivos tal cual; al publicar el repositorio los
  archivos quedan descargables, así que es preferible evitarlos.

## Registro de procedencia (completar al incorporar cada archivo)

| Archivo | Autor | URL de origen | Licencia | Edición realizada |
|---------|-------|---------------|----------|-------------------|
|         |       |               |          |                   |
