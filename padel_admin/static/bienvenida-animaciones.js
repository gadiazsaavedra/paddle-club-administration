// Contador animado
function animateCounter(id, end, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  let start = 0;
  const step = Math.ceil(end / (duration / 16));
  function update() {
    start += step;
    if (start >= end) {
      el.textContent = end;
    } else {
      el.textContent = start;
      requestAnimationFrame(update);
    }
  }
  update();
}

document.addEventListener('DOMContentLoaded', function() {
  animateCounter('counter-socios', 350, 1200);
  animateCounter('counter-partidos', 1200, 1200);
  animateCounter('counter-torneos', 48, 1200);
});

// Slider simple para testimonios y galería
function simpleSlider(containerSelector, interval=4000) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  const slides = container.querySelectorAll('.slide');
  let idx = 0;
  function showSlide(i) {
    slides.forEach((s, j) => s.style.display = (i === j ? 'block' : 'none'));
  }
  function next() {
    idx = (idx + 1) % slides.length;
    showSlide(idx);
  }
  showSlide(idx);
  setInterval(next, interval);
}
document.addEventListener('DOMContentLoaded', function() {
  simpleSlider('.testimonios-slider', 6000);
  simpleSlider('.gallery-slider', 3500);
});

// Lightbox para galería
function openLightbox(src) {
  let lb = document.getElementById('lightbox-modal');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'lightbox-modal';
    lb.style.position = 'fixed';
    lb.style.top = 0;
    lb.style.left = 0;
    lb.style.width = '100vw';
    lb.style.height = '100vh';
    lb.style.background = 'rgba(0,0,0,0.8)';
    lb.style.display = 'flex';
    lb.style.alignItems = 'center';
    lb.style.justifyContent = 'center';
    lb.style.zIndex = 9999;
    lb.onclick = () => lb.remove();
    document.body.appendChild(lb);
  }
  lb.innerHTML = `<img src="${src}" style="max-width:90vw;max-height:80vh;border-radius:16px;box-shadow:0 8px 32px #0008;">`;
  lb.style.display = 'flex';
}
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.gallery-slider img').forEach(img => {
    img.style.cursor = 'zoom-in';
    img.onclick = () => openLightbox(img.src);
  });
});
