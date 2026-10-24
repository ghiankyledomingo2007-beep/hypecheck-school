'use strict';

/* ── Icons ─────────────────────────────────────────────────────────────── */
const icons = {
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path d="M9 21v-8h6v8"/>',
  heart:'<path d="M20.8 4.7a5.5 5.5 0 0 0-7.8 0L12 5.8l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.5a5.5 5.5 0 0 0 0-7.8Z"/>',
  wallet:'<path d="M20 7V5a2 2 0 0 0-2-2L5 5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h15V7H5"/><path d="M20 12h-5v5h5"/><path d="M16 14.5h.1"/>',
  history:'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  leaf:'<path d="M20 3C9 3 3 6 4 14c1 6 9 7 13 3 4-4 3-10 3-14Z"/><path d="m3 21 11-11"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  'chevron-right':'<path d="m9 5 7 7-7 7"/>',
  'chevron-left':'<path d="m15 5-7 7 7 7"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  sparkle:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  'check-circle':'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  coffee:'<path d="M4 8h13v8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4ZM17 9h1a3 3 0 0 1 0 6h-1M7 2v3M12 2v3M2 22h18"/>',
  car:'<path d="m5 7 2-4h10l2 4 2 4v7H3v-7ZM3 11h18M6 18v3M18 18v3M6 14h2M16 14h2"/>',
  bag:'<path d="M5 7h14l2 14H3ZM8 8V6a4 4 0 0 1 8 0v2"/>',
  tech:'<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M10 18h4M10 5h4"/>',
  dots:'<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.1"/>',
  external:'<path d="M14 3h7v7M21 3 10 14M10 3H3v18h18v-7"/>',
  edit:'<path d="m15 4 5 5M3 21l5-1L21 7l-5-5L3 15Z"/>',
  sort:'<path d="M4 7h13M4 12h9M4 17h5M18 9v10m0 0-3-3m3 3 3-3"/>'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.sparkle}</svg>`;

/* ── Formatting ────────────────────────────────────────────────────────── */
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const currency = value => new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP',maximumFractionDigits:Number.isInteger(Number(value))?0:2}).format(value);
const cents = rows => rows.reduce((sum,row) => sum + Math.round(Number(row.amount)*100),0)/100;
const parseTime = value => new Date(value.replace(' ','T')+'Z');
const localDate = (value = new Date()) => `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`;
const shortDate = value => new Date(value.length === 10 ? value+'T12:00:00' : value.replace(' ','T')+'Z').toLocaleDateString('en',{month:'short',day:'numeric'});
const plural = (count, one, many = one+'s') => `${count} ${count===1?one:many}`;

const otto = (pose='happy', label='Otto, your thoughtful little companion') => {
  const effects = pose==='sleeping'
    ? '<svg class="otto-effects" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><text class="sleep-z" x="62" y="37">z</text><text class="sleep-z" x="62" y="37">z</text><text class="sleep-z" x="62" y="37">z</text></svg>'
    : pose==='thinking'
      ? '<svg class="otto-effects" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><text class="thought-mark" x="77" y="20">?</text></svg>'
      : '';
  return `<div class="otto ${pose}" role="img" aria-label="${escapeHTML(label)}"><span class="otto-frame" aria-hidden="true"></span>${effects}</div>`;
};

// small-space art: a head for tiny spots, a flat-bottomed bust that sits on a card's bottom edge
const HEADS = ['happy','proud','sleepy','thinking','worried','wow'];
const head = mood => `<span class="otto-head" style="--i:${HEADS.indexOf(mood)}" aria-hidden="true"></span>`;
const coin = '<img class="coin" src="/assets/otto-coin-icon.webp" alt="" width="160" height="160">';
const peek = (kind, label, width, height) => `<img class="peek peek-${kind}" src="/assets/otto-peek-${kind}.webp?v=2" alt="${escapeHTML(label)}" width="${width}" height="${height}" decoding="async">`;

/* ── State ─────────────────────────────────────────────────────────────── */
const main = document.querySelector('main');
const sheet = document.querySelector('#sheet');
const SHEET_QUERY = matchMedia('(max-width:760px)');
// [route, icon, label]
const links = [['home','home','Home'],['wishlist','heart','Wishlist'],['money','wallet','Spending'],['history','history','Decisions']];
const aliases = {overview:'home', expenses:'money', budget:'money'};
const categoryMeta = {1:['tech','tech'],2:['bag','style'],3:['leaf','lifestyle'],4:['coffee','food'],5:['car','transport']};

let database, page='home', filter='all', search='', sort='newest', activeDecision=null, selectedDecision=null, saving=false, toastTimer;
let month = new Date().getMonth()+1, year = new Date().getFullYear();

const routeOf = hash => { const key = hash.slice(1) || 'home'; const route = aliases[key] || key; return links.some(l => l[0]===route) ? route : 'home'; };
const cat = id => database.categories.find(c => c.category_id===id)?.category_name || 'Other';
const catIcon = id => categoryMeta[id]?.[0] || 'dots';
const catTone = id => categoryMeta[id]?.[1] || 'other';
const waiting = () => database.wishlist_items.filter(w => w.status==='waiting');
const ready = item => item.status==='waiting' && parseTime(item.wait_until) <= new Date();
const currentExpenses = () => database.expenses.filter(e => e.expense_date.startsWith(`${year}-${String(month).padStart(2,'0')}`));
const currentBudget = () => database.monthly_budgets.find(b => b.budget_year===year && b.budget_month===month);
const monthTitle = () => new Date(year,month-1,1).toLocaleDateString('en',{month:'long',year:'numeric'});
const expenseSort = (a,b) => b.expense_date.localeCompare(a.expense_date) || b.expense_id-a.expense_id;

function waitText(item){
  if(item.status!=='waiting') return item.status==='bought' ? 'Bought' : 'Let go';
  const minutes = Math.max(0, Math.ceil((parseTime(item.wait_until)-Date.now())/60000));
  if(!minutes) return 'Ready to decide';
  const days = Math.floor(minutes/1440), hours = Math.floor(minutes%1440/60), mins = minutes%60;
  return `${days?days+'d ':''}${hours?hours+'h ':''}${!days&&!hours?mins+'m ':''}left`;
}
function waitProgress(item){
  const start = parseTime(item.created_at).getTime(), end = parseTime(item.wait_until).getTime();
  return end>start ? Math.min(1, Math.max(0, (Date.now()-start)/(end-start))) : 1;
}

/* ── Shell ─────────────────────────────────────────────────────────────── */
function decorate(root=document){ root.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon)); }

// every request gets a deadline: a stalled network must never trap the user in a sheet
const REQUEST_TIMEOUT_MS = 20000;
async function api(url, options={}){
  try{
    return await fetch(url, { ...options, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) });
  }catch(problem){
    const slow = problem && (problem.name==='TimeoutError' || problem.name==='AbortError');
    throw new Error(slow ? 'That took too long. Check your connection and try again.' : 'Couldn’t connect. Please try again.');
  }
}
// a body that isn't JSON (a gateway error page, a timeout) must not surface as "Unexpected token '<'"
async function readJson(response){ try{ return await response.json(); }catch{ return {}; } }

async function load(){
  const response = await api('/api/state');
  if(response.status===401){ showAuth(location.pathname.startsWith('/signup') ? 'register' : 'login'); return false; }  // false: the caller must not celebrate over a login screen
  if(!response.ok) throw new Error('Your space couldn’t load. Please try again.');
  database = await response.json();
  document.body.classList.remove('signed-out');
  if(/^\/(login|signin|signup)/.test(location.pathname)) window.history.replaceState(null,'','/app'+location.hash);  // signed in: this is the app now
  render();
  return true;
}

/* ── Signing in ────────────────────────────────────────────────────────── */
let authOptions = {signup:false, needs_code:false, google:false, google_open:false};
// Google's own mark, unmodified, as their branding rules require
const googleMark = '<svg class="g-mark" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
const AUTH_ERRORS = {google:'Google sign-in didn’t finish. Please try again.', invite:'No account uses that Google email yet. Tap “Create an account”, enter your sign-up code, then continue with Google.', throttled:'Too many attempts. Try again in 15 minutes.', server:'Couldn’t reach the database. Please try again.'};
async function showAuth(mode='login'){
  database = null; document.body.classList.add('signed-out'); document.title = 'Sign in · HypeCheck';
  if(sheet.open) sheet.close();
  try { authOptions = await (await api('/api/auth/options')).json(); } catch { /* keep the closed defaults */ }
  const register = mode==='register' && authOptions.signup;
  const problem = AUTH_ERRORS[new URLSearchParams(location.search).get('auth_error')] || '';
  if(location.search) window.history.replaceState(null,'',location.pathname+location.hash);  // show the message once
  const email = `<div class="field"><label for="auth-email">Email</label><input id="auth-email" name="email" type="email" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="255" required></div>`;
  const password = `<div class="field"><label for="auth-password">Password</label><input id="auth-password" name="password" type="password" autocomplete="${register?'new-password':'current-password'}" minlength="${register?10:1}" maxlength="200" enterkeyhint="go" required>${register?'<small>At least 10 characters. A few random words works well.</small>':''}</div>`;
  main.innerHTML = `<div class="view auth">${peek('hello','Otto peeking over to say hello',480,394)}<section class="card auth-card"><h1>${register?'Make your space.':'Welcome back.'}</h1><p class="sheet-description">${register?'Your wishes, your pace. Only you can see them.':'Sign in to see your wishes.'}</p><div class="form-error ${problem?'show':''}" role="alert">${problem}</div>
    ${authOptions.google?`<button type="button" class="btn btn-google" data-action="google">${googleMark}${register?'Sign up with Google':'Continue with Google'}</button>${authOptions.google_open&&!register?'<p class="google-note">New here? Google creates your account in one tap.</p>':''}<p class="or"><span>${register?'or use an email and the sign-up code':'or'}</span></p>`:''}
    <form data-form="${register?'register':'login'}">${register?`<div class="field"><label for="auth-name">Your name</label><input id="auth-name" name="full_name" autocomplete="name" maxlength="100" required></div>`:''}${email}${password}${register&&authOptions.needs_code?`<div class="field"><label for="auth-code">Sign-up code</label><input id="auth-code" name="signup_code" autocomplete="off" autocapitalize="none" maxlength="100" required><small>This app is invite-only. Ask the owner for the code.</small></div>`:''}<button type="submit" class="btn btn-primary auth-submit">${register?'Create account':'Sign in'}</button></form>
    ${authOptions.signup?`<button class="link auth-switch" data-action="${register?'auth-login':'auth-register'}">${register?'I already have an account':'Create an account'}</button>`:''}<p class="auth-legal">By continuing you agree to the <a href="/terms.html">Terms</a> and <a href="/privacy.html">Privacy Policy</a>.</p></section><p class="auth-foot">Want it. Wait. Decide.</p></div>`;
  main.querySelector('input')?.focus({preventScroll:true});
}
async function signOut(){
  try {
    const response = await api('/api/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    if(!response.ok) throw new Error('logout rejected');
    showAuth();
  } catch { toast('Couldn’t sign out. Check your connection and try again.'); }
}
function navigate(next){
  filter='all'; search='';
  if(routeOf(location.hash)===next){ page=next; render(); window.scrollTo({top:0,behavior:'instant'}); }
  else location.hash = next;
}
function renderNav(){
  const readyCount = database.wishlist_items.filter(ready).length;
  const badge = key => key!=='wishlist' ? '' : readyCount ? `<b class="badge ready">${readyCount}</b>` : waiting().length ? `<b class="badge">${waiting().length}</b>` : '';
  const item = ([key,symbol,text]) => `<a href="#${key}" class="${page===key?'active':''}" ${page===key?'aria-current="page"':''}>${icon(symbol)}<span>${text}</span>${badge(key)}</a>`;
  document.querySelector('#rail-nav').innerHTML = links.map(item).join('');
  document.querySelector('#dock').innerHTML = links.slice(0,2).map(item).join('') + `<button class="dock-add" data-action="add" aria-label="Add a wish or an expense">${icon('plus')}</button>` + links.slice(2).map(item).join('');
  const bell = document.querySelector('#bell-count');
  bell.hidden = !readyCount; bell.textContent = readyCount;
  bell.parentElement.setAttribute('aria-label', readyCount ? `${plural(readyCount,'wish','wishes')} ready for a decision` : 'Nothing is ready for a decision yet');
}
// Every render replaces the whole page, which throws keyboard focus back to <body>: a filter tap,
// a month step or a save would restart a keyboard or screen-reader user at the top. Remember what
// was focused by its action, and give focus back to the element that replaced it.
function focusMark(el){
  if(!el || el===document.body || !main.contains(el) && !el.closest('#rail-nav, #dock')) return null;
  const { action, value } = el.dataset;
  if(action) return `[data-action="${action}"]${value ? `[data-value="${value}"]` : ''}`;
  if(el.id) return `#${el.id}`;
  const href = el.getAttribute?.('href');
  return href?.startsWith('#') ? `[href="${href}"]` : null;
}
function render(){
  const mark = focusMark(document.activeElement);
  document.title = `${links.find(l => l[0]===page)[2]} · HypeCheck`;
  renderNav();
  main.innerHTML = ({home, wishlist, money, history: historyPage})[page]();
  if(mark) document.querySelector(mark)?.focus({ preventScroll: true });
}

