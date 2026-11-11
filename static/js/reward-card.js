/* ──────────────────────────────────────────────────────
   RicitosFlow — Tarjeta de recompensa (pieza de la historieta)

   Solo PRESENTA una pieza que el servidor ya registró (puzzle_pieces).
   No envía nada al servidor ni decide recompensas.

   Secuencia (modo "flip"):
     A. La ilustración sale del marco del libro (.sbn-art), se eleva y viaja
        al centro mientras crece (técnica FLIP sobre .rwd-lift).
     B. La tarjeta gira 180° en Y (.rwd-card); a 90° (de canto) la caja ya
        va adoptando la proporción de la viñeta (.rwd-fly).
     C. Destello + partículas, mensaje y botón «Continuar».

   Modo "fade" (prefers-reduced-motion o sin 3D / Web Animations):
     fundido del frente al reverso, sin desplazamiento ni giro.

   Capas:  .rwd-fly  → centrado y tamaño
           .rwd-lift → salida del libro (translate/scale)
           .rwd-card → giro 3D

   Línea de tiempo (modo "flip") y efectos de sonido:
     0.0 – 1.2 s  salida del libro ............ libro_abrir
     1.2 – 2.2 s  viaje al centro ............. tarjeta_salida
     2.2 – 3.4 s  giro 180° ................... tarjeta_giro
     3.4 – 4.2 s  revelación + destello ....... recompensa
     4.2 – 5.0 s  mensaje y botón «Continuar» (CSS)
   ────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var root = document.getElementById('rwd');
  if (!root || window.__rwdActive) return;       // una sola recompensa a la vez
  window.__rwdActive = true;

  // Fuera de cualquier contenedor con containment/transform (.sbn-stage),
  // para que position: fixed se refiera a la ventana.
  document.body.appendChild(root);

  var fly     = root.querySelector('.rwd-fly');
  var lift    = root.querySelector('.rwd-lift');
  var card    = root.querySelector('.rwd-card');
  var caption = root.querySelector('.rwd-caption');
  var button  = root.querySelector('.rwd-continue');
  var sparks  = root.querySelector('.rwd-sparks');
  var frontImg = root.querySelector('.rwd-front .rwd-img');
  var backImg  = root.querySelector('.rwd-back .rwd-img');
  var soundBtn = root.querySelector('.rwd-sound');

  var art    = document.querySelector('.sbn-art:not(.sbn-art--empty)');
  // Frente genérico (retos sin ilustración): la tarjeta sale del formulario de huella
  var source = art || document.querySelector('.card.glow-green');

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var supports = function (p, v) { return !!(window.CSS && CSS.supports && CSS.supports(p, v)); };
  var can3d = typeof card.animate === 'function' &&
              supports('transform-style', 'preserve-3d') &&
              (supports('backface-visibility', 'hidden') || supports('-webkit-backface-visibility', 'hidden'));
  var mode = (reduce || !can3d) ? 'fade' : 'flip';
  root.classList.add('rwd--' + mode);

  var state = 'idle';          // idle → playing → revealed → closing → done
  var anims = [];
  var timers = [];
  var lastFocus = document.activeElement;
  var dims = null;

  // Duraciones (ms). EXIT + TRAVEL forman una sola animación continua.
  var T = { EXIT: 1200, TRAVEL: 1000, FLIP: 1200, SAFETY: 9000,
            FADE_FRONT: 30, FADE_SWAP: 1500, FADE_REVEAL: 2400 };

  // ── Efectos de sonido (Web Audio) ──────────────────────────────────
  // Nunca bloquea la animación: si un audio no está, no cargó a tiempo,
  // el sonido está silenciado o el navegador no permite reproducir sin una
  // interacción previa, ese efecto simplemente no suena.
  var Sound = (function () {
    var urls = {};
    try { urls = JSON.parse(root.getAttribute('data-sounds') || '{}') || {}; } catch (e) {}
    var AC = window.AudioContext || window.webkitAudioContext;
    var VOL = { libro_abrir: 0.7, tarjeta_salida: 0.6, tarjeta_giro: 0.7, recompensa: 0.85 };
    var ctx = null, master = null;
    var buffers = {}, live = {}, used = {};
    var loading = false;

    function enabled() { return !window.RFSound || window.RFSound.enabled(); }
    function trace(name, action) {
      try { document.dispatchEvent(new CustomEvent('rwd:sound', { detail: { name: name, action: action } })); } catch (e) {}
    }
    function pick(list) {
      var probe = document.createElement('audio');
      for (var i = 0; i < list.length; i++) {
        var type = /\.ogg$/i.test(list[i]) ? 'audio/ogg; codecs="vorbis"' : 'audio/mpeg';
        if (probe.canPlayType && probe.canPlayType(type)) return list[i];
      }
      return null;
    }
    function load() {
      if (loading || !AC || !enabled() || !Object.keys(urls).length || !window.fetch) return;
      loading = true;
      try { ctx = new AC(); master = ctx.createGain(); master.connect(ctx.destination); }
      catch (e) { ctx = null; return; }
      trace('context', ctx.state);
      ctx.onstatechange = function () { trace('context', ctx.state); };
      Object.keys(urls).forEach(function (name) {
        var url = pick(urls[name] || []);
        if (!url) return;
        fetch(url, { cache: 'force-cache' })
          .then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); })
          .then(function (data) {
            return new Promise(function (ok, ko) { ctx.decodeAudioData(data, ok, ko); });
          })
          .then(function (buf) { buffers[name] = buf; })
          .catch(function () { trace(name, 'missing'); });
      });
    }
    // Intenta reanudar el contexto. El navegador decide: sin interacción válida
    // sigue "suspended" y no se reproduce nada (no se encola para después).
    function wake() {
      if (ctx && ctx.state === 'suspended' && enabled()) ctx.resume().catch(function () {});
    }
    function stop(name, fade) {
      var s = live[name];
      if (!s) return;
      delete live[name];
      var t = ctx.currentTime, f = Math.max(0.03, fade || 0.25);
      try {
        s.gain.gain.cancelScheduledValues(t);
        s.gain.gain.setValueAtTime(s.gain.gain.value, t);
        s.gain.gain.linearRampToValueAtTime(0, t + f);
        s.src.stop(t + f + 0.02);
      } catch (e) {}
      trace(name, 'stop');
    }
    function stopAll(fade) { Object.keys(live).forEach(function (n) { stop(n, fade); }); }
    var current = null;                             // última etapa pedida
    function play(name, fadeOthers) {
      if (used[name]) return;                       // una sola vez por recompensa
      used[name] = true;
      current = name;
      if (!enabled() || !ctx || !buffers[name]) { trace(name, 'skip'); return; }
      // Sin superposiciones bruscas. Solo corta si esta etapa tiene sonido propio:
      // una etapa sin archivo no debe silenciar el efecto anterior.
      if (fadeOthers) stopAll(fadeOthers);
      if (ctx.state === 'running') { start(name); return; }
      // Contexto suspendido: el navegador decide. Si concede la reanudación pronto
      // (≤ 500 ms: lo que tarda en abrirse el dispositivo de audio) y la etapa sigue
      // vigente, suena; si no, se descarta (nunca queda en cola fuera de tiempo).
      var asked = Date.now();
      ctx.resume().then(function () {
        if (ctx.state === 'running' && Date.now() - asked <= 500 && current === name && enabled()) start(name);
        else trace(name, 'skip');
      }, function () { trace(name, 'skip'); });
    }
    function start(name) {
      var src = ctx.createBufferSource(), gain = ctx.createGain();
      src.buffer = buffers[name];
      gain.gain.value = VOL[name] || 0.7;
      src.connect(gain); gain.connect(master);
      src.onended = function () { if (live[name] && live[name].src === src) delete live[name]; };
      src.start();
      live[name] = { src: src, gain: gain };
      trace(name, 'play');
    }

    if (window.RFSound) window.RFSound.onChange(function (on) {
      if (!on) stopAll(0.15); else { load(); wake(); }
    });
    // Una interacción dentro de la página habilita los efectos siguientes
    ['pointerdown', 'keydown'].forEach(function (ev) {
      document.addEventListener(ev, wake, true);
    });

    return { load: load, wake: wake, play: play, stop: stop, stopAll: stopAll };
  })();

  function later(fn, ms) { var t = setTimeout(fn, ms); timers.push(t); return t; }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }
  function px(n) { return Math.round(n) + 'px'; }

  function ratio(img, fallback) {
    return img && img.naturalWidth ? img.naturalWidth / img.naturalHeight : fallback;
  }

  function ready(img) {
    if (!img) return Promise.resolve();
    if (img.decode) return img.decode().catch(function () {});
    if (img.complete) return Promise.resolve();
    return new Promise(function (ok) { img.onload = img.onerror = ok; });
  }

  // ── Medidas: tarjeta centrada en el espacio libre sobre el mensaje ──
  function measure() {
    var vw = document.documentElement.clientWidth;
    var vh = window.innerHeight;
    var gutter = vw < 600 ? 16 : 28;
    var capH = caption.offsetHeight;
    var availW = vw - gutter * 2;
    var availH = Math.max(140, vh - capH - gutter * 2 - 18);

    function fit(r, maxW) {
      // 0.92: margen para el "salto" del giro (escala ×1.07 y −14 px)
      var w = Math.min(availW * 0.92, maxW, availH * 0.92 * r);
      return { w: w, h: w / r };
    }
    var rf = ratio(frontImg, 3 / 2);
    var rb = ratio(backImg, 1);
    var f = fit(rf, 820);
    var b = fit(rb, 640);
    if (mode === 'fade') f = b;                     // sin cambio de forma

    var cx = vw / 2;
    var cy = gutter + availH / 2;
    return { fw: f.w, fh: f.h, bw: b.w, bh: b.h, cx: cx, cy: cy,
             capTop: cy + b.h / 2 + 18, vw: vw, vh: vh };
  }

  function place(w, h) {
    fly.style.left = px(dims.cx);
    fly.style.top = px(dims.cy);
    fly.style.width = px(w);
    fly.style.height = px(h);
    caption.style.top = px(Math.min(dims.capTop, dims.vh - caption.offsetHeight - 12));
  }

  // ── Partículas del destello ──
  function burst() {
    if (mode === 'fade') return;
    var n = 16;
    var reach = Math.max(dims.bw, dims.bh) * 0.62;
    for (var i = 0; i < n; i++) {
      var s = document.createElement('span');
      s.className = 'rwd-spark' + (i % 3 === 0 ? ' rwd-spark--star' : '');
      s.style.setProperty('--a', (360 / n * i + (Math.random() * 14 - 7)).toFixed(1) + 'deg');
      s.style.setProperty('--d', px(reach * (0.75 + Math.random() * 0.4)));
      s.style.setProperty('--delay', (Math.random() * 0.3).toFixed(2) + 's');
      sparks.appendChild(s);
    }
    later(function () { sparks.textContent = ''; }, 2400);
  }

  // ── C. Revelación. skipped = el jugador adelantó el final (Esc, Enter, clic) ──
  function reveal(skipped) {
    if (state === 'revealed' || state === 'closing' || state === 'done') return;
    clearTimers();
    anims.forEach(function (a) { try { a.cancel(); } catch (e) {} });
    anims = [];
    if (skipped === true) root.classList.add('is-skipped');   // mensaje sin espera
    root.classList.add('is-flipped', 'is-revealed');
    place(dims.bw, dims.bh);
    state = 'revealed';
    burst();
    // Al saltar se cortan las etapas que ya no corresponden; el giro natural
    // se desvanece suavemente bajo el sonido de la recompensa.
    Sound.play('recompensa', skipped === true ? 0.15 : 0.6);
    button.focus({ preventScroll: true });
  }
  function skip() { reveal(true); }

  // ── A + B: salida del libro, viaje al centro y giro ──
  function playFlip() {
    place(dims.fw, dims.fh);

    // Punto de partida: el marco de la ilustración en el libro
    var from = { x: 0, y: 40, sx: 0.3, sy: 0.3 };
    if (source) {
      var r = source.getBoundingClientRect();
      if (r.width && r.bottom > 0 && r.top < dims.vh) {
        from = { x: r.left + r.width / 2 - dims.cx, y: r.top + r.height / 2 - dims.cy,
                 sx: r.width / dims.fw, sy: r.height / dims.fh };
      }
    }
    function at(dy, k) {
      return 'translate(' + px(from.x) + ',' + px(from.y + dy) + ') scale(' +
             (from.sx * k).toFixed(4) + ',' + (from.sy * k).toFixed(4) + ')';
    }
    var total = T.EXIT + T.TRAVEL;
    var lifted = T.EXIT / total;                  // fin de la salida (1.2 s)

    root.classList.add('is-lifting');
    if (art) art.classList.add('is-lifted');      // el marco queda vacío en la página
    Sound.play('libro_abrir');

    // A. Se desprende despacio (0–0.45 s), se eleva (hasta 1.2 s) y,
    //    sin detenerse, viaja al centro creciendo (1.2–2.2 s).
    var travel = lift.animate([
      { transform: at(0, 1),       offset: 0,             easing: 'cubic-bezier(.4,0,.6,1)' },
      { transform: at(-6, 1.025),  offset: lifted * 0.38, easing: 'cubic-bezier(.3,0,.3,1)' },
      { transform: at(-30, 1.1),   offset: lifted,        easing: 'cubic-bezier(.45,.05,.25,1)' },
      { transform: 'translate(0px,0px) scale(1,1)', offset: 1 }
    ], { duration: total, fill: 'both' });
    anims.push(travel);
    later(function () { Sound.play('tarjeta_salida', 0.5); }, T.EXIT);

    travel.finished.then(function () {
      if (state !== 'playing') return;
      root.classList.remove('is-lifting');
      flip();                                     // sin pausa: el giro sigue al viaje
    }).catch(function () {});
  }

  // B. Giro pausado de 180°
  function flip() {
    if (state !== 'playing') return;
    var D = T.FLIP;
    Sound.play('tarjeta_giro', 0.4);
    var ease = 'cubic-bezier(.45,.05,.55,.95)';   // simétrica: 90° en la mitad
    anims.push(card.animate(
      [{ transform: 'rotateY(0deg)' }, { transform: 'rotateY(180deg)' }],
      { duration: D, easing: ease, fill: 'both' }));
    anims.push(fly.animate(
      [{ width: px(dims.fw), height: px(dims.fh) }, { width: px(dims.bw), height: px(dims.bh) }],
      { duration: D, easing: ease, fill: 'both' }));
    var pop = lift.animate([
      { transform: 'translateY(0) scale(1)' },
      { transform: 'translateY(-14px) scale(1.07)', offset: 0.5 },
      { transform: 'translateY(0) scale(1)' }
    ], { duration: D, easing: ease, fill: 'both' });
    anims.push(pop);

    // Seguro extra contra el parpadeo de ambas caras: cambio de cara a 90°
    later(function () { root.classList.add('is-flipped'); }, D / 2);

    pop.finished.then(function () { if (state === 'playing') reveal(); }).catch(function () {});
  }

  // ── Modo fundido (movimiento reducido o sin 3D) ──
  function playFade() {
    place(dims.bw, dims.bh);
    if (art) art.classList.add('is-lifted');
    Sound.play('libro_abrir');
    later(function () { root.classList.add('is-shown'); }, T.FADE_FRONT);
    later(function () { root.classList.add('is-flipped'); Sound.play('tarjeta_giro', 0.5); }, T.FADE_SWAP);
    later(reveal, T.FADE_REVEAL);
  }

  // ── Cierre ──
  function close() {
    if (state === 'closing' || state === 'done') return;
    if (state !== 'revealed') { skip(); return; }     // primer gesto: saltar al final
    state = 'closing';
    clearTimers();
    Sound.stopAll(0.35);
    root.classList.add('is-closing');
    if (art) art.classList.remove('is-lifted');      // la ilustración vuelve a su página
    setTimeout(finish, reduce ? 160 : 420);
  }

  function finish() {
    if (state === 'done') return;
    state = 'done';
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', onResize);
    document.documentElement.classList.remove('rwd-open');
    root.remove();
    window.__rwdActive = false;
    var target = (lastFocus && lastFocus !== document.body && document.contains(lastFocus))
      ? lastFocus
      : (document.querySelector('.card.glow-green .btn') || document.querySelector('.sbn-zone--right'));
    if (target && target.focus) target.focus({ preventScroll: true });
  }

  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); close(); return; }
    if (e.key === 'Tab') {                         // foco atrapado en el diálogo
      e.preventDefault();
      var list = [soundBtn];
      if (state === 'revealed') list.push(button);
      list = list.filter(Boolean);
      var i = list.indexOf(document.activeElement);
      var n = i < 0 ? (state === 'revealed' ? list.length - 1 : 0)
                    : (i + (e.shiftKey ? -1 : 1) + list.length) % list.length;
      if (list[n]) list[n].focus(); else root.focus();
      return;
    }
    // Enter / Espacio sobre el botón de sonido: lo maneja el propio botón
    if (soundBtn && document.activeElement === soundBtn) return;
    if ((e.key === 'Enter' || e.key === ' ') && state === 'playing') { e.preventDefault(); skip(); }
  }

  function onResize() {
    var w = document.documentElement.clientWidth;
    if (state === 'playing') {
      // En móvil la barra del navegador dispara resize al moverse: solo un
      // cambio real de ancho (rotación, ventana) interrumpe el vuelo.
      if (Math.abs(w - dims.vw) < 60) return;
      skip();
    }
    if (state !== 'revealed') return;
    dims = measure();
    place(dims.bw, dims.bh);
  }

  root.addEventListener('click', function (e) {
    if (e.target.closest('[data-sound-toggle]')) return;   // no interfiere con la tarjeta
    if (e.target.closest('[data-rwd-close]') || state === 'playing') close();
  });

  // ── Arranque ──
  function start() {
    if (state !== 'idle') return;
    state = 'playing';
    root.hidden = false;
    root.setAttribute('tabindex', '-1');
    document.documentElement.classList.add('rwd-open');
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', onResize);
    dims = measure();
    root.focus({ preventScroll: true });
    // Siguiente fotograma (con respaldo: rAF no corre en pestañas ocultas)
    var begun = false;
    var begin = function () {
      if (begun || state !== 'playing') return;
      begun = true;
      root.classList.add('is-open');
      if (mode === 'flip') playFlip(); else playFade();
    };
    Sound.wake();
    requestAnimationFrame(begin);
    setTimeout(begin, 80);
    // Red de seguridad: pase lo que pase, la recompensa queda visible y cerrable
    later(skip, T.SAFETY);
  }

  // Los audios se piden en paralelo a las imágenes; nunca se esperan
  Sound.load();
  if (window.RFSound) window.RFSound.paint();

  // Espera a que ambas caras estén decodificadas (máx. 2,5 s) para no girar en blanco
  var go = function () { start(); };
  Promise.race([
    Promise.all([ready(frontImg), ready(backImg)]),
    new Promise(function (ok) { setTimeout(ok, 2500); })
  ]).then(function () {
    if (document.readyState === 'complete') go();
    else window.addEventListener('load', go, { once: true });
    setTimeout(go, 3000);                          // por si "load" tarda (recursos lentos)
  });
})();
