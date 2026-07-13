function decode(part) {
  try {
    return decodeURIComponent(part);
  } catch {
    return "";
  }
}

export function parseRoute(hash = location.hash) {
  const source = hash.replace(/^#/, "") || "/";
  const parts = source.split("/").filter(Boolean).map(decode);
  if (parts.length === 0) return { name: "overview" };
  if (parts[0] !== "p" || !parts[1]) return { name: "overview" };
  const projectId = parts[1];
  const section = parts[2] || "board";
  if (section === "todos") return { name: "todos", projectId };
  if (section === "runs") return { name: "runs", projectId };
  if (section === "reviews") return { name: "reviews", projectId };
  return { name: "board", projectId };
}

export function projectHash(projectId, section = "board") {
  const project = encodeURIComponent(String(projectId));
  if (section === "todos") return `#/p/${project}/todos`;
  if (section === "runs") return `#/p/${project}/runs`;
  if (section === "reviews") return `#/p/${project}/reviews`;
  return `#/p/${project}`;
}

export function goTo(hash) {
  if (location.hash === hash) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    return;
  }
  location.hash = hash;
}

export function routeLabel(route) {
  if (route.name === "overview") return "Portfolio overview";
  if (route.name === "todos") return "Todos";
  if (route.name === "runs") return "Runs";
  if (route.name === "reviews") return "Reviews";
  return "Board";
}
