export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

export function button(text, className = "button") {
  const node = element("button", className, text);
  node.type = "button";
  return node;
}

export function clear(node) {
  node.replaceChildren();
  return node;
}

export function formatDate(value) {
  if (!value) return "No activity";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function skeleton(lines = 4) {
  const card = element("div", "skeleton");
  card.setAttribute("aria-label", "Loading");
  card.setAttribute("aria-busy", "true");
  for (let index = 0; index < lines; index += 1) {
    const line = element("div", index === lines - 1 ? "skeleton__line skeleton__line--short" : "skeleton__line");
    card.append(line);
  }
  return card;
}

export function loading(root, lines = 4) {
  clear(root).append(skeleton(lines));
}

export function emptyState(message) {
  const state = element("section", "empty-state");
  state.append(element("p", "", message));
  return state;
}

export function errorState(error) {
  const state = element("section", "error-state");
  state.setAttribute("role", "alert");
  state.append(element("p", "", error && error.message ? error.message : "Unable to load this view."));
  return state;
}

export function pulse(root) {
  root.classList.remove("is-pulsing");
  requestAnimationFrame(() => {
    root.classList.add("is-pulsing");
    window.setTimeout(() => root.classList.remove("is-pulsing"), 750);
  });
}

export function focusTrap(container, event) {
  if (event.key !== "Tab") return;
  const focusable = [...container.querySelectorAll("button, [href], input, select, [tabindex]:not([tabindex='-1'])")]
    .filter((node) => !node.disabled);
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