/* ── Shared pieces ─────────────────────────────────────────────────────── */
const pageHead = (title, subtitle, actions='') => `<header class="page-head"><div><h1>${title}</h1>${subtitle?`<p>${subtitle}</p>`:''}</div>${actions?`<div class="page-actions">${actions}</div>`:''}</header>`;
const sectionHead = (title, action='') => `<div class="section-head"><h2>${title}</h2>${action}</div>`;
const bar = (fraction, tone='') => `<span class="bar ${tone}"><i style="width:${Math.round(fraction*100)}%"></i></span>`;
const empty = (title, text, action, label) => `<div class="empty">${otto('sleeping')}<h3>${title}</h3><p>${text}</p>${action?`<button class="btn btn-primary" data-action="${action}">${icon('plus')}${label}</button>`:''}</div>`;
const monthPicker = () => `<div class="month-picker"><button class="icon-btn" data-action="month-prev" aria-label="Previous month">${icon('chevron-left')}</button><strong>${monthTitle()}</strong><button class="icon-btn" data-action="month-next" aria-label="Next month">${icon('chevron-right')}</button></div>`;

function thumb(item){
  const match = /headphone/i.test(item.item_name)?'headphones':/sneaker/i.test(item.item_name)?'sneaker':/camera/i.test(item.item_name)?'camera':null;
  return match
    ? `<span class="thumb"><span class="product-image ${match}" role="img" aria-label="Illustration of ${escapeHTML(item.item_name)}"></span></span>`
    : `<span class="thumb tone-${catTone(item.category_id)}" aria-hidden="true">${icon(catIcon(item.category_id))}</span>`;
}
function wishCard(item){
  const isReady = ready(item), decided = item.status!=='waiting';
  const state = isReady ? 'ready' : decided ? item.status : 'waiting';
  return `<button class="wish is-${state}" data-action="${decided?'history':'review'}" data-id="${item.wishlist_item_id}">
    ${thumb(item)}
    <span class="wish-main">
      <span class="wish-cat">${escapeHTML(cat(item.category_id))}</span>
      <span class="wish-name">${escapeHTML(item.item_name)}</span>
      <span class="wish-price money">${currency(item.estimated_price)}</span>
    </span>
    <span class="wish-state">
      <span class="chip chip-${state}">${icon(isReady?'check-circle':decided?(item.status==='bought'?'bag':'leaf'):'clock')}<span data-countdown="${item.wishlist_item_id}">${waitText(item)}</span></span>
      ${decided||isReady ? '' : bar(waitProgress(item),'amber')}
    </span>
  </button>`;
}
function expenseRow(e, removable=false){
  return `<div class="row"><span class="tile tone-${catTone(e.category_id)}">${icon(catIcon(e.category_id))}</span><button class="row-main" data-action="edit-expense" data-id="${e.expense_id}" aria-label="Edit ${escapeHTML(e.description)}"><strong>${escapeHTML(e.description)}</strong><small>${escapeHTML(cat(e.category_id))}${removable?'':' · '+shortDate(e.expense_date)}</small></button><span class="row-amount money">−${currency(e.amount)}</span>${removable?`<button class="icon-btn quiet" data-action="delete-expense" data-id="${e.expense_id}" aria-label="Remove ${escapeHTML(e.description)}">${icon('trash')}</button>`:''}</div>`;
}

