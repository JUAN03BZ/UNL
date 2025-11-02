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
