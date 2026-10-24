'use strict';
// Landing page motion. Everything is an enhancement: with no JavaScript the page is fully visible and static.
document.documentElement.classList.add('js');
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;

// Reveal each block once as it scrolls in. Never re-hide: re-animating on every pass fights the reader.
const revealer = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('in'); observer.unobserve(entry.target); } });
}, { rootMargin: '0px 0px -6% 0px', threshold: 0.05 });  // low bar: a tall block near the page end must still be able to cross it
document.querySelectorAll('.reveal').forEach(node => revealer.observe(node));

// "Do the math": count up once, ease-out, when the number is on screen.
const peso = value => '₱' + Math.round(value).toLocaleString('en-PH');
const COUNT_MS = 1400;
const counter = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    observer.unobserve(entry.target);
    const target = Number(entry.target.dataset.count);
    if (calm) { entry.target.textContent = peso(target); return; }
    const start = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - start) / COUNT_MS);
      entry.target.textContent = peso(target * (1 - Math.pow(1 - t, 4)));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}, { threshold: 0.6 });
document.querySelectorAll('[data-count]').forEach(node => counter.observe(node));

// The little timer card in the hero really counts down, the way a wish does in the app.
const timer = document.querySelector('[data-demo-timer]'), bar = document.querySelector('[data-demo-bar]');
if (timer) {
  const TOTAL = 72 * 3600, begin = Date.now();
  let left = 47 * 3600 + 59 * 60 + 59;
  const paint = () => {
    const d = Math.floor(left / 86400), h = Math.floor(left % 86400 / 3600), m = Math.floor(left % 3600 / 60), s = left % 60;
    timer.textContent = `${d}d ${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s left`;
    if (bar) bar.style.width = ((1 - left / TOTAL) * 100).toFixed(2) + '%';
  };
  paint();
  if (!calm) setInterval(() => { left = Math.max(0, 47 * 3600 + 59 * 60 + 59 - Math.floor((Date.now() - begin) / 1000)); paint(); }, 1000);
}

// Hero loop: a still poster for people who asked for less motion; otherwise play only while it is on screen.
const video = document.querySelector('.l-video');
if (video) {
  if (calm) { video.removeAttribute('autoplay'); video.pause(); }
  else new IntersectionObserver(entries => entries.forEach(entry => { entry.isIntersecting ? video.play().catch(() => {}) : video.pause(); }), { threshold: 0.15 }).observe(video);
}

// Keep signup usable without Google credentials (including the offline school presentation).
fetch('/api/auth/options').then(response => response.ok ? response.json() : {}).then(options => {
  const link = document.querySelector('.l-google');
  if (!link) return;
  if (options.google && options.google_open) {
    link.href = '/api/auth/google/start';
    link.textContent = 'Start free with Google';
  } else if (options.signup === false) {
    link.href = '/login';
    link.textContent = 'Sign in';
  }
}).catch(() => {}); // the plain signup link still works if this request fails