/* ── Home ──────────────────────────────────────────────────────────────── */
// item = the wish that most needs attention: a ready one, else the soonest check-in
function focusCard(item, readyCount){
  const next = item;
  if(readyCount){
    const days = Math.max(1, Math.round((parseTime(item.wait_until)-parseTime(item.created_at))/86400000));
    return `<section class="focus is-ready" aria-labelledby="focus-title"><div class="focus-copy"><p class="eyebrow">${icon('check-circle')}Ready to decide</p><h2 id="focus-title">${escapeHTML(item.item_name)}</h2><p class="focus-meta"><span class="money">${currency(item.estimated_price)}</span> · you waited ${plural(days,'day')}</p><div class="focus-actions"><button class="btn btn-primary" data-action="review" data-id="${item.wishlist_item_id}">Decide now</button>${readyCount>1?`<button class="btn btn-ghost" data-action="ready">+${readyCount-1} more ready</button>`:''}</div></div>${otto('thinking','Otto wondering what you’ll choose')}</section>`;
  }
  if(next){
    return `<section class="focus" aria-labelledby="focus-title"><div class="focus-copy"><p class="eyebrow">${icon('clock')}Next check-in</p><h2 id="focus-title" class="countdown" data-countdown="${next.wishlist_item_id}">${waitText(next)}</h2><p class="focus-meta">${escapeHTML(next.item_name)} · <span class="money">${currency(next.estimated_price)}</span></p>${bar(waitProgress(next))}<div class="focus-actions"><button class="btn btn-soft" data-action="review" data-id="${next.wishlist_item_id}">View wish</button></div></div>${otto('sleeping','Otto napping while you wait')}</section>`;
  }
  return `<section class="focus" aria-labelledby="focus-title"><div class="focus-copy"><p class="eyebrow">${icon('leaf')}Small pauses. Better choices.</p><h2 id="focus-title">Love it now.<br>Still love it later?</h2><p class="focus-meta">Save what you want and give the hype time to settle.</p><div class="focus-actions"><button class="btn btn-primary" data-action="new-wish">${icon('plus')}Add a wish</button></div></div>${otto('happy')}</section>`;
}
function home(){
  const today = new Date(); month = today.getMonth()+1; year = today.getFullYear();
  const wishes = waiting(), skipped = database.wishlist_items.filter(w => w.status==='skipped');
  const spent = cents(currentExpenses()), limit = Number(currentBudget()?.budget_amount||0), left = limit-spent;
  const readyCount = wishes.filter(ready).length, hour = today.getHours();
  const ordered = [...wishes].sort((a,b) => ready(b)-ready(a) || a.wait_until.localeCompare(b.wait_until));
  const queue = ordered.slice(1,4); // ordered[0] is the focus card
  const recent = currentExpenses().sort(expenseSort).slice(0,3);
  const summary = wishes.length ? `${plural(wishes.length,'wish','wishes')} waiting${readyCount?` · ${readyCount} ready to decide`:''}` : 'Nothing waiting right now.';
  return `<div class="view view-home">${pageHead(`Good ${hour<12?'morning':hour<18?'afternoon':'evening'}.`, summary)}
    <div class="home-grid">
      ${focusCard(ordered[0], readyCount)}
      <section class="stats" aria-label="Your numbers">
        <button class="stat stat-hero" data-action="history"><span class="stat-label">${coin}Money you didn’t spend</span><span class="stat-value money">${currency(skipped.reduce((s,w) => s+Number(w.estimated_price),0))}</span><span class="stat-note">${plural(skipped.length,'wish','wishes')} let go</span>${peek('coin','Otto hugging a gold coin',480,558)}</button>
        <button class="stat" data-action="wishlist"><span class="stat-label">${icon('heart')}On your wishlist</span><span class="stat-value money">${currency(wishes.reduce((s,w) => s+Number(w.estimated_price),0))}</span><span class="stat-note">${plural(wishes.length,'wish','wishes')} waiting</span></button>
        <button class="stat" data-action="money"><span class="stat-label">${icon('wallet')}Left this month</span><span class="stat-value money ${left<0?'over':''}">${currency(left)}</span>${limit?bar(Math.min(spent/limit,1), left<0?'rose':''):''}<span class="stat-note">${limit?`${Math.round(spent/limit*100)}% of ${currency(limit)} used`:'No budget set yet'}</span></button>
      </section>
      <section class="home-queue">${sectionHead('Waiting room', wishes.length?`<button class="link" data-action="wishlist">See all</button>`:'')}<div class="wish-list">${queue.length?queue.map(wishCard).join(''):wishes.length?'<p class="muted">That’s the only one. Nothing else is waiting.</p>':empty('Room for something good.','Save something you want, then give yourself time to think.','new-wish','Add a wish')}</div></section>
      <section class="home-side">
        <div class="card">${sectionHead('Recent spending',`<button class="link" data-action="new-expense">${icon('plus')}Log</button>`)}${recent.length?recent.map(e => expenseRow(e)).join(''):'<p class="muted">Nothing spent this month. A fresh start.</p>'}<button class="link card-foot" data-action="money">All spending</button></div>
        <aside class="thought"><p class="eyebrow">${icon('sparkle')}A thought from Otto</p><h3>You can like it without owning it.</h3><p>Sometimes the best thing you bring home is peace of mind.</p>${otto('thinking')}</aside>
      </section>
    </div></div>`;
}

