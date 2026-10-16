(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // Theme toggle
  const toggle = $('#theme-toggle');
  if (toggle) toggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', next);
    try { localStorage.setItem('cs-theme', next); } catch (e) {}
  });

  // Auto-dismiss flash messages
  $$('.flash').forEach((el, i) => setTimeout(() => {
    if (window.bootstrap && document.body.contains(el)) bootstrap.Alert.getOrCreateInstance(el).close();
  }, 5500 + i * 600));

  // Landing: live ticket demo
  const demo = $('#demo');
  if (demo && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const steps = [
      { s: 'Open', cls: 'st-open', who: 'M', msg: 'Ticket received. Routing to the network team.' },
      { s: 'In Progress', cls: 'st-in-progress', who: 'A', msg: 'Admin assigned. Checking the access point on floor 3.' },
      { s: 'Resolved', cls: 'st-resolved', who: 'A', msg: 'Fixed: firmware updated and Wi-Fi is back for everyone.' },
    ];
    const pill = $('#demo-pill'), msg = $('#demo-msg'), av = $('#demo-av');
    let i = 0;
    const paint = () => {
      const st = steps[i];
      demo.dataset.step = i + 1;
      pill.className = 'pill ' + st.cls;
      pill.innerHTML = '<i></i>' + st.s;
      av.textContent = st.who;
      msg.classList.add('out');
      setTimeout(() => { msg.textContent = st.msg; msg.classList.remove('out'); }, 220);
      i = (i + 1) % steps.length;
    };
    paint();
    setInterval(paint, 2800);
  }

  // Password: show/hide + strength
  $$('.pw-toggle').forEach(btn => btn.addEventListener('click', () => {
    const input = btn.parentElement.querySelector('input');
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.textContent = show ? 'Hide' : 'Show';
  }));
  const meter = $('#strength');
  if (meter) {
    const input = $('#pw');
    input.addEventListener('input', () => {
      const v = input.value; let n = 0;
      if (v.length >= 10) n++;
      if (v.length >= 14) n++;
      if (/[a-z]/.test(v) && /[A-Z]/.test(v)) n++;
      if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) n++;
      meter.dataset.level = v ? Math.max(1, n) : 0;
    });
  }

  // Dashboard: filter + search
  const rows = $$('#ticket-rows tr[data-status]');
  if (rows.length) {
    let status = 'all', q = '';
    const none = $('#no-match'), shown = $('#shown-count');
    const apply = () => {
      let c = 0;
      rows.forEach(r => {
        const ok = (status === 'all' || r.dataset.status === status) && (!q || r.dataset.search.includes(q));
        r.hidden = !ok; if (ok) c++;
      });
      if (shown) shown.textContent = c;
      if (none) none.hidden = c !== 0;
    };
    $$('.chip').forEach(ch => ch.addEventListener('click', () => {
      $$('.chip').forEach(x => x.classList.remove('active')); ch.classList.add('active');
      status = ch.dataset.filter; apply();
    }));
    const s = $('#ticket-search');
    if (s) s.addEventListener('input', () => { q = s.value.trim().toLowerCase(); apply(); });
  }

  // Counters
  $$('textarea[data-counter], input[data-counter]').forEach(el => {
    const out = $(el.dataset.counter), max = el.getAttribute('maxlength');
    const upd = () => { if (out) out.textContent = el.value.length + ' / ' + max; };
    el.addEventListener('input', upd); upd();
  });

  // Dropzone
  const dz = $('#dropzone');
  if (dz) {
    const input = $('input', dz), label = $('#dz-name'), MAX = 5 * 1024 * 1024;
    const show = () => {
      const f = input.files[0];
      if (!f) { label.textContent = 'PNG, JPG, PDF, TXT or LOG, up to 5 MB'; return; }
      label.textContent = f.name + ' · ' + (f.size / 1024 > 1024 ? (f.size / 1048576).toFixed(1) + ' MB' : Math.ceil(f.size / 1024) + ' KB')
        + (f.size > MAX ? ' (too large)' : '');
    };
    input.addEventListener('change', show);
    ['dragenter', 'dragover'].forEach(e => dz.addEventListener(e, ev => { ev.preventDefault(); dz.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach(e => dz.addEventListener(e, () => dz.classList.remove('drag')));
    dz.addEventListener('drop', ev => { ev.preventDefault(); if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; show(); } });
  }

  // Prevent double submits
  $$('form').forEach(f => f.addEventListener('submit', () => {
    const b = $('button:not([type]),button[type=submit]', f);
    if (b && f.checkValidity()) setTimeout(() => { b.disabled = true; }, 0);
  }));
})();