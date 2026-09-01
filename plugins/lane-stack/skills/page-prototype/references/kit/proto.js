/* page-prototype kit. data-proto-* only. No Vue, no CDN. */
(function () {
  function on(el, ev, fn) {
    el.addEventListener(ev, fn);
  }

  function tabs(root) {
    var tabs = root.querySelectorAll('[role="tab"]');
    var panels = root.querySelectorAll('[role="tabpanel"]');
    tabs.forEach(function (tab, i) {
      on(tab, "click", function () {
        tabs.forEach(function (t, j) {
          t.setAttribute("aria-selected", j === i ? "true" : "false");
        });
        panels.forEach(function (p, j) {
          p.classList.toggle("is-on", j === i);
        });
      });
    });
  }

  function accordion(root) {
    root.querySelectorAll(".proto-acc-item").forEach(function (item) {
      var btn = item.querySelector("button");
      if (!btn) return;
      on(btn, "click", function () {
        var open = item.classList.contains("is-on");
        if (!root.hasAttribute("data-proto-many")) {
          root.querySelectorAll(".proto-acc-item").forEach(function (x) {
            x.classList.remove("is-on");
          });
        }
        item.classList.toggle("is-on", !open);
      });
    });
  }

  function slider(root) {
    var track = root.querySelector(".proto-slider-track");
    if (!track) return;
    var slides = Array.prototype.slice.call(track.children);
    var i = 0;
    var dots = root.querySelector(".proto-dots");
    function go(n) {
      i = (n + slides.length) % slides.length;
      track.style.transform = "translateX(" + -i * 100 + "%)";
      if (dots) {
        dots.querySelectorAll("button").forEach(function (d, j) {
          d.classList.toggle("is-on", j === i);
        });
      }
    }
    if (dots && !dots.children.length) {
      slides.forEach(function (_, j) {
        var b = document.createElement("button");
        b.type = "button";
        b.setAttribute("aria-label", "slide " + (j + 1));
        if (j === 0) b.className = "is-on";
        on(b, "click", function () { go(j); });
        dots.appendChild(b);
      });
    }
    var prev = root.querySelector("[data-proto-prev]");
    var next = root.querySelector("[data-proto-next]");
    if (prev) on(prev, "click", function () { go(i - 1); });
    if (next) on(next, "click", function () { go(i + 1); });
    go(0);
  }

  function toggle(root) {
    var btn = root.querySelector("[data-proto-toggle]");
    if (!btn) return;
    on(btn, "click", function () {
      root.classList.toggle("is-on");
      btn.setAttribute("aria-expanded", root.classList.contains("is-on") ? "true" : "false");
    });
  }

  function modal(root) {
    var id = root.id;
    document.querySelectorAll('[data-proto-open="' + id + '"]').forEach(function (btn) {
      on(btn, "click", function (e) {
        e.preventDefault();
        root.classList.add("is-on");
      });
    });
    root.querySelectorAll("[data-proto-close]").forEach(function (btn) {
      on(btn, "click", function () { root.classList.remove("is-on"); });
    });
    on(root, "click", function (e) {
      if (e.target === root) root.classList.remove("is-on");
    });
  }

  function menu(btn) {
    var sel = btn.getAttribute("data-proto-menu-btn");
    var nav = document.querySelector(sel);
    if (!nav) return;
    on(btn, "click", function () {
      nav.classList.toggle("is-on");
    });
  }

  document.querySelectorAll("[data-proto-tabs]").forEach(tabs);
  document.querySelectorAll("[data-proto-acc]").forEach(accordion);
  document.querySelectorAll("[data-proto-slider]").forEach(slider);
  document.querySelectorAll("[data-proto-toggle]").forEach(function (btn) {
    var root = btn.closest(".proto-toggle") || btn.parentElement;
    if (root && !root._protoToggle) {
      root._protoToggle = true;
      toggle(root);
    }
  });
  document.querySelectorAll(".proto-modal").forEach(modal);
  document.querySelectorAll("[data-proto-menu-btn]").forEach(menu);
})();