/* ── Wishlist ──────────────────────────────────────────────────────────── */
function filteredWishes(){
  const match = w => filter==='history' ? w.status!=='waiting' : filter==='ready' ? ready(w) : filter==='waiting' ? w.status==='waiting'&&!ready(w) : w.status==='waiting';
  const order = (a,b) => ready(b)-ready(a) || (sort==='price' ? a.estimated_price-b.estimated_price : sort==='soonest' ? a.wait_until.localeCompare(b.wait_until) : b.created_at.localeCompare(a.created_at));
  return database.wishlist_items.filter(match).filter(w => `${w.item_name} ${cat(w.category_id)}`.toLowerCase().includes(search.toLowerCase())).sort(order);
}
function wishCards(){
  const wishes = filteredWishes();
  if(wishes.length) return wishes.map(wishCard).join('');
  if(search) return empty('No wishes found.','Try a different name or category.');
  if(filter==='ready') return empty('Good things take time.','Nothing is ready yet. Otto’s keeping an eye on the clock.');
  if(filter==='history') return empty('No decisions yet.','Wishes you buy or let go will land here.');
  return empty('Room for something good.','Save something you want, then give yourself time to think.','new-wish','Add a wish');
}
function filterBar(){
  const items = database.wishlist_items;
  const counts = {all:waiting().length, waiting:items.filter(w => w.status==='waiting'&&!ready(w)).length, ready:items.filter(ready).length, history:items.filter(w => w.status!=='waiting').length};
  const tabs = [['all','All'],['waiting','Waiting'],['ready','Ready'],['history','Decided']].map(([key,label]) => `<button class="seg ${filter===key?'active':''}" data-action="filter" data-value="${key}" aria-pressed="${filter===key}">${label}<b>${counts[key]}</b></button>`).join('');
  const option = (value,label) => `<option value="${value}" ${sort===value?'selected':''}>${label}</option>`;
  return `<div class="toolbar"><div class="segs" role="group" aria-label="Filter wishlist">${tabs}</div><label class="sort">${icon('sort')}<span class="visually-hidden">Sort wishlist</span><select id="sort">${option('newest','Newest')}${option('price','Price')}${option('soonest','Ready soonest')}</select></label></div>`;
}
function wishlist(){
  const wishes = waiting();
  return `<div class="view">${pageHead('Wishlist', wishes.length?`${plural(wishes.length,'wish','wishes')} waiting · <span class="money">${currency(wishes.reduce((s,w) => s+Number(w.estimated_price),0))}</span>`:'A home for the things on your mind.')}
    <label class="search">${icon('search')}<input id="wish-search" type="search" enterkeyhint="search" placeholder="Search your wishlist" aria-label="Search wishlist" value="${escapeHTML(search)}"></label>
    ${filterBar()}<div class="wish-grid" id="wish-grid">${wishCards()}</div></div>`;
}

/* ── Spending (expenses + budget) ──────────────────────────────────────── */
function ring(fraction, over){
  const r=52, c=2*Math.PI*r;
  return `<svg class="ring ${over?'over':''}" viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="${r}"/><circle class="ring-fill" cx="60" cy="60" r="${r}" stroke-dasharray="${(c*fraction).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 60 60)"/></svg>`;
}
function expenseGroups(){
  const rows = currentExpenses().filter(e => `${e.description} ${cat(e.category_id)}`.toLowerCase().includes(search.toLowerCase())).sort(expenseSort);
  if(!rows.length) return `<div class="empty empty-small">${peek('hello','Otto peeking over',480,394)}<h3>Nothing here yet.</h3><p>${search?'Try a different search.':'Log an expense or pick another month.'}</p></div>`;
  const today = localDate(), yesterday = localDate(new Date(Date.now()-86400000));
  const title = date => date===today ? 'Today' : date===yesterday ? 'Yesterday' : new Date(date+'T12:00:00').toLocaleDateString('en',{weekday:'short',month:'short',day:'numeric'});
  const groups = new Map();
  rows.forEach(e => groups.set(e.expense_date, [...(groups.get(e.expense_date)||[]), e]));
  return [...groups].map(([date,list]) => `<div class="day"><div class="day-head"><span>${title(date)}</span><span class="money">${currency(cents(list))}</span></div>${list.map(e => expenseRow(e,true)).join('')}</div>`).join('');
}
function money(){
  const rows = currentExpenses(), spent = cents(rows), limit = Number(currentBudget()?.budget_amount||0), left = limit-spent;
  const days = new Date(year,month,0).getDate();
  // a month in progress averages over the days so far, not the days it will have
  const now = new Date(), thisMonth = now.getFullYear()===year && now.getMonth()+1===month;
  const elapsedDays = thisMonth ? Math.max(1, Math.min(now.getDate(), days)) : days;
  const grouped = database.categories.map(c => ({...c, total:cents(rows.filter(e => e.category_id===c.category_id))})).filter(c => c.total>0).sort((a,b) => b.total-a.total);
  return `<div class="view">${pageHead('Spending','', `<button class="btn btn-soft desktop-only" data-action="new-expense">${icon('plus')}Log expense</button>`)}
    <div class="money-tools">${monthPicker()}<button class="link" data-action="export">${icon('download')}Export CSV</button></div>
    <div class="money-grid">
      <div class="money-side">
        <section class="card budget" aria-label="Monthly budget">
          <div class="budget-ring" aria-label="${limit?`${currency(Math.max(left,0))} left of ${currency(limit)}, ${Math.round(Math.min(spent/limit,1)*100)} percent used`:'No budget set yet'}">${ring(limit?Math.min(spent/limit,1):0, left<0)}<div><small>${limit?(left<0?'Over by':'Left to spend'):'No budget yet'}</small><strong class="money ${left<0?'over':''}">${currency(Math.abs(left))}</strong>${limit?`<span>of ${currency(limit)}</span>`:''}</div></div>
          ${left<0&&limit?`<div class="over-note">${otto('worried','Otto looking a little concerned')}<p><strong>A little over the plan.</strong> No judgment. Look at where it went, then adjust the budget or the rest of the month.</p></div>`:''}<dl class="budget-facts"><div><dt>Spent</dt><dd class="money">${currency(spent)}</dd></div><div><dt>Daily average</dt><dd class="money">${currency(Math.round(spent/elapsedDays))}</dd></div><div><dt>Entries</dt><dd>${rows.length}</dd></div></dl>
          <button class="btn btn-soft" data-action="set-budget">${icon('edit')}${currentBudget()?'Adjust budget':'Set a budget'}</button>
        </section>
        ${grouped.length?`<section class="card">${sectionHead('Where it’s going')}<div class="stack" aria-hidden="true">${grouped.map(c => `<i class="tone-${catTone(c.category_id)}" style="flex:${c.total}"></i>`).join('')}</div>${grouped.map(c => `<div class="legend"><span class="dot tone-${catTone(c.category_id)}"></span><span>${escapeHTML(c.category_name)}</span><small>${Math.round(c.total/spent*100)}%</small><strong class="money">${currency(c.total)}</strong></div>`).join('')}</section>`:''}
      </div>
      <section class="card ledger">${sectionHead('Expenses')}<label class="search">${icon('search')}<input id="expense-search" type="search" enterkeyhint="search" aria-label="Search expenses" placeholder="Search expenses" value="${escapeHTML(search)}"></label><div id="expense-rows">${expenseGroups()}</div></section>
    </div></div>`;
}

