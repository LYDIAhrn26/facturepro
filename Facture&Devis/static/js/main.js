/* ═══════════════════════════════════════════════════════════════════════════
   GL GLOBAL SERVICES — main.js
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

  // ── Auto-fermeture des flash messages ──────────────────────────────────
  setTimeout(function () {
    document.querySelectorAll('.flash').forEach(function (el) {
      el.style.transition = 'opacity .4s ease';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    });
  }, 4000);

  // ── Formatage des montants en euros (fr-FR) ────────────────────────────
  window.formatEur = function (val) {
    return parseFloat(val || 0).toLocaleString('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }) + ' €';
  };

  // ── Calcul HT / TVA / TTC ─────────────────────────────────────────────
  window.calcTotaux = function (htId, tvaSelectId, tvaLblId, tvaOutId, ttcOutId, htOutId) {
    var ht  = parseFloat(document.getElementById(htId)?.value || 0);
    var tva = parseFloat(document.getElementById(tvaSelectId)?.value || 20);
    var tvaAmt = ht * tva / 100;
    var ttc    = ht + tvaAmt;

    if (htOutId)  document.getElementById(htOutId).textContent  = formatEur(ht);
    if (tvaLblId) document.getElementById(tvaLblId).textContent = 'TVA (' + tva + '%)';
    if (tvaOutId) document.getElementById(tvaOutId).textContent = formatEur(tvaAmt);
    if (ttcOutId) document.getElementById(ttcOutId).textContent = formatEur(ttc);

    return { ht, tvaAmt, ttc };
  };

  // ── Afficher / masquer une bande de confirmation ───────────────────────
  window.toggleStrip = function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (el.style.display === 'flex') {
      el.style.display = 'none';
    } else {
      el.style.display = 'flex';
      el.style.animation = 'popIn .2s ease';
    }
  };

  // ── Toggle visibilité mot de passe ────────────────────────────────────
  window.togglePassword = function (inputId, iconId) {
    var input = document.getElementById(inputId || 'password');
    var icon  = document.getElementById(iconId  || 'eye-icon');
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      if (icon) icon.className = 'ti ti-eye-off';
    } else {
      input.type = 'password';
      if (icon) icon.className = 'ti ti-eye';
    }
  };

  // ── Animation d'entrée des lignes de tableau ───────────────────────────
  window.animateRows = function () {
    document.querySelectorAll('.table tbody tr').forEach(function (tr, i) {
      tr.style.opacity = '0';
      tr.style.transform = 'translateY(8px)';
      setTimeout(function () {
        tr.style.transition = 'opacity .2s ease, transform .2s ease';
        tr.style.opacity = '1';
        tr.style.transform = 'translateY(0)';
      }, i * 40);
    });
  };
  animateRows();

});
