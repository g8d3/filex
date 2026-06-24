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

// ===== Directory Font Size =====
(function() {
  var dfs = parseInt(localStorage.getItem('filex_dir_font_size') || '14');
  function applyDir(px) {
    var body = document.getElementById('dirFiles');
    if (body) body.style.setProperty('--dir-font-size', px + 'px');
    var lbl = document.getElementById('dirFontSizeLabel');
    if (lbl) lbl.textContent = px + 'px';
  }
  applyDir(dfs);
  window.changeDirFontSize = function(delta) {
    dfs = Math.max(10, Math.min(24, dfs + delta));
    applyDir(dfs);
    localStorage.setItem('filex_dir_font_size', dfs);
  };
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

function truncateName(name) {
  if (name.length <= 30) return name;
  var dot = name.lastIndexOf('.');
  var ext = dot > 0 ? name.slice(dot) : '';
  var base = dot > 0 ? name.slice(0, dot) : name;
  var avail = 30 - 3 - ext.length;
  if (avail < 8) return base.slice(0, 14) + '...' + name.slice(-12);
  var front = Math.ceil(avail * 0.55);
  var back = avail - front;
  return base.slice(0, front) + '...' + base.slice(-back) + ext;
}

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
    rows.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#999">(vacío)</td></tr>';
    return;
  }
  sorted.forEach(function(e) {
    var cls = e.is_dir ? 'dir-row' : 'file-row';
    var label = e.is_dir ? e.name + '/' : e.name;
    var display = truncateName(label);
    var files = document.getElementById('dirFiles');
    var dir = files ? files.dataset.dirFiles || '/' : '/';
    var href = dir.replace(/\/+$/, '') + '/' + encodeURIComponent(e.name) + (e.is_dir ? '/' : '');
    var tr = document.createElement('tr');
    tr.className = cls;
    tr.style.cursor = 'pointer';
    var safeHref = href.replace(/'/g, "\\'");
    var dlBtn = e.is_dir ? '' : '<button class="action-btn" onclick="event.stopPropagation();window.location.href=\'' + safeHref + '?dl=1\'" title="Descargar">⬇</button>';
    var renameBtn = '<button class="action-btn" onclick="event.stopPropagation();renameItem(\'' + safeHref + '\')" title="Renombrar">✏️</button>';
    var delBtn = '<button class="del-btn" onclick="event.stopPropagation();deleteItem(\'' + safeHref + '\')" title="Eliminar">🗑</button>';
    if (e.is_dir) {
      tr.innerHTML =
        '<td><a href="javascript:void(0)" data-dir="' + href + '" class="modal-dir-link">' + display.replace(/</g, '&lt;') + '</a></td>' +
        '<td class="size-col"></td>' +
        '<td class="date-col">' + e.date.replace(/</g, '&lt;') + '</td>' +
        '<td class="action-col">' + dlBtn + renameBtn + delBtn + '</td>';
      tr.addEventListener('click', function() {
        showDirModal(href);
      });
    } else {
      tr.innerHTML =
        '<td><a href="' + href + '">' + display.replace(/</g, '&lt;') + '</a></td>' +
        '<td class="size-col">' + e.size_fmt + '</td>' +
        '<td class="date-col">' + e.date.replace(/</g, '&lt;') + '</td>' +
        '<td class="action-col">' + dlBtn + renameBtn + delBtn + '</td>';
      tr.addEventListener('click', function() {
        window.location.href = href;
      });
    }
    rows.appendChild(tr);
  });
  updateSortIcons();
}

function updateSortIcons() {
  document.querySelectorAll('#modalSortName, #modalSortSize, #modalSortDate').forEach(function(el) {
    el.textContent = '';
  });
  var icon = modalSortDir === 'asc' ? ' ▲' : ' ▼';
  document.querySelectorAll('#modalSortName, #modalSortSize, #modalSortDate').forEach(function(el) {
    el.style.color = '#06c';
    el.style.fontWeight = 'bold';
  });
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
  var files = document.getElementById('dirFiles');
  var title = document.getElementById('modalTitle');
  var rows = document.getElementById('modalRows');
  if (!files || !title || !rows) return;
  var rootName = files.getAttribute('data-root-name') || '/';
  var parts = dir.replace(/\/+$/, '').split('/').filter(Boolean);
  var accum = '';
  var html = '<span class="bc-link" data-dir="/">📁 ' + rootName + '</span>';
  for (var i = 0; i < parts.length; i++) {
    accum += '/' + parts[i];
    if (i < parts.length - 1) {
      html += '<span class="bc-sep"> / </span><span class="bc-link" data-dir="' + accum + '/">' + parts[i] + '</span>';
    } else {
      html += '<span class="bc-sep"> / </span><span class="bc-current">' + parts[i] + '</span>';
    }
  }
  title.innerHTML = html;
  // Bind clicks on new breadcrumb links
  title.querySelectorAll('.bc-link').forEach(function(el) {
    el.addEventListener('click', function(e) {
      e.preventDefault();
      var d = this.getAttribute('data-dir');
      if (d) showDirModal(d);
    });
  });
  rows.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#999">Cargando…</td></tr>';
  files.style.display = '';
  files.dataset.dirFiles = dir;
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
      rows.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#c00">' + err.message + '</td></tr>';
    });
}
// ===== File actions (create dir, upload) =====
function getCurrentDir() {
  var files = document.getElementById('dirFiles');
  if (files && files.style.display !== 'none' && files.dataset.dirFiles) {
    return files.dataset.dirFiles.replace(/\/+$/, '') + '/';
  }
  return window.location.pathname.replace(/\/+$/, '') + '/';
}