/* ── Decisions ─────────────────────────────────────────────────────────── */
function historyPage(){
  const logs = [...database.decision_logs].sort((a,b) => b.decided_at.localeCompare(a.decided_at));
  const kept = database.wishlist_items.filter(w => w.status==='skipped').reduce((s,w) => s+Number(w.estimated_price),0);
  const count = kind => logs.filter(l => l.decision===kind).length;
  const verdict = {buy:['happy','Chose to buy','bought'], skip:['proud','Let it go','skipped'], wait_longer:['sleepy','Gave it more time','waiting']};
  return `<div class="view">${pageHead('Decisions','Every pause tells a story.')}
    ${logs.length?`<div class="tally"><div class="tally-main"><small>Kept in your pocket</small><strong class="money">${currency(kept)}</strong>${peek('coin','Otto hugging a gold coin',480,558)}</div><div><strong>${count('skip')}</strong><small>let go</small></div><div><strong>${count('buy')}</strong><small>bought</small></div><div><strong>${count('wait_longer')}</strong><small>extended</small></div></div>
    <ol class="timeline">${logs.map(log => { const item = database.wishlist_items.find(w => w.wishlist_item_id===log.wishlist_item_id), [symbol,label,tone] = verdict[log.decision]; return `<li class="is-${tone}"><span class="timeline-dot">${head(symbol)}</span><div class="card"><div class="timeline-top"><strong>${escapeHTML(item?.item_name || 'A wishlist item')}</strong><time>${shortDate(log.decided_at)}</time></div><p class="timeline-verdict">${label}${item?` · <span class="money">${currency(item.estimated_price)}</span>`:''}</p>${log.reflection?`<blockquote>“${escapeHTML(log.reflection)}”</blockquote>`:''}${log.new_wait_until?`<p class="muted">New check-in: ${shortDate(log.new_wait_until)}</p>`:''}</div></li>`; }).join('')}</ol>`
    : empty('Your story starts with a pause.','Your decisions will find a home here.','new-wish','Add a wish')}</div>`;
}

/* ── Sheets ────────────────────────────────────────────────────────────── */
function showSheet(title, description, content){
  document.querySelector('#sheet-body').innerHTML = `<div class="sheet-head"><span class="grabber" aria-hidden="true"></span><div class="sheet-title"><h2 id="sheet-title">${title}</h2><button class="icon-btn" data-action="close" aria-label="Close">${icon('close')}</button></div></div><div class="sheet-content">${description?`<p class="sheet-description">${description}</p>`:''}<div class="form-error" role="alert"></div>${content}</div>`;
  if(!sheet.open) sheet.showModal();
  // swapping the body of an open sheet (add menu to form, decision to result) leaves focus on the
  // dialog root and announces nothing: move it to the new heading so the change is spoken
  else { const heading = document.querySelector('#sheet-title'); if(heading){ heading.tabIndex = -1; heading.focus({ preventScroll: true }); } }
}
const formActions = (label, cancel='Cancel') => `<div class="sheet-actions"><button type="button" class="btn btn-soft" data-action="close">${cancel}</button><button type="submit" class="btn btn-primary">${label}</button></div>`;
const categoryChips = (selected) => `<fieldset class="field"><legend>Category</legend><div class="chips">${database.categories.map((c,i) => `<label class="pick"><input type="radio" name="category_id" value="${c.category_id}" ${i?'':'required'} ${c.category_id===selected?'checked':''}><span>${icon(catIcon(c.category_id))}${escapeHTML(c.category_name)}</span></label>`).join('')}</div></fieldset>`;
const waitOptions = () => `<fieldset class="field"><legend>How long should you wait?</legend><div class="chips chips-even">${[[24,'24 hours'],[48,'48 hours'],[72,'3 days'],[168,'1 week']].map(([n,label]) => `<label class="pick"><input type="radio" name="wait_hours" value="${n}" ${n===48?'checked':''}><span>${label}</span></label>`).join('')}</div></fieldset>`;
const amountField = (id, name, label, value='', min='0.01') => `<div class="field"><label for="${id}">${label}</label><div class="amount"><span aria-hidden="true">₱</span><input id="${id}" name="${name}" type="number" inputmode="decimal" min="${min}" max="9999999999.99" step="0.01" placeholder="0.00" value="${value}" required></div></div>`;

