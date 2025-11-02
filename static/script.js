// === CARRUSEL DE IMÁGENES ===
let index = 0;
const slides = document.querySelectorAll('.slide');

function showSlide(n) {
  slides.forEach((slide, i) => slide.classList.toggle('active', i === n));
}

function nextSlide() {
  if (slides.length > 0) {
    index = (index + 1) % slides.length;
    showSlide(index);
  }
}

setInterval(nextSlide, 4000);


// === ANIMACIÓN DEL CARRITO ===
document.addEventListener("DOMContentLoaded", () => {
  const cartIcon = document.querySelector(".fa-cart-shopping");
  const flashes = document.querySelectorAll(".flash-info, .flash-success");

  if (flashes.length && cartIcon) {
    cartIcon.classList.add("bounce");
    setTimeout(() => cartIcon.classList.remove("bounce"), 700);
  }
});
// static/js/script.js

document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.querySelector('.menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // === ANIMACIONES DE SCROLL ===
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Opcional: animar los elementos hijos
                const cards = entry.target.querySelectorAll('.benefit-card');
                cards.forEach(card => {
                    card.style.animation = card.style.animation.replace('none', '');
                });
            }
        });
    }, observerOptions);

    // Observar todas las secciones
    document.querySelectorAll('.about-section').forEach(section => {
        observer.observe(section);
    });
});
