/**
 * SMM Panel — tương tác giao diện Gentelella (bản rút gọn, tự viết).
 *
 * Cố ý KHÔNG dùng file main-v4.js gốc của Gentelella: bản gốc gắn một
 * listener toàn cục lên mọi <form> để giả lập submit (preventDefault + toast
 * + reset) phục vụ mục đích demo tĩnh. Điều đó sẽ chặn đứng mọi form thật
 * (login, tạo user, ...) gửi lên FastAPI backend. File này chỉ implement lại
 * đúng phần UI thuần túy: toggle sidebar, accordion menu, dark mode, dropdown.
 */
(function () {
  "use strict";

  var RAIL_KEY = "smm:sidebar-rail";
  var THEME_KEY = "theme";

  function isDesktop() {
    return window.matchMedia("(min-width: 769px)").matches;
  }

  function initSidebarToggle() {
    var sidebar = document.querySelector(".sidebar");
    var toggle = document.querySelector(".sidebar-toggle");
    if (!sidebar || !toggle) return;

    var backdrop = document.querySelector(".sidebar-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      backdrop.hidden = true;
      document.body.appendChild(backdrop);
    }

    function drawerClose() {
      sidebar.classList.remove("open");
      backdrop.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      document.body.classList.remove("sidebar-open");
    }

    function drawerOpen() {
      sidebar.classList.add("open");
      backdrop.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      document.body.classList.add("sidebar-open");
    }

    function setRail(on) {
      document.body.classList.toggle("sidebar-rail", on);
      toggle.setAttribute("aria-pressed", on ? "true" : "false");
      try {
        localStorage.setItem(RAIL_KEY, on ? "1" : "0");
      } catch (e) {
        /* private mode */
      }
    }

    var stored = "0";
    try {
      stored = localStorage.getItem(RAIL_KEY) || "0";
    } catch (e) {
      /* ignore */
    }
    if (stored === "1" && isDesktop()) setRail(true);

    toggle.addEventListener("click", function () {
      if (isDesktop()) {
        setRail(!document.body.classList.contains("sidebar-rail"));
      } else {
        sidebar.classList.contains("open") ? drawerClose() : drawerOpen();
      }
    });
    backdrop.addEventListener("click", drawerClose);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("open")) drawerClose();
    });
  }

  function initNavAccordion() {
    var trees = Array.prototype.slice.call(document.querySelectorAll(".sidebar .nav-tree"));
    if (!trees.length) return;

    function closeAll(except) {
      trees.forEach(function (t) {
        if (t === except) return;
        t.classList.remove("open");
        var btn = t.querySelector(".nav-toggle");
        if (btn) btn.setAttribute("aria-expanded", "false");
      });
    }

    trees.forEach(function (tree) {
      var btn = tree.querySelector(".nav-toggle");
      if (!btn) return;
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var willOpen = !tree.classList.contains("open");
        closeAll(willOpen ? tree : null);
        tree.classList.toggle("open", willOpen);
        btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      });
    });
  }

  function initThemeToggle() {
    var btn = document.querySelector(".theme-toggle");
    if (!btn) return;

    function apply(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }

    var current = document.documentElement.getAttribute("data-theme") || "light";
    btn.setAttribute("aria-pressed", current === "dark" ? "true" : "false");

    btn.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (e) {
        /* private mode */
      }
      apply(next);
    });
  }

  function initDropdowns() {
    // Bất kỳ [data-dropdown-toggle] nào điều khiển phần tử [data-dropdown-menu]
    // liền kề. Đóng khi click ra ngoài hoặc nhấn Escape.
    document.addEventListener("click", function (e) {
      var toggle = e.target.closest("[data-dropdown-toggle]");
      document.querySelectorAll("[data-dropdown-menu].open").forEach(function (menu) {
        if (toggle && menu.previousElementSibling === toggle) return;
        if (toggle && menu === toggle.nextElementSibling) return;
        menu.classList.remove("open");
      });
      if (toggle) {
        var menu = toggle.nextElementSibling;
        if (menu && menu.hasAttribute("data-dropdown-menu")) {
          menu.classList.toggle("open");
        }
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        document.querySelectorAll("[data-dropdown-menu].open").forEach(function (m) {
          m.classList.remove("open");
        });
      }
    });
  }

  function preapplyTheme() {
    try {
      var stored = localStorage.getItem(THEME_KEY);
      var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      var theme = stored || (prefersDark ? "dark" : "light");
      document.documentElement.setAttribute("data-theme", theme);
    } catch (e) {
      /* ignore */
    }
  }

  preapplyTheme();

  document.addEventListener("DOMContentLoaded", function () {
    initSidebarToggle();
    initNavAccordion();
    initThemeToggle();
    initDropdowns();
  });
})();