function addMenu(){
  showSheet('What would you like to add?','',`<div class="add-menu">${peek('hello','Otto peeking over to say hello',480,394)}<button class="add-option" data-action="new-wish"><span class="tile tone-lifestyle">${icon('heart')}</span><span><strong>A wish</strong><small>Something you want. Start the wait.</small></span>${icon('chevron-right')}</button><button class="add-option" data-action="new-expense"><span class="tile tone-food">${icon('wallet')}</span><span><strong>An expense</strong><small>Something you already paid for.</small></span>${icon('chevron-right')}</button></div>`);
}
function wishForm(item){
  const v = key => escapeHTML(item?.[key] ?? ''), hasExtra = item && (item.notes || item.product_url);
  const fields = `<div class="field"><label for="item-name">What is it?</label><input id="item-name" name="item_name" placeholder="Those headphones I keep thinking about" maxlength="150" autocomplete="off" value="${v('item_name')}" required></div>${amountField('wish-price','estimated_price','Estimated price',v('estimated_price'),'0')}${categoryChips(item?.category_id)}${item?'':waitOptions()}<details class="more" ${hasExtra?'open':''}><summary>${icon('plus')}Add a note or a link</summary><div class="field"><label for="wish-notes">Why do you want it?</label><textarea id="wish-notes" name="notes" maxlength="2000" placeholder="What would this add to my everyday life?">${v('notes')}</textarea></div><div class="field"><label for="product-url">Product link</label><input type="url" id="product-url" name="product_url" maxlength="2048" placeholder="https://" autocapitalize="none" value="${v('product_url')}"></div></details>`;
  if(item) showSheet('Edit wish','Change the details. Your wait keeps running as it was.',`<form data-form="wish-update"><input type="hidden" name="wishlist_item_id" value="${item.wishlist_item_id}">${fields}${formActions('Save changes')}</form>`);
  else showSheet('Something caught your eye?','Give it a home here. Decide when the excitement settles.',`<form data-form="wish">${fields}${formActions('Start my pause')}</form>`);
}
const newWish = () => wishForm();
function removeWish(id){
  const item = database.wishlist_items.find(w => w.wishlist_item_id===id); if(!item) return;
  showSheet('Remove this wish?',`${escapeHTML(item.item_name)} · ${currency(item.estimated_price)}`,`<form data-form="wish-delete"><input type="hidden" name="wishlist_item_id" value="${id}"><p class="prompt">It leaves your wishlist without being decided, so it won’t count as money saved. This can’t be undone.</p><div class="sheet-actions"><button type="button" class="btn btn-soft" data-action="close">Keep it</button><button type="submit" class="btn btn-danger">Remove</button></div></form>`);
}
function expenseForm(expense){
  const v = key => escapeHTML(expense?.[key] ?? '');
  const fields = `<div class="field"><label for="expense-description">What was it for?</label><input id="expense-description" name="description" maxlength="255" autocomplete="off" required placeholder="Coffee, groceries, a ride home" value="${v('description')}"></div>${amountField('expense-amount','amount','Amount',v('amount'))}${categoryChips(expense?.category_id)}<div class="field"><label for="expense-date">When?</label><input id="expense-date" name="expense_date" type="date" value="${expense?.expense_date ?? localDate()}" required></div><details class="more" ${expense?.notes?'open':''}><summary>${icon('plus')}Add a note</summary><div class="field"><label for="expense-notes">Note</label><textarea id="expense-notes" name="notes" maxlength="2000" placeholder="Anything you’d like to remember.">${v('notes')}</textarea></div></details>`;
  if(expense) showSheet('Edit expense','',`<form data-form="expense-update"><input type="hidden" name="expense_id" value="${expense.expense_id}">${fields}${formActions('Save changes')}</form>`);
  else showSheet('Log an expense','Big or small, every entry helps you see the whole picture.',`<form data-form="expense">${fields}${formActions('Save expense')}</form>`);
}
const newExpense = () => expenseForm();
function setBudget(){
  showSheet(`Budget for ${monthTitle()}`,'Pick an amount that feels right. You can change it anytime.',`<form data-form="budget">${amountField('budget-amount','budget_amount','Monthly budget',currentBudget()?.budget_amount??'','0')}<p class="hint">${icon('leaf')}Every expense you log counts toward this.</p>${formActions('Save budget')}</form>`);
}
function review(id){
  const item = database.wishlist_items.find(w => w.wishlist_item_id===id); if(!item) return;
  activeDecision = id; selectedDecision = null;
  const summary = `<div class="sheet-item">${thumb(item)}<div><strong>${escapeHTML(item.item_name)}</strong><span class="money">${currency(item.estimated_price)}</span></div></div>`;
  const notes = item.notes ? `<blockquote class="note">${escapeHTML(item.notes)}</blockquote>` : '';
  const manage = `<div class="manage"><button type="button" class="link" data-action="edit-wish" data-id="${id}">${icon('edit')}Edit details</button><button type="button" class="link link-danger" data-action="remove-wish" data-id="${id}">${icon('trash')}Remove</button></div>`;
  if(!ready(item)){
    showSheet('Still waiting','Your wish is safe. Let the excitement settle first.',`${summary}<div class="wait-panel">${otto('sleeping')}<div class="countdown" data-big-countdown="${id}">${waitText(item)}</div><p>Check-in on ${parseTime(item.wait_until).toLocaleString('en',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}</p>${bar(waitProgress(item),'amber')}</div>${notes}${manage}<div class="sheet-actions">${item.product_url?`<a class="btn btn-soft" href="${escapeHTML(item.product_url)}" target="_blank" rel="noopener noreferrer">${icon('external')}Product link</a>`:''}<button class="btn btn-primary" data-action="close">Let it rest</button></div>`);
    return;
  }
  showSheet('Still a good idea?','The wait is over. There’s no right answer, just the right one for you.',`${summary}${notes}${manage}<form data-form="decision"><p class="prompt">Will it add something to your life? Does it fit your budget? Would you want it if nobody else saw it?</p><div class="choices" role="group" aria-label="Your decision"><button type="button" class="choice choice-buy" data-action="choose-decision" data-value="buy" aria-pressed="false">${icon('bag')}I still want it</button><button type="button" class="choice choice-skip" data-action="choose-decision" data-value="skip" aria-pressed="false">${icon('leaf')}Let it go</button><button type="button" class="choice choice-wait" data-action="choose-decision" data-value="wait_longer" aria-pressed="false">${icon('clock')}More time</button></div><div id="decision-extra"></div><div class="field"><label for="reflection">A thought to remember <i>Optional</i></label><textarea id="reflection" name="reflection" maxlength="2000" placeholder="How do you feel about it now?"></textarea></div><div class="sheet-actions"><button type="button" class="btn btn-soft" data-action="close">Keep thinking</button><button id="decision-submit" type="submit" class="btn btn-primary" disabled>Save my decision</button></div></form>`);
}
function chooseDecision(value){
  selectedDecision = value;
  document.querySelectorAll('.choice').forEach(b => { b.classList.toggle('selected', b.dataset.value===value); b.setAttribute('aria-pressed', String(b.dataset.value===value)); });
  const item = database.wishlist_items.find(w => w.wishlist_item_id===activeDecision);
  document.querySelector('#decision-extra').innerHTML = value==='buy'
    ? `<label class="check"><input type="checkbox" name="record_expense" id="record-expense" checked>I bought it. Log it as an expense.</label><div id="purchase-amount-field">${amountField('purchase-amount','amount','Amount paid',item.estimated_price)}</div>`
    : value==='wait_longer' ? waitOptions()
    : `<p class="hint">${icon('leaf')}Letting go can feel good, too. It stays in your decisions.</p>`;
  document.querySelector('#decision-submit').disabled = false;
}
function decisionResult(kind, item){
  const copy = {
    buy:['celebrate','Otto cheering','Enjoy it.','You waited, thought it through and still wanted it. That’s a good purchase.'],
    skip:['letgo','Otto waving a leaf goodbye','Let go.',`${currency(item.estimated_price)} stays in your pocket. A little less stuff, a little more room.`],
    wait_longer:['sleeping','Otto going back to sleep','More time it is.','No rush. Otto will check in again when the new wait is over.']
  }[kind];
  showSheet(copy[2],'',`<div class="result">${otto(copy[0],copy[1])}<p class="prompt">${copy[3]}</p></div><div class="sheet-actions"><button class="btn btn-primary" data-action="close">Done</button></div>`);
}
function confirmDelete(id){
  const item = database.expenses.find(e => e.expense_id===id); if(!item) return;
  showSheet('Remove this expense?',`${escapeHTML(item.description)} · ${currency(item.amount)}`,`<form data-form="delete"><input type="hidden" name="expense_id" value="${id}"><p class="prompt">It comes off your spending totals. Any wishlist decision stays in your history.</p><div class="sheet-actions"><button type="button" class="btn btn-soft" data-action="close">Keep it</button><button type="submit" class="btn btn-danger">Remove</button></div></form>`);
}
function about(){
  showSheet('Hello from HypeCheck','Want it. Wait. Decide.',`<div class="account"><span class="tile tone-lifestyle">${head('happy')}</span><div><strong>${escapeHTML(database.user?.full_name||'')}</strong><small>${escapeHTML(database.user?.email||'')}</small></div><button class="btn btn-soft" data-action="sign-out">Sign out</button></div><div class="about">${otto('happy')}<p class="prompt">A calm space to pause before a purchase and feel clearer about your spending.</p></div><p class="hint">${icon('info')}Your wishes and spending are private to your account. Amounts are in Philippine pesos.</p><p class="legal-links"><a href="/welcome">About HypeCheck</a> · <a href="/privacy.html">Privacy Policy</a> · <a href="/terms.html">Terms of Service</a></p><div class="sheet-actions"><button class="btn btn-primary" data-action="close">Got it</button></div>`);
}

