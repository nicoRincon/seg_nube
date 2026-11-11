/* ──────────────────────────────────────────────────────
   RicitosFlow — Música ambiental y efectos del juego

   Un solo reproductor para toda la página. Respeta la preferencia compartida
   de sound-pref.js (window.RFSound) y las restricciones de reproducción
   automática: si el navegador no deja sonar sin un gesto previo, la música
   espera al primer clic o tecla; los efectos con momento fijo se descartan si
   ese momento ya pasó (nunca suenan fuera de tiempo).

   Escena (atributo data-rf-scene del <body>, lo fija base.html):
     login      → cuento_de_hadas.mp3 en bucle (registro e inicio de sesión)
     forest     → bosque_medio_12s.mp3 en bucle (mapa y diario)
     challenge  → sin música; tic-tac del temporizador
     lose       → nada (la secuencia de derrota la lanza el temporizador)

   Los efectos de la tarjeta de recompensa (magic_suave y hadas_medio) los
   reproduce reward-card.js con su propia línea de tiempo.

   API:  RFAudio.timer(segundos)   — lo llama el cronómetro de base.html
         RFAudio.defeat(loseUrl)   — tiempo agotado: rugido → derrota + triste
         RFAudio.door()            — efecto de puerta (sin uso en la entrada al bosque:
                                     el video de transición trae su propio sonido)
         RFAudio.forestIntro()     — música del bosque al terminar el video de entrada
         RFAudio.forestFx()        — efecto mágico (hadas) al pasar del video al mapa
         RFAudio.prime(nombre)     — desbloquea un sonido dentro de un gesto (móviles)
         RFAudio.hint(done)        — oso al confirmar una pista (hint-popup.js)
         RFAudio.wrong()           — gruñido corto: respuesta incorrecta (_wrong_alert.html)
         RFAudio.victory(id)       — reservado para la victoria final real
   ────────────────────────────────────────────────────── */
