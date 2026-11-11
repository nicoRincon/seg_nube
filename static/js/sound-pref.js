/* ──────────────────────────────────────────────────────
   RicitosFlow — Preferencia de efectos de sonido

   Un solo interruptor lógico ("rf-sound" en localStorage) para todos los
   botones [data-sound-toggle] de la página: el del menú Ajustes del HUD y el
   de la tarjeta de recompensa. Se conserva entre páginas y pestañas.

   API para otros scripts:  window.RFSound.enabled() · .set(bool) · .onChange(fn)
   ────────────────────────────────────────────────────── */
(function () {
  'use strict';
  if (window.RFSound) return;

  var KEY = 'rf-sound';
  var subs = [];

  function read() {
    try { return localStorage.getItem(KEY) !== 'off'; }   // activado por defecto
    catch (e) { return true; }
  }
  var on = read();

  function paint() {
    var btns = document.querySelectorAll('[data-sound-toggle]');
    Array.prototype.forEach.call(btns, function (b) {
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.classList.toggle('is-muted', !on);
      var text = on ? 'Efectos activados' : 'Efectos silenciados';
      var label = b.querySelector('[data-sound-label]');
      if (label) label.textContent = text;
      b.setAttribute('title', on ? 'Silenciar efectos de sonido' : 'Activar efectos de sonido');
      if (!label) b.setAttribute('aria-label', text + ' — pulsa para ' + (on ? 'silenciar' : 'activar'));
    });
  }

  function emit() { subs.forEach(function (fn) { try { fn(on); } catch (e) {} }); }

  function set(value) {
    on = !!value;
    try { localStorage.setItem(KEY, on ? 'on' : 'off'); } catch (e) {}
    paint();
    emit();
  }

  // Delegado: sirve también para botones que se añaden después (la tarjeta)
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-sound-toggle]');
    if (!b) return;
    e.preventDefault();
    set(!on);
  });

  // Otra pestaña cambió la preferencia
  window.addEventListener('storage', function (e) {
    if (e.key !== KEY) return;
    on = read();
    paint();
    emit();
  });

  window.RFSound = {
    enabled: function () { return on; },
    set: set,
    onChange: function (fn) { subs.push(fn); },
    paint: paint
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', paint);
  else paint();
})();