/* Drag the sheet down by its header to dismiss (phones only). Settling is a CSS
   transition so a release retargets from wherever the finger left it. */
const SWIPE_THRESHOLD = 100, FLICK_VELOCITY = 0.11, HYSTERESIS = 10;
const rubberband = (overshoot, dimension, constant=0.55) => (overshoot*dimension*constant)/(dimension+constant*Math.abs(overshoot));
let drag = null;
sheet.addEventListener('pointerdown', event => {
  if(drag || saving || !SHEET_QUERY.matches || !event.target.closest('.sheet-head') || event.target.closest('button')) return;
  drag = {y:event.clientY, time:performance.now(), id:event.pointerId};
  sheet.style.transition = 'none';
  sheet.setPointerCapture(event.pointerId); // last: keeps tracking when the finger leaves the header
});
sheet.addEventListener('pointermove', event => {
  if(!drag || event.pointerId!==drag.id) return;
  const delta = event.clientY-drag.y;
  sheet.style.transform = `translateY(${delta>0 ? delta : rubberband(delta, sheet.offsetHeight)}px)`;
});
function endDrag(event){
  if(!drag || event.pointerId!==drag.id) return;
  const delta = event.clientY-drag.y, velocity = delta/(performance.now()-drag.time);
  drag = null; sheet.style.transition = ''; sheet.style.transform = '';
  if(event.type==='pointerup' && (delta>=SWIPE_THRESHOLD || (delta>HYSTERESIS && velocity>FLICK_VELOCITY))) sheet.close();
}
sheet.addEventListener('pointerup', endDrag);
sheet.addEventListener('pointercancel', endDrag);

/* ── Feedback ──────────────────────────────────────────────────────────── */
function toast(message){
  const node = document.querySelector('#toast');
  node.innerHTML = head('proud')+escapeHTML(message); node.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove('show'), 4200);
}
function celebrate(){
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const container = document.createElement('div'); container.className='celebration'; container.setAttribute('aria-hidden','true');
  container.innerHTML = Array.from({length:18},(_,i) => `<i style="--x:${36+Math.random()*28}%;--c:${['#2f9e8f','#e0b15a','#9fd3c0'][i%3]};--drift:${Math.random()*200-100}px;animation-delay:${Math.random()*.15}s"></i>`).join('');
  document.body.append(container); setTimeout(() => container.remove(), 1900);
}