(function () {
  'use strict';
  if (window.RFAudio) return;

  var me = document.currentScript;
  var BASE = (me && me.getAttribute('data-base')) || '/static/audio/';

  var FILES = {
    login:   'cuento_de_hadas.mp3',
    forest:  'bosque_medio_12s.mp3',
    door:    'puerta_vieja.mp3',
    bear:    'sonido_de_oso.mp3',
    tick:    'reloj_suave_muestra.mp3',
    roar:    'oso_enojado.mp3',
    sad:     'game_over_triste.mp3',
    victory: 'victoria_sonic.mp3',
    fairy:   'hadas_medio_3-5s.mp3',  // mismo archivo que la revelación de la tarjeta (reward-card.js)
    grr:     'oso_enojado.mp3'        // mismo archivo que el rugido de derrota, pero solo un gruñido corto
  };
  // Volúmenes moderados (0–1). La música queda claramente por debajo de los efectos.
  // bear (pista): 0.55 → 0.9 para que suene como advertencia. Se mantiene < 1:
  // el canal nunca amplifica por encima del archivo original, así que no satura.
  var VOL = { login: 0.22, forest: 0.18, door: 0.6, bear: 0.9, tick: 0.28,
              tickFast: 0.42, roar: 0.55, sad: 0.5, victory: 0.6, fairy: 0.8, grr: 0.5 };

  var TIMER = {
    INTRO: 3,           // s de tic-tac al iniciar un desafío
    QUARTER: 900,       // aviso cada 15 min de tiempo de juego
    NOTICE: 2.5,        // s que dura cada aviso
    FINAL: 60,          // último minuto: tic-tac acelerado
    FAST_RATE: 1.6      // velocidad del tic-tac en el último minuto
  };
  // sonido_de_oso.mp3 dura ~89 s: para la pista solo se usa el fragmento 14 s → 17 s.
  var BEAR_CLIP = { start: 14, length: 3, fade: 0.5 };
  // oso_enojado.mp3 dura ~12 s: gruñidos entre 0,75 y 5 s y el rugido fuerte
  // (el de la derrota) entre 6,7 y 8,5 s. La respuesta incorrecta usa solo un
  // gruñido: 0,8 s → 3,0 s, con fundido.
  var GRR_CLIP = { start: 0.8, length: 2.2, fade: 0.5 };

  var scene = document.body ? document.body.getAttribute('data-rf-scene') || '' : '';
  var live = {};          // nombre → canal en reproducción (una sola instancia por nombre)
  var waiting = [];       // reproducciones pendientes del primer gesto
  var over = false;       // la partida terminó en esta página: no más sonidos de tiempo

  function enabled() { return !window.RFSound || window.RFSound.enabled(); }
  function trace(name, action) {
    try { document.dispatchEvent(new CustomEvent('rf:audio', { detail: { name: name, action: action } })); } catch (e) {}
  }
  function store(key, value) {
    try {
      if (value === undefined) return sessionStorage.getItem(key);
      if (value === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, value);
    } catch (e) {}
    return null;
  }

  // ── Volumen: iOS ignora audio.volume, así que allí se enruta por Web Audio ──
  var AC = window.AudioContext || window.webkitAudioContext;
  var ctx = null;
  var volumeLocked = (function () {
    try { var a = document.createElement('audio'); a.volume = 0.5; return a.volume !== 0.5; }
    catch (e) { return false; }
  })();
  function ensureCtx() {
    if (ctx || !AC || !volumeLocked) return ctx;
    try { ctx = new AC(); } catch (e) { ctx = null; }
    return ctx;
  }

  // Precarga: los efectos con momento fijo deben estar listos antes de su evento
  var pool = {};
  function preload(name) {
    if (pool[name] || !FILES[name]) return;
    var el = new Audio();
    el.preload = 'auto';
    el.src = BASE + FILES[name];
    try { el.load(); } catch (e) {}
    pool[name] = el;
  }

  // ── Canal: un <audio> con volumen y fundidos ──
  function Channel(name, opts) {
    var el = pool[name] || new Audio();
    delete pool[name];                              // cada elemento se usa una sola vez
    if (!el.src) { el.preload = 'auto'; el.src = BASE + FILES[name]; }
    el.loop = !!opts.loop;
    this.name = name;
    this.el = el;
    this.level = 0;
    this.gain = null;
    this.fadeTimer = null;
    this.stopTimer = null;
    if (ensureCtx()) {
      try {
        var src = ctx.createMediaElementSource(el);
        this.gain = ctx.createGain();
        src.connect(this.gain);
        this.gain.connect(ctx.destination);
      } catch (e) { this.gain = null; }
    }
    this.set(0);
  }
  Channel.prototype.set = function (v) {
    this.level = Math.max(0, Math.min(1, v));
    if (this.gain) this.gain.gain.value = this.level;
    else this.el.volume = this.level;
  };
  Channel.prototype.fade = function (to, secs, done) {
    var self = this, from = this.level, t0 = Date.now(), ms = Math.max(1, secs * 1000);
    clearInterval(this.fadeTimer);
    this.fadeTimer = setInterval(function () {
      var k = Math.min(1, (Date.now() - t0) / ms);
      self.set(from + (to - from) * k);
      if (k >= 1) { clearInterval(self.fadeTimer); self.fadeTimer = null; if (done) done(); }
    }, 40);
  };
  Channel.prototype.halt = function () {
    clearInterval(this.fadeTimer);
    clearTimeout(this.stopTimer);
    try { this.el.pause(); } catch (e) {}
  };

  // Reproduce `name`. opts: loop, volume, fadeIn, at (segundo inicial),
  // limit (segundos y se detiene con fundido), rate, deadline (ms epoch: si
  // el navegador exige un gesto y llega tarde, se descarta), onEnd.
  function play(name, opts) {
    opts = opts || {};
    if (!enabled()) { trace(name, 'muted'); if (opts.onFail) opts.onFail('muted'); return null; }
    var ch = live[name];
    if (ch && !ch.el.paused) return ch;              // ya suena: no se duplica
    if (ch) ch.halt();
    ch = new Channel(name, opts);
    live[name] = ch;

    var target = opts.volume != null ? opts.volume : (VOL[name] || 0.5);
    if (opts.rate) setRate(ch, opts.rate);
    if (opts.at) {
      var seek = function () { try { ch.el.currentTime = opts.at; } catch (e) {} };
      if (ch.el.readyState >= 1) seek(); else ch.el.addEventListener('loadedmetadata', seek, { once: true });
    }
    ch.el.addEventListener('ended', function () {
      if (live[name] === ch) delete live[name];
      trace(name, 'ended');
      if (opts.onEnd) opts.onEnd();
    });

    function begin() {
      if (live[name] !== ch || !enabled()) return;
      if (opts.deadline && Date.now() > opts.deadline) { drop('late'); return; }
      if (ctx && ctx.state !== 'running') ctx.resume().catch(function () {});
      var p;
      try { p = ch.el.play(); } catch (e) { p = Promise.reject(e); }
      Promise.resolve(p).then(function () {
        trace(name, 'play');
        if (opts.onStart) opts.onStart();
        if (opts.fadeIn) { ch.set(0); ch.fade(target, opts.fadeIn); } else ch.set(target);
        if (opts.limit) {
          var fadeOut = opts.limitFade || 0.6;
          ch.stopTimer = setTimeout(function () { stop(name, fadeOut, opts.onEnd); },
                                    Math.max(0, opts.limit - fadeOut) * 1000);
        }
      }, function (err) {
        if (err && err.name === 'NotAllowedError' && !opts.noWait) {
          trace(name, 'blocked');
          waiting.push(begin);                       // el primer gesto lo vuelve a intentar
        } else {
          drop(err && err.name === 'NotAllowedError' ? 'blocked' : 'error');
        }
      });
    }
    function drop(why) {
      if (live[name] === ch) { ch.halt(); delete live[name]; }
      trace(name, why);
      if (opts.onFail) opts.onFail(why);
    }
    begin();
    return ch;
  }

  function stop(name, fade, done) {
    var ch = live[name];
    if (!ch) { if (done) done(); return; }
    delete live[name];
    clearTimeout(ch.stopTimer);
    if (!fade || ch.el.paused) { ch.halt(); trace(name, 'stop'); if (done) done(); return; }
    ch.fade(0, fade, function () { ch.halt(); trace(name, 'stop'); if (done) done(); });
  }
  function stopAll(fade) { Object.keys(live).forEach(function (n) { stop(n, fade); }); }

  function setRate(ch, rate) {
    var el = ch.el;
    try {
      el.preservesPitch = el.mozPreservesPitch = el.webkitPreservesPitch = false;   // tic-tac más vivo
      el.playbackRate = rate;
    } catch (e) {}
  }

  // Primer gesto: reanuda el contexto y lanza lo que esperaba permiso
  function onGesture() {
    if (ctx && ctx.state === 'suspended') ctx.resume().catch(function () {});
    if (!waiting.length) return;
    var list = waiting; waiting = [];
    list.forEach(function (fn) { fn(); });
  }
  ['pointerdown', 'keydown', 'touchend'].forEach(function (ev) {
    document.addEventListener(ev, onGesture, true);
  });

  // ── Música ambiental ──
  // La posición se guarda al salir de la página: mapa ↔ diario (o una recarga
  // del formulario de acceso) continúan donde iban, sin empezar de cero.
  var AMBIENT = { login: 'login', forest: 'forest' }[scene] || null;
  var POS_KEY = AMBIENT ? 'rf-amb:' + AMBIENT : null;
  var RESUME_WINDOW = 45 * 1000;   // tras más tiempo fuera, empieza de nuevo

  function resumePoint() {
    var raw = store(POS_KEY);
    if (!raw) return 0;
    var p = raw.split('|');
    var at = parseFloat(p[0]), when = parseInt(p[1], 10);
    if (!(at > 0) || !(Date.now() - when < RESUME_WINDOW)) return 0;
    return at;                                     // retoma justo donde se dejó
  }
  // Guarda la posición de cualquier música ambiental que esté sonando (también
  // la del bosque iniciada en la puerta del Guardián, para que el mapa la continúe).
  function saveAmbient() {
    ['login', 'forest'].forEach(function (n) {
      var ch = live[n];
      if (ch && !ch.el.paused && ch.el.currentTime > 0) store('rf-amb:' + n, ch.el.currentTime.toFixed(2) + '|' + Date.now());
    });
  }
  function startAmbient() {
    if (!AMBIENT || over || !enabled()) return;
    var at = resumePoint();
    play(AMBIENT, { loop: true, fadeIn: at ? 0.6 : 1.5, at: at });
  }
  function stopAmbient(fade) { if (AMBIENT) { saveAmbient(); stop(AMBIENT, fade); } }

  window.addEventListener('pagehide', function () { saveAmbient(); });
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) startAmbient();                 // volver con «atrás» (bfcache)
  });

  // ── Temporizador (solo en los desafíos) ──
  var isChallenge = scene === 'challenge';
  var solved = document.body && document.body.getAttribute('data-rf-solved') === '1';
  var lastRemaining = null;
  var tickMode = null;      // null | 'intro' | 'notice' | 'fast'

  function tickPlay(mode, limit) {
    if (over) return;
    var fast = mode === 'fast';
    var ch = live.tick;
    if (ch && !ch.el.paused) {                      // reutiliza el mismo sonido
      clearTimeout(ch.stopTimer);
      ch.el.loop = true;
      setRate(ch, fast ? TIMER.FAST_RATE : 1);
      ch.fade(fast ? VOL.tickFast : VOL.tick, 0.4);
      if (limit) ch.stopTimer = setTimeout(function () { tickStop(0.8); }, Math.max(0, limit - 0.8) * 1000);
      tickMode = mode;
      return;
    }
    tickMode = mode;
    play('tick', {
      loop: true,
      volume: fast ? VOL.tickFast : VOL.tick,
      rate: fast ? TIMER.FAST_RATE : 1,
      fadeIn: 0.3,
      limit: limit || 0,
      limitFade: 0.8,
      // el aviso del tiempo tiene momento fijo: si el gesto llega tarde, no suena
      deadline: limit ? Date.now() + limit * 1000 : 0,
      onEnd: function () { if (tickMode === mode) tickMode = null; }
    });
  }
  function tickStop(fade) { tickMode = null; stop('tick', fade); }

  function timer(remaining) {
    if (!isChallenge || over) { lastRemaining = remaining; return; }
    var prev = lastRemaining;
    lastRemaining = remaining;

    if (remaining <= 0) { tickStop(0.1); return; }

    if (remaining <= TIMER.FINAL) {
      if (tickMode !== 'fast') tickPlay('fast', 0);
      return;
    }
    if (tickMode === 'fast') tickStop(0.3);          // (no ocurre en la práctica: el tiempo no vuelve atrás)

    if (prev === null) {
      // Al iniciar el desafío: tic-tac breve, una vez por visita (no en recargas
      // del mismo reto por pistas o intentos) y nunca en un reto ya resuelto.
      var here = location.pathname;
      var from = store('rf-last-page');
      if (!solved && from !== here) tickPlay('intro', TIMER.INTRO);
      return;
    }
    // Aviso cada 15 minutos de juego (105:00, 90:00…). Se anota cada marca para
    // que no se repita al recargar ni al cambiar de reto.
    var mark = Math.floor(prev / TIMER.QUARTER);
    if (Math.floor(remaining / TIMER.QUARTER) < mark && mark >= 1) {
      var key = String(mark * TIMER.QUARTER);
      if (store('rf-quarter') !== key) {
        store('rf-quarter', key);
        if (tickMode !== 'intro') tickPlay('notice', TIMER.NOTICE);
      }
    }
  }

  // ── Derrota por tiempo: rugido → pantalla de derrota + sonido triste ──
  function defeat(loseUrl) {
    if (over) return;
    over = true;
    waiting = [];
    tickStop(0.1);
    stopAmbient(0.3);
    stop('bear', 0.2);
    var go = function () { window.location = loseUrl; };
    if (!enabled()) { go(); return; }
    var done = false;
    var safety;
    var next = function () {
      if (done) return;
      done = true;
      clearTimeout(safety);
      showLose(loseUrl);
    };
    var roar = play('roar', {
      noWait: true,                                   // sin permiso del navegador: derrota inmediata
      onEnd: next,
      onFail: function () { if (!done) { done = true; go(); } }
    });
    if (!roar) { if (!done) { done = true; go(); } return; }
    safety = setTimeout(next, 15000);                 // por si "ended" no llega
  }

  // Muestra la pantalla de derrota existente sin recargar, para que el sonido
  // triste siga en la misma página (una página nueva no tendría permiso de audio).
  function showLose(loseUrl) {
    var played = false;
    var sad = function () {
      if (played) return;
      played = true;
      if (enabled()) play('sad', { noWait: true });
    };
    if (!window.fetch || !window.DOMParser) { window.location = loseUrl; return; }
    fetch(loseUrl, { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        if (!doc.querySelector('.lose-scene')) throw new Error('sin pantalla de derrota');
        Array.prototype.forEach.call(doc.body.querySelectorAll('script'), function (s) { s.remove(); });
        sad();
        document.title = doc.title;
        document.body.className = doc.body.className;
        document.body.setAttribute('data-rf-scene', 'lose');
        document.body.innerHTML = doc.body.innerHTML;
        try { history.replaceState(null, '', loseUrl); } catch (e) {}
        window.scrollTo(0, 0);
        if (window.RFSound) window.RFSound.paint();
      })
      .catch(function () { window.location = loseUrl; });
  }

  // ── Pistas: oso → el servidor descuenta 5 min y 25 pts → pista visible ──
  // La confirmación, el bloqueo del doble envío y el envío del formulario los
  // gestiona hint-popup.js; aquí solo suena el fragmento del oso y, al acabar
  // (o si no puede sonar), se llama a `done` una única vez.
  function hint(done) {
    var called = false;
    var finish = function () { if (called) return; called = true; if (done) done(); };
    if (!enabled() || over) { finish(); return null; }
    tickStop(0.2);
    var bear = play('bear', {
      at: BEAR_CLIP.start, limit: BEAR_CLIP.length, limitFade: BEAR_CLIP.fade,
      noWait: true, onEnd: finish, onFail: finish
    });
    if (!bear) finish();
    setTimeout(finish, (BEAR_CLIP.length + 1.2) * 1000);   // red de seguridad
    return bear;
  }

  // ── Entrada al bosque (prólogo del Guardián) ──
  // La música del bosque empieza al terminar el video de transición; la posición se guarda
  // al salir (saveAmbient) y el mapa la continúa sin cortes.
  function forestIntro(fadeIn) {
    if (over || !enabled()) return null;
    return play('forest', { loop: true, fadeIn: fadeIn || 1.5, noWait: true });
  }

  // Efecto mágico (hadas_medio_3-5s.mp3) al terminar el video de entrada, justo
  // antes de pasar al mapa. Como el cambio de página cortaría el sonido, al
  // salir se anota su posición (saveFx) y el mapa lo termina desde ese punto
  // (resumeFx). Nunca espera un gesto: si el navegador no deja, no suena.
  var FX_KEY = 'rf-fx:fairy';
  var FX_WINDOW = 4000;            // ms: después de esto ya no tiene sentido continuarlo
  function forestFx() {
    if (over || !enabled()) return null;
    store(FX_KEY, null);
    return play('fairy', { noWait: true });
  }
  function saveFx() {
    var ch = live.fairy;
    if (ch && !ch.el.paused && !ch.el.ended) store(FX_KEY, ch.el.currentTime.toFixed(2) + '|' + Date.now());
  }
  function resumeFx() {
    var raw = store(FX_KEY);
    if (!raw) return;
    store(FX_KEY, null);                             // una sola vez
    var p = raw.split('|');
    var at = parseFloat(p[0]), when = parseInt(p[1], 10);
    var away = Date.now() - when;
    if (!(at >= 0) || !(away >= 0 && away < FX_WINDOW) || over || !enabled()) return;
    // Se espera a conocer la duración para arrancar ya en su punto (sin un
    // instante desde el segundo 0) y no sonar si el efecto ya habría acabado.
    preload('fairy');
    var el = pool.fairy;
    var go = function () {
      if (over || !enabled() || live.fairy) return;
      var pos = at + (Date.now() - when) / 1000;      // sigue al ritmo real
      if (el && el.duration && pos >= el.duration - 0.1) return;
      if (el) { try { el.currentTime = pos; } catch (e) {} }
      play('fairy', { at: pos, noWait: true });
    };
    if (el && el.readyState < 1) el.addEventListener('loadedmetadata', go, { once: true });
    else go();
  }
  window.addEventListener('pagehide', saveFx);

  // Respuesta incorrecta (la alerta de _wrong_alert.html, que solo existe si el
  // servidor rechazó la bandera). Una sola instancia; nunca espera un gesto:
  // si el navegador no deja sonar ya, no suena tarde.
  function wrong() {
    if (over || !enabled()) return null;
    return play('grr', { at: GRR_CLIP.start, limit: GRR_CLIP.length, limitFade: GRR_CLIP.fade, noWait: true });
  }

  // Puerta: efecto puerta_vieja.mp3. Se conserva en la API, pero la entrada al
  // bosque del Guardián ya no lo usa (el video de transición trae su sonido).
  function door(opts) { return play('door', opts || {}); }

  // Desbloqueo para un sonido que empezará más tarde, fuera del gesto del
  // usuario (p. ej. la música del bosque al terminar el video del Guardián).
  // Llamar dentro de un clic: en iOS/Safari cada <audio> necesita haberse
  // reproducido una vez durante un gesto. Se reproduce en silencio, se pausa
  // al instante y queda en la precarga para que play() lo reutilice.
  function prime(name) {
    if (!enabled() || over || !FILES[name] || live[name]) return;
    if (ensureCtx() && ctx.state !== 'running') ctx.resume().catch(function () {});
    preload(name);
    var el = pool[name];
    if (!el) return;
    el.muted = true;
    var p;
    try { p = el.play(); } catch (e) { p = Promise.reject(e); }
    Promise.resolve(p).then(function () {
      if (pool[name] === el) {                       // aún no lo tomó un canal
        try { el.pause(); el.currentTime = 0; } catch (e) {}
      }
      el.muted = false;
    }, function () { el.muted = false; });
  }

  // ── Reservado (sin evento todavía) ──

  // Victoria final: solo cuando el servidor haya validado el rompecabezas.
  // Una sola vez por identificador (p. ej. el participante).
  function victory(id) {
    var key = 'rf-victory:' + (id || '');
    if (store(key)) return null;
    stopAll(0.4);
    return play('victory', {
      deadline: Date.now() + 20000,
      onStart: function () { store(key, '1'); }
    });
  }

  // ── Preferencia de sonido ──
  if (window.RFSound) window.RFSound.onChange(function (on) {
    if (!on) { saveAmbient(); waiting = []; stopAll(0.2); tickMode = null; }
    else startAmbient();
  });

  // Página actual (para distinguir "entrar a un reto" de "recargarlo")
  window.addEventListener('pagehide', function () { store('rf-last-page', location.pathname); });

  window.RFAudio = {
    timer: timer, defeat: defeat, door: door, victory: victory,
    hint: hint, wrong: wrong, forestIntro: forestIntro, forestFx: forestFx, prime: prime,
    play: play, stop: stop, stopAll: stopAll, enabled: enabled,
    _state: function () { return { scene: scene, live: Object.keys(live), tickMode: tickMode, over: over,
                                   rate: live.tick ? live.tick.el.playbackRate : null,
                                   level: live.tick ? live.tick.level : null,
                                   ambientAt: AMBIENT && live[AMBIENT] ? live[AMBIENT].el.currentTime : null }; }
  };

  // Precarga según la escena (la derrota puede llegar en cualquier pantalla de juego)
  if (enabled()) {
    if (isChallenge) {
      preload('tick');
      if (document.querySelector('form[data-rf-hint]')) preload('bear');
    }
    if (isChallenge || scene === 'forest') preload('roar');
    // Puerta del Guardián: la transición es un video con su propio audio, así
    // que aquí no se precarga puerta_vieja.mp3; solo la música del bosque.
    if (document.querySelector('form[data-gd-enter]')) { preload('forest'); preload('fairy'); }
  }

  if (scene === 'forest') resumeFx();               // efecto de entrada que venía sonando
  startAmbient();
  var vEl = document.querySelector('[data-rf-victory]');
  if (vEl) victory(vEl.getAttribute('data-rf-victory'));
})();
