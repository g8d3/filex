// filex.js — Shared functionality for code and md templates

// ===== Font Size =====
(function() {
  var fs = parseInt(localStorage.getItem('filex_font_size') || '13');
  function apply(px) {
    document.documentElement.style.setProperty('--content-font-size', px + 'px');
    var lbl = document.getElementById('fontSizeLabel');
    if (lbl) lbl.textContent = px + 'px';
  }
  apply(fs);
  window.changeFontSize = function(delta) {
    fs = Math.max(8, Math.min(32, fs + delta));
    apply(fs);
    localStorage.setItem('filex_font_size', fs);
    document.dispatchEvent(new CustomEvent('filex-fontchange', { detail: { size: fs } }));
  };
  window.getFontSize = function() { return fs; };
})();

// ===== Preferences =====
function loadPref(key, def) {
  try { var v = localStorage.getItem('filex_pref_' + key); return v !== null ? JSON.parse(v) : def; }
  catch(e) { return def; }
}
function setPref(key, val) {
  localStorage.setItem('filex_pref_' + key, JSON.stringify(val));
  applyPrefs();
}
function applyPrefs() {
  var border = loadPref('tableBorder', true);
  document.querySelectorAll('.md-content table, .md-content th, .md-content td').forEach(function(el) {
    el.style.border = border ? '1px solid #ccc' : 'none';
  });
  var pad = loadPref('cellPad', 6);
  var padVal = document.getElementById('prefPaddingVal');
  if (padVal) padVal.textContent = pad;
  var padRange = document.getElementById('prefPadding');
  if (padRange) padRange.value = pad;
  document.querySelectorAll('.md-content table th, .md-content table td').forEach(function(el) {
    el.style.padding = pad + 'px';
    el.style.margin = '0';
  });
}
function togglePrefs() {
  var p = document.getElementById('prefsPanel');
  if (p) p.style.display = p.style.display === 'none' ? '' : 'none';
}

// ===== Directory Modal =====
var modalData = null;
var modalSortCol = 'name';
var modalSortDir = 'asc';

function renderModalRows() {
  var rows = document.getElementById('modalRows');
  if (!rows || !modalData) return;
  var sorted = modalData.slice().sort(function(a, b) {
    var va = a[modalSortCol], vb = b[modalSortCol];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    if (va < vb) return modalSortDir === 'asc' ? -1 : 1;
    if (va > vb) return modalSortDir === 'asc' ? 1 : -1;
    return 0;
  });
  rows.innerHTML = '';
  if (sorted.length === 0) {
    rows.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#999">(vacío)</td></tr>';
    return;
  }
  sorted.forEach(function(e) {
    var cls = e.is_dir ? 'dir-row' : 'file-row';
    var label = e.is_dir ? e.name + '/' : e.name;
    var modal = document.getElementById('dirModal');
    var dir = modal ? modal.dataset.modalDir || '/' : '/';
    var href = dir.replace(/\/+$/, '') + '/' + encodeURIComponent(e.name) + (e.is_dir ? '/' : '');
    if (e.is_dir) {
      rows.innerHTML += '<tr class="' + cls + '">' +
        '<td><a href="#" data-dir="' + href + '" class="modal-dir-link">' + label.replace(/</g, '&lt;') + '</a></td>' +
        '<td class="size-col"></td>' +
        '<td class="date-col"></td></tr>';
    } else {
      rows.innerHTML += '<tr class="' + cls + '">' +
        '<td><a href="' + href + '">' + label.replace(/</g, '&lt;') + '</a></td>' +
        '<td class="size-col">' + e.size_fmt + '</td>' +
        '<td class="date-col">' + e.date.replace(/</g, '&lt;') + '</td></tr>';
    }
  });
  // Bind directory clicks to stay in modal
  document.querySelectorAll('.modal-dir-link').forEach(function(el) {
    el.onclick = function(e) {
      e.preventDefault();
      var d = this.getAttribute('data-dir');
      if (d) showDirModal(d);
    };
  });
  updateSortIcons();
}

function updateSortIcons() {
  document.querySelectorAll('#modalSortName, #modalSortSize, #modalSortDate').forEach(function(el) {
    el.textContent = '';
  });
  var icon = modalSortDir === 'asc' ? ' ▲' : ' ▼';
  var id = {name:'modalSortName', size:'modalSortSize', date:'modalSortDate'}[modalSortCol];
  var el = document.getElementById(id);
  if (el) el.textContent = icon;
}

function sortModal(col) {
  if (col === modalSortCol) {
    modalSortDir = modalSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    modalSortCol = col;
    modalSortDir = 'asc';
  }
  localStorage.setItem('filex_pref_modal_sort', JSON.stringify({col: modalSortCol, dir: modalSortDir}));
  renderModalRows();
}

function showDirModal(dir) {
  var modal = document.getElementById('dirModal');
  var title = document.getElementById('modalTitle');
  var rows = document.getElementById('modalRows');
  if (!modal || !title || !rows) return;
  title.textContent = '📁 ' + dir;
  rows.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#999">Cargando…</td></tr>';
  modal.style.display = 'flex';
  modal.dataset.modalDir = dir;
  var q = dir.indexOf('?') >= 0 ? '&format=json' : '?format=json';
  fetch(dir + q)
    .then(function(r) { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    .then(function(data) {
      modalData = data || [];
      var saved = loadPref('modal_sort', null);
      if (saved && saved.col) {
        modalSortCol = saved.col;
        modalSortDir = saved.dir || 'asc';
      } else {
        modalSortCol = 'name';
        modalSortDir = 'asc';
      }
      renderModalRows();
    })
    .catch(function(err) {
      rows.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#c00">' + err.message + '</td></tr>';
    });
}
function closeDirModal() {
  var el = document.getElementById('dirModal');
  if (el) el.style.display = 'none';
}
// ===== Breadcrumb clicks =====
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.bc-link').forEach(function(el) {
    el.addEventListener('click', function(e) {
      e.preventDefault();
      var dir = this.getAttribute('data-dir');
      if (dir) showDirModal(dir);
    });
  });
  var cb = document.getElementById('prefTableBorder');
  if (cb) cb.checked = loadPref('tableBorder', true);
  loadPref('cellPad', 6); // ensure default
  applyPrefs();
});
