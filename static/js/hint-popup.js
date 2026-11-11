/* ──────────────────────────────────────────────────────
   RicitosFlow — Confirmación de pistas (popup del oso)

   Intercepta el envío de los formularios form[data-rf-hint] (macro hints de
   _macros.html) y abre el <dialog id="bear-pop">:
     · Cancelar (botón, Esc o clic fuera): se cierra sin enviar nada.
     · Confirmar: suena el oso (RFAudio.hint) y, al terminar, se envía el
       formulario UNA sola vez. El servidor (/hint/<cid>/<n>) es quien aplica
       −5 min y −25 pts, y lo hace de forma idempotente.
   Nada suena ni se descuenta antes de confirmar.
   Sin <dialog> moderno se usa window.confirm como respaldo.
   ────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var dlg = document.getElementById('bear-pop');
  var pending = null;      // formulario que espera confirmación
  var busy = false;        // ya se confirmó: no se admite otro envío

  function hintButtons() { return document.querySelectorAll('form[data-rf-hint] button'); }
  function lockAll(on) {
    Array.prototype.forEach.call(hintButtons(), function (b) {
      b.disabled = on;
      if (on) b.setAttribute('aria-busy', 'true'); else b.removeAttribute('aria-busy');
    });
    if (dlg) Array.prototype.forEach.call(dlg.querySelectorAll('.bp-btn'), function (b) { b.disabled = on; });
  }

  function send(form) {
    if (busy) return;
    busy = true;
    lockAll(true);
    if (dlg) dlg.classList.add('is-growling');
    var sent = false;
    var go = function () { if (sent) return; sent = true; form.submit(); };   // submit() no vuelve a disparar 'submit'
    if (window.RFAudio && window.RFAudio.hint) window.RFAudio.hint(go);
    else go();
    setTimeout(go, 6000);                                                     // red de seguridad
  }

  function open(form) {
    pending = form;
    if (dlg.open) return;
    dlg.classList.remove('is-growling');
    dlg.showModal();
    var no = dlg.querySelector('[data-bp-cancel]');
    if (no) no.focus();
  }
  function close() {
    pending = null;
    if (dlg.open) dlg.close();
  }

  // Captura: se ejecuta antes que cualquier otro manejador de envío
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.matches || !form.matches('form[data-rf-hint]')) return;
    e.preventDefault();
    if (busy) return;                                   // doble clic / envío simultáneo
    if (!dlg || typeof dlg.showModal !== 'function') {
      var msg = dlg ? dlg.querySelector('.bp-title').textContent + '\n\n' +
                      dlg.querySelector('.bp-costs').textContent.replace(/\s+/g, ' ').trim() + '\n\n' +
                      dlg.querySelector('.bp-ask').textContent
                    : '¿Estás seguro de que quieres recibir una pista?';
      if (window.confirm(msg)) send(form);
      return;
    }
    open(form);
  }, true);

  if (!dlg) return;

  dlg.querySelector('[data-bp-cancel]').addEventListener('click', function () { if (!busy) close(); });
  dlg.querySelector('[data-bp-confirm]').addEventListener('click', function () {
    if (busy || !pending) return;
    send(pending);
  });
  // Esc: solo cancela si todavía no se confirmó
  dlg.addEventListener('cancel', function (e) {
    e.preventDefault();
    if (!busy) close();
  });
  // Clic en el fondo oscuro (fuera de la tarjeta) = cancelar
  dlg.addEventListener('click', function (e) {
    if (e.target === dlg && !busy) close();
  });

  // Volver con «atrás» (bfcache): la página reaparece tal cual quedó
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    busy = false;
    lockAll(false);
    dlg.classList.remove('is-growling');
    close();
  });

  // La imagen pesa: se precarga para que el popup aparezca ya pintado
  var bg = getComputedStyle(dlg.querySelector('.bp-art')).backgroundImage;
  var m = bg && bg.match(/^url\(["']?(.*?)["']?\)$/);
  if (m) { var img = new Image(); img.decoding = 'async'; img.src = m[1]; }
})();
