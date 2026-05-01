/* Header interactions:
 *  - sticky scroll class (.is-scrolled)
 *  - mobile nav drawer with iOS body-scroll-lock
 *  - desktop dropdown keyboard navigation
 *  - mobile submenu accordions
 *  - search button event
 */
(() => {
  "use strict";

  // ── Sticky header ──────────────────────────────────────────────────────────
  const header = document.querySelector("[data-sticky-header]");
  if (header) {
    const THRESHOLD = 8;
    const onScroll = () =>
      header.classList.toggle("is-scrolled", window.scrollY > THRESHOLD);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ── Mobile nav ─────────────────────────────────────────────────────────────
  const toggleBtn = document.querySelector("[data-action='toggle-nav']");
  const mobileNav = document.getElementById("mobile-nav");

  let savedScrollY = 0;

  function openNav() {
    savedScrollY = window.scrollY;
    toggleBtn.setAttribute("aria-expanded", "true");
    mobileNav.removeAttribute("hidden");
    // iOS Safari: position:fixed + top stop scroll-through
    document.body.style.top = `-${savedScrollY}px`;
    document.body.classList.add("nav-open");
    // Перший елемент меню отримує фокус для доступності
    const firstLink = mobileNav.querySelector("a, button");
    if (firstLink) firstLink.focus();
  }

  function closeNav() {
    toggleBtn.setAttribute("aria-expanded", "false");
    mobileNav.setAttribute("hidden", "");
    document.body.classList.remove("nav-open");
    document.body.style.top = "";
    // Відновлюємо позицію скролу після position:fixed
    window.scrollTo({ top: savedScrollY, behavior: "instant" });
    toggleBtn.focus();
  }

  if (toggleBtn && mobileNav) {
    toggleBtn.addEventListener("click", () => {
      const isOpen = toggleBtn.getAttribute("aria-expanded") === "true";
      isOpen ? closeNav() : openNav();
    });

    // Закрити при кліку на посилання
    mobileNav.addEventListener("click", (e) => {
      if (e.target.closest("a")) closeNav();
    });

    // Закрити при Escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toggleBtn.getAttribute("aria-expanded") === "true") {
        closeNav();
      }
    });
  }

  // Dropdown прибрано — проста плоска навігація

  // ── Search button ──────────────────────────────────────────────────────────
  const searchBtn = document.querySelector("[data-action='open-search']");
  if (searchBtn) {
    searchBtn.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("fpu:open-search"));
      // Якщо є форма пошуку на сторінці — перейти до неї
      const searchInput = document.querySelector(".search-form__input");
      if (searchInput) {
        searchInput.focus();
        searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        window.location.href = "/search/";
      }
    });
  }
})();
