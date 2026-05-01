/* Vanilla JS lightbox:
 *  - відкривається при кліку на .photo-grid__link[data-lightbox]
 *  - навігація: кнопки ‹ ›, стрілки ← →, Escape для закриття
 *  - touch swipe (iOS-сумісний)
 *  - lazy preload: наступне + попереднє зображення
 *  - ARIA: role=dialog, aria-modal, focus trap
 */
(() => {
  "use strict";

  const lb = document.getElementById("lightbox");
  const overlay = document.getElementById("lightbox-overlay");
  const lbImg = document.getElementById("lb-img");
  const lbCaption = document.getElementById("lb-caption");
  const lbCounter = document.getElementById("lb-counter");
  const btnClose = document.getElementById("lb-close");
  const btnPrev = document.getElementById("lb-prev");
  const btnNext = document.getElementById("lb-next");

  if (!lb || !overlay) return;

  // Збираємо всі посилання поточного альбому
  const links = Array.from(document.querySelectorAll(".photo-grid__link[data-lightbox]"));
  if (!links.length) return;

  let currentIndex = 0;
  let touchStartX = 0;
  let touchStartY = 0;
  const preloadCache = new Set();

  // ── Preload ───────────────────────────────────────────────────────────────
  function preload(idx) {
    if (idx < 0 || idx >= links.length) return;
    const src = links[idx].getAttribute("href");
    if (!src || preloadCache.has(src)) return;
    preloadCache.add(src);
    const img = new Image();
    img.src = src;
  }

  // ── Show ──────────────────────────────────────────────────────────────────
  function show(idx) {
    currentIndex = Math.max(0, Math.min(idx, links.length - 1));
    const link = links[currentIndex];
    const src = link.getAttribute("href");
    const caption = link.dataset.caption || "";

    lbImg.classList.add("is-loading");
    lbImg.src = src;
    lbImg.alt = caption;
    lbCaption.textContent = caption;
    lbCounter.textContent = `${currentIndex + 1} / ${links.length}`;

    lbImg.onload = () => lbImg.classList.remove("is-loading");
    lbImg.onerror = () => lbImg.classList.remove("is-loading");

    // Preload сусідніх
    preload(currentIndex - 1);
    preload(currentIndex + 1);

    // Вимикаємо кнопки на краях
    btnPrev.disabled = currentIndex === 0;
    btnNext.disabled = currentIndex === links.length - 1;
  }

  // ── Open ──────────────────────────────────────────────────────────────────
  function open(idx) {
    show(idx);
    lb.removeAttribute("hidden");
    overlay.removeAttribute("hidden");
    document.body.classList.add("lightbox-open");
    document.body.style.overflow = "hidden";
    btnClose.focus();

    // Забороняємо scroll-through на iOS
    overlay.addEventListener("touchmove", preventScroll, { passive: false });
  }

  function preventScroll(e) {
    e.preventDefault();
  }

  // ── Close ─────────────────────────────────────────────────────────────────
  function close() {
    lb.setAttribute("hidden", "");
    overlay.setAttribute("hidden", "");
    document.body.classList.remove("lightbox-open");
    document.body.style.overflow = "";
    overlay.removeEventListener("touchmove", preventScroll);

    // Повертаємо фокус на відкриту картинку
    const trigger = links[currentIndex];
    if (trigger) trigger.focus();
  }

  // ── Event listeners ───────────────────────────────────────────────────────
  links.forEach((link, idx) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      open(idx);
    });
    link.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open(idx);
      }
    });
  });

  btnClose.addEventListener("click", close);
  overlay.addEventListener("click", close);

  btnPrev.addEventListener("click", (e) => {
    e.stopPropagation();
    if (currentIndex > 0) show(currentIndex - 1);
  });

  btnNext.addEventListener("click", (e) => {
    e.stopPropagation();
    if (currentIndex < links.length - 1) show(currentIndex + 1);
  });

  // ── Keyboard ──────────────────────────────────────────────────────────────
  document.addEventListener("keydown", (e) => {
    if (lb.hasAttribute("hidden")) return;
    switch (e.key) {
      case "ArrowLeft":
        if (currentIndex > 0) show(currentIndex - 1);
        break;
      case "ArrowRight":
        if (currentIndex < links.length - 1) show(currentIndex + 1);
        break;
      case "Escape":
        close();
        break;
    }
  });

  // ── Focus trap ────────────────────────────────────────────────────────────
  lb.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    const focusable = Array.from(lb.querySelectorAll("button:not([disabled]), [href], [tabindex]:not([tabindex='-1'])"));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) { e.preventDefault(); last.focus(); }
    } else {
      if (document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // ── Touch swipe (iOS Safari) ──────────────────────────────────────────────
  lb.addEventListener("touchstart", (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
  }, { passive: true });

  lb.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].screenX - touchStartX;
    const dy = e.changedTouches[0].screenY - touchStartY;

    // Горизонтальний swipe (мінімум 50px, горизонтальніший за вертикальний)
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0 && currentIndex < links.length - 1) show(currentIndex + 1);
      if (dx > 0 && currentIndex > 0) show(currentIndex - 1);
    }
    // Swipe вниз → закрити
    if (dy > 100 && Math.abs(dy) > Math.abs(dx)) {
      close();
    }
  }, { passive: true });
})();