function createDir() {
  var name = prompt('Nombre del nuevo directorio:');
  if (!name) return;
  var dir = getCurrentDir();
  fetch(dir + encodeURIComponent(name) + '/', { method: 'MKCOL' })
    .then(function(r) {
      if (r.status === 201) {
        showDirModal(dir);
      } else {
        return r.text().then(function(t) { alert('Error: ' + t); });
      }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

function createFile() {
  var name = prompt('Nombre del nuevo archivo:');
  if (!name) return;
  var dir = getCurrentDir();
  fetch(dir + encodeURIComponent(name), { method: 'PUT', body: '' })
    .then(function(r) {
      if (r.status === 201 || r.status === 200) {
        window.location.href = dir + encodeURIComponent(name);
      } else {
        return r.text().then(function(t) { alert('Error: ' + t); });
      }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

function uploadFile(input) {
  var file = input.files[0];
  if (!file) return;
  var dir = getCurrentDir();
  var reader = new FileReader();
  reader.onload = function(e) {
    fetch(dir + encodeURIComponent(file.name), { method: 'PUT', body: e.target.result })
      .then(function(r) {
        if (r.status === 201 || r.status === 200) {
          showDirModal(dir);
        } else {
          return r.text().then(function(t) { alert('Error: ' + t); });
        }
      })
      .catch(function(e) { alert('Error: ' + e.message); });
  };
  reader.readAsArrayBuffer(file);
  input.value = '';
}

function showFileActions() {
  var fileBtn = document.getElementById('newFileBtn');
  var dirBtn = document.getElementById('newDirBtn');
  var upload = document.getElementById('uploadBtn');
  if (fileBtn) fileBtn.style.display = '';
  if (dirBtn) dirBtn.style.display = '';
  if (upload) upload.style.display = '';
}

function deleteItem(path) {
  var name = path.split('/').filter(Boolean).pop() || path;
  if (!confirm('¿Eliminar "' + name + '"?')) return;
  fetch(path, { method: 'DELETE' })
    .then(function(r) {
      if (r.ok) {
        var dir = path.substring(0, path.lastIndexOf('/')) + '/';
        showDirModal(dir);
      } else {
        return r.text().then(function(t) { alert('Error: ' + t); });
      }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

function downloadCurrent() {
  var path = window.location.pathname;
  window.location.href = path + (path.indexOf('?') >= 0 ? '&' : '?') + 'dl=1';
}

function deleteCurrent() {
  var path = window.location.pathname;
  var name = path.split('/').filter(Boolean).pop() || path;
  if (!confirm('¿Eliminar "' + name + '"?')) return;
  fetch(path, { method: 'DELETE' })
    .then(function(r) {
      if (r.ok) {
        var dir = path.substring(0, path.lastIndexOf('/')) + '/';
        window.location.href = dir;
      } else {
        return r.text().then(function(t) { alert('Error: ' + t); });
      }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

function renameItem(path) {
  var oldName = path.split('/').filter(Boolean).pop() || path;
  var newName = prompt('Nuevo nombre para "' + oldName + '":', oldName);
  if (!newName || newName === oldName) return;
  var dir = path.substring(0, path.lastIndexOf('/') + 1);
  var dest = dir + encodeURIComponent(newName);
  fetch(path, { method: 'MOVE', headers: { 'Destination': dest } })
    .then(function(r) {
      if (r.ok) {
        showDirModal(dir);
      } else {
        return r.text().then(function(t) { alert('Error: ' + t); });
      }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

function closeDirModal() {
  var el = document.getElementById('dirFiles');
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
