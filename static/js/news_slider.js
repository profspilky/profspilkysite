/* News Slider — автопрокрутка, клавіатура, touch, reduced-motion.
 * Runs on DOMContentLoaded; no external dependencies.
 */

(function () {
  "use strict";

  const AUTOPLAY_MS = 5000;
  const TRANSITION_MS = 540;

  function initSlider(root) {
    const track = root.querySelector("[data-slider-track]");
    const slides = Array.from(root.querySelectorAll("[data-slider-slide]"));
    const dots = Array.from(root.querySelectorAll("[data-slider-dot]"));
    const btnPrev = root.querySelector("[data-slider-prev]");
    const btnNext = root.querySelector("[data-slider-next]");
    const progress = root.querySelector("[data-slider-progress]");

    if (!track || slides.length < 2) return;

    const count = slides.length;
    let current = 0;
    let autoTimer = null;
    let progTimer = null;
    let isTransitioning = false;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* Set CSS variable for track width calculation */
    track.style.setProperty("--slider-count", count);
    root.style.setProperty("--slider-count", count);

    /* ── Core: go to slide N ─────────────────────────────────────────── */
    function goTo(idx, direction) {
      if (isTransitioning) return;
      isTransitioning = true;

      const prev = current;
      current = (idx + count) % count;

      /* Move track */
      track.style.transform = `translateX(calc(-${current} * (100% / ${count})))`;

      /* Update dots */
      dots.forEach((d, i) => {
        const active = i === current;
        d.classList.toggle("news-slider__dot--active", active);
        d.setAttribute("aria-selected", active ? "true" : "false");
      });

      /* Update slide aria-hidden */
      slides.forEach((s, i) => {
        s.setAttribute("aria-hidden", i !== current ? "true" : "false");
        /* Prevent tab into hidden slides */
        const focusables = s.querySelectorAll("a, button");
        focusables.forEach((el) => {
          el.setAttribute("tabindex", i !== current ? "-1" : "0");
        });
      });

      /* Announce to screen reader */
      const liveEl = root.querySelector("[data-slider-live]");
      if (liveEl) {
        liveEl.textContent = `Новина ${current + 1} з ${count}`;
      }

      setTimeout(() => {
        isTransitioning = false;
      }, TRANSITION_MS);
    }

    /* ── Progress bar animation ─────────────────────────────────────── */
    function startProgress() {
      if (reduced || !progress) return;
      clearTimeout(progTimer);
      progress.style.transition = "none";
      progress.style.transform = "scaleX(0)";

      /* Force reflow so the reset is applied before new transition */
      void progress.offsetWidth;

      progress.style.transition = `transform ${AUTOPLAY_MS}ms linear`;
      progress.style.transform = "scaleX(1)";
    }

    function stopProgress() {
      if (!progress) return;
      progress.style.transition = "none";
      progress.style.transform = "scaleX(0)";
    }

    /* ── Autoplay ────────────────────────────────────────────────────── */
    function startAuto() {
      if (reduced) return;
      stopAuto();
      startProgress();
      autoTimer = setTimeout(() => {
        goTo(current + 1);
        startAuto();
      }, AUTOPLAY_MS);
    }

    function stopAuto() {
      clearTimeout(autoTimer);
      clearTimeout(progTimer);
      stopProgress();
      autoTimer = null;
    }

    /* ── Button handlers ─────────────────────────────────────────────── */
    btnPrev?.addEventListener("click", () => {
      stopAuto();
      goTo(current - 1);
      startAuto();
    });

    btnNext?.addEventListener("click", () => {
      stopAuto();
      goTo(current + 1);
      startAuto();
    });

    /* ── Dot handlers ────────────────────────────────────────────────── */
    dots.forEach((dot, i) => {
      dot.addEventListener("click", () => {
        if (i === current) return;
        stopAuto();
        goTo(i);
        startAuto();
      });
    });

    /* ── Keyboard navigation ─────────────────────────────────────────── */
    root.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        stopAuto();
        goTo(current - 1);
        startAuto();
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        stopAuto();
        goTo(current + 1);
        startAuto();
      }
    });

    /* ── Pause on hover / focus ──────────────────────────────────────── */
    root.addEventListener("mouseenter", stopAuto);
    root.addEventListener("mouseleave", startAuto);
    root.addEventListener("focusin", stopAuto);
    root.addEventListener("focusout", (e) => {
      if (!root.contains(e.relatedTarget)) startAuto();
    });

    /* ── Touch / swipe ───────────────────────────────────────────────── */
    let touchStartX = 0;
    let touchStartY = 0;
    let isSwiping = false;

    root.addEventListener(
      "touchstart",
      (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        isSwiping = false;
        stopAuto();
      },
      { passive: true }
    );

    root.addEventListener(
      "touchmove",
      (e) => {
        if (!isSwiping) {
          const dx = Math.abs(e.touches[0].clientX - touchStartX);
          const dy = Math.abs(e.touches[0].clientY - touchStartY);
          /* Only treat as swipe if predominantly horizontal */
          if (dx > dy && dx > 8) {
            isSwiping = true;
          }
        }
      },
      { passive: true }
    );

    root.addEventListener(
      "touchend",
      (e) => {
        if (!isSwiping) {
          startAuto();
          return;
        }
        const dx = e.changedTouches[0].clientX - touchStartX;
        if (Math.abs(dx) > 40) {
          goTo(dx < 0 ? current + 1 : current - 1);
        }
        startAuto();
        isSwiping = false;
      },
      { passive: true }
    );

    /* ── Init ────────────────────────────────────────────────────────── */
    goTo(0);
    startAuto();
  }

  /* ── Boot ────────────────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-news-slider]").forEach(initSlider);
  });
})();