/* ── Saving ────────────────────────────────────────────────────────────── */
async function submitForm(event){
  const form = event.target.closest('form[data-form]'); if(!form) return; event.preventDefault(); if(saving) return;
  const data = Object.fromEntries(new FormData(form)); let endpoint, message;
  switch(form.dataset.form){
    case 'login': endpoint='/api/auth/login'; message='Welcome back.'; break;
    case 'register': endpoint='/api/auth/register'; message='Your space is ready.'; break;
    case 'wish': endpoint='/api/wishlist'; data.category_id=Number(data.category_id); data.wait_hours=Number(data.wait_hours); message='Your pause starts now. Otto’s on it.'; break;
    case 'wish-update': endpoint='/api/wishlist/update'; data.wishlist_item_id=Number(data.wishlist_item_id); data.category_id=Number(data.category_id); message='Wish updated. Your wait keeps running.'; break;
    case 'wish-delete': endpoint='/api/wishlist/delete'; data.wishlist_item_id=Number(data.wishlist_item_id); message='Wish removed.'; break;
    case 'expense-update': endpoint='/api/expenses/update'; data.expense_id=Number(data.expense_id); data.category_id=Number(data.category_id); message='Expense updated.'; break;
    case 'expense': endpoint='/api/expenses'; data.category_id=Number(data.category_id); message='Logged. A little more clarity.'; break;
    case 'budget': endpoint='/api/budget'; data.budget_month=month; data.budget_year=year; message='Budget saved.'; break;
    case 'decision': if(!selectedDecision) return; endpoint='/api/decisions'; data.wishlist_item_id=activeDecision; data.decision=selectedDecision; data.expense_date=localDate(); data.record_expense=data.record_expense==='on'; if(data.wait_hours) data.wait_hours=Number(data.wait_hours); message={buy:'A thoughtful choice. Decision saved.',skip:'A little less stuff. A little more breathing room.',wait_longer:'No rush. Your wish has more time.'}[selectedDecision]; break;
    case 'delete': endpoint='/api/expenses/delete'; data.expense_id=Number(data.expense_id); message='Expense removed.'; break;
    default: return;
  }
  const button = form.querySelector('[type="submit"]'), old = button.innerHTML; button.disabled=true; button.textContent='Saving…'; saving=true;
  const error = document.querySelector('.form-error'); error.textContent=''; error.classList.remove('show');
  try{
    const response = await api(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await readJson(response);
    if(response.status===401 && !endpoint.startsWith('/api/auth/')){ showAuth(); return; }  // session ended
    if(!response.ok) throw new Error(response.status>=500 ? 'Something went wrong on our side. Please try again.' : (result.error||'That didn’t save. Please try again.'));
    const decided = form.dataset.form==='decision' ? database.wishlist_items.find(w => w.wishlist_item_id===activeDecision) : null;
    if(!decided){ sheet.close(); saving=false; }  // the lock is for the open form; don't swallow taps in the next sheet while the view reloads
    try { const signedIn = await load(); if(signedIn === false) return; if(decided){ decisionResult(selectedDecision, decided); if(selectedDecision!=='wait_longer') celebrate(); } else toast(message); }
    catch { sheet.close(); main.innerHTML=`<div class="error-message">Your change was saved, but the view couldn’t refresh.</div><button class="btn btn-primary" data-action="retry">Refresh</button>`; }
  }catch(problem){ error.textContent = problem.message||'Couldn’t connect. Please try again.'; error.classList.add('show'); error.scrollIntoView({block:'nearest'});
    load().catch(() => {});  // the save may have landed before the connection died; show what the server actually has
  }
  finally{ saving=false; button.disabled=false; button.innerHTML=old; }
}
function exportExpenses(){
  const safe = value => `"${String(value).replace(/^[=+\-@\t\r]/,"'$&").replace(/"/g,'""')}"`;
  const csv = [['Date','Description','Category','Amount (PHP)'],...currentExpenses().sort(expenseSort).map(e => [e.expense_date,e.description,cat(e.category_id),e.amount])].map(row => row.map(safe).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'})); const link = document.createElement('a');
  link.href=url; link.download=`hypecheck-expenses-${year}-${String(month).padStart(2,'0')}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
  toast('Your monthly expenses, ready to keep.');
}

/* ── Events ────────────────────────────────────────────────────────────── */
document.addEventListener('click', event => {
  const target = event.target.closest('[data-action]'); if(!target) return;
  const action = target.dataset.action, id = Number(target.dataset.id);
  if(saving && sheet.contains(target)) return;
  switch(action){
    case 'add': addMenu(); break;
    case 'new-wish': newWish(); break;
    case 'new-expense': newExpense(); break;
    case 'set-budget': setBudget(); break;
    case 'about': if(database) about(); break;
    case 'sign-out': signOut(); break;
    case 'google': location.href = '/api/auth/google/start?code=' + encodeURIComponent(document.querySelector('#auth-code')?.value || ''); break;
    case 'auth-login': showAuth('login'); break;
    case 'auth-register': showAuth('register'); break;
    case 'close': sheet.close(); break;
    case 'review': review(id); break;
    case 'choose-decision': chooseDecision(target.dataset.value); break;
    case 'delete-expense': confirmDelete(id); break;
    case 'edit-wish': wishForm(database.wishlist_items.find(w => w.wishlist_item_id===id)); break;
    case 'remove-wish': removeWish(id); break;
    case 'edit-expense': expenseForm(database.expenses.find(e => e.expense_id===id)); break;
    case 'filter': filter=target.dataset.value; render(); break;
    case 'wishlist': case 'money': case 'history': navigate(action); break;
    case 'ready': page='wishlist'; filter='ready'; search=''; window.history.replaceState(null,'','#wishlist'); render(); window.scrollTo({top:0,behavior:'instant'}); break;
    case 'month-prev': case 'month-next': { const date = new Date(year, month-1+(action==='month-prev'?-1:1), 1); year=date.getFullYear(); month=date.getMonth()+1; render(); break; }
    case 'export': exportExpenses(); break;
    case 'retry': load().catch(() => toast('Still unable to connect. Check your connection and try again.')); break;
  }
});
document.addEventListener('input', event => {
  if(event.target.id==='wish-search'){ search=event.target.value; document.querySelector('#wish-grid').innerHTML=wishCards(); }
  if(event.target.id==='expense-search'){ search=event.target.value; document.querySelector('#expense-rows').innerHTML=expenseGroups(); }
});
document.addEventListener('change', event => {
  if(event.target.id==='sort'){ sort=event.target.value; document.querySelector('#wish-grid').innerHTML=wishCards(); }
  if(event.target.id==='record-expense'){ const input=document.querySelector('#purchase-amount'); input.required=event.target.checked; input.disabled=!event.target.checked; document.querySelector('#purchase-amount-field').hidden=!event.target.checked; }
});
document.addEventListener('submit', submitForm);
sheet.addEventListener('click', event => { if(event.target===sheet && !saving){ const rect=sheet.getBoundingClientRect(); if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom) sheet.close(); } });
sheet.addEventListener('cancel', event => { if(saving) event.preventDefault(); });
sheet.addEventListener('close', () => { document.querySelector('#sheet-body').innerHTML = ''; });  // nothing left behind to tick or reopen

window.addEventListener('hashchange', () => {
  if(!database) return;
  const key = location.hash.slice(1);
  if(key && !aliases[key] && !links.some(l => l[0]===key)) return;  // #main and other non-routes belong to the page, not the router
  page=routeOf(location.hash); filter='all'; search=''; render(); window.scrollTo({top:0,behavior:'instant'});
});

// a phone left open overnight shows yesterday's data, and actions then fail against the server
let lastRefresh = Date.now();
document.addEventListener('visibilitychange', () => {
  if(document.hidden || !database || sheet.open) return;
  if(Date.now() - lastRefresh < 60000) return;
  lastRefresh = Date.now();
  load().catch(() => {});  // quiet: the view just keeps what it has
});

setInterval(() => {
  if(!database || document.hidden) return;
  let changed = false;
  document.querySelectorAll('[data-countdown]').forEach(el => { const item=database.wishlist_items.find(w => w.wishlist_item_id===Number(el.dataset.countdown)); if(!item) return; const text=waitText(item); if(text==='Ready to decide' && el.textContent!==text) changed=true; el.textContent=text; });
  if(sheet.open) document.querySelectorAll('[data-big-countdown]').forEach(el => { const item=database.wishlist_items.find(w => w.wishlist_item_id===Number(el.dataset.bigCountdown)); if(!item) return; if(ready(item)) review(item.wishlist_item_id); else el.textContent=waitText(item); });
  if(changed) render();
}, 1000);

document.documentElement.classList.add('fresh'); setTimeout(() => document.documentElement.classList.remove('fresh'), 1500);
decorate();
document.querySelector('#rail-otto').outerHTML = otto('sleeping','Otto taking a peaceful nap');
page = routeOf(location.hash);
load().catch(error => { main.innerHTML=`<div class="error-message">${escapeHTML(error.message)}</div><button class="btn btn-primary" data-action="retry">Try again</button>`; });
