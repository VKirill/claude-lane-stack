import { projectHash } from "../router.js";
import { getProjectName, getProjects, loadReviews } from "../store.js";
import { element, emptyState, errorState, loading } from "../ui.js";
import { badge } from "../components/badges.js";

function projectName(projectId) {
  return getProjectName(getProjects().find((project) => String(project.id ?? project.projectId ?? project.slug ?? project.name) === projectId));
}

function tabs(projectId) {
  const nav = element("nav", "view-tabs");
  nav.setAttribute("aria-label", "Project views");
  [["board", "Board"], ["todos", "Todos"], ["runs", "Runs"], ["reviews", "Reviews"]].forEach(([section, label]) => {
    const link = element("a", `view-tabs__link${section === "reviews" ? " view-tabs__link--active" : ""}`, label);
    link.href = projectHash(projectId, section);
    if (section === "reviews") link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  return nav;
}

function verdictLabel(v) {
  if (v && typeof v === "object") {
    return v.scope ? `${v.scope}: ${v.verdict || ""}` : (v.verdict || "");
  }
  return String(v || "");
}

function verdictValue(v) {
  return (v && typeof v === "object") ? (v.verdict || "") : String(v || "");
}

function asList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return value.split("\n").filter(Boolean);
  return [];
}

function priorityOf(finding) {
  const value = String(typeof finding === "string" ? finding : finding && (finding.level ?? finding.priority) || "").toUpperCase();
  return value.match(/\bP[01]\b/)?.[0] || value;
}

function findingText(finding) {
  return typeof finding === "string" ? finding : finding && (finding.title || finding.text || finding.message) || "Finding";
}

function reviewCard(review) {
  const card = element("article", "review-card");
  const header = element("div", "review-card__meta");
  header.append(element("h2", "", review.date || "Undated review"));
  asList(review.verdicts).forEach((verdict) => {
    header.append(badge(verdictLabel(verdict), /fail|blocked/i.test(verdictValue(verdict)) ? "blocked" : "neutral"));
  });
  card.append(header);
  const important = asList(review.findings).filter((finding) => ["P0", "P1"].includes(priorityOf(finding)));
  if (important.length > 0) {
    const section = element("section", "review-card__section");
    section.append(element("h3", "", "P0 / P1 findings"));
    const list = element("ul", "");
    important.forEach((finding) => list.append(element("li", "", findingText(finding))));
    section.append(list);
    card.append(section);
  }
  const plan = asList(review.fixPlan);
  if (plan.length > 0) {
    const section = element("section", "review-card__section");
    section.append(element("h3", "", "Morning fix plan"));
    const list = element("ul", "");
    plan.forEach((line) => list.append(element("li", "", line)));
    section.append(list);
    card.append(section);
  }
  return card;
}

export async function renderReviews({ root, route, isCurrent }) {
  loading(root, 5);
  try {
    const reviews = await loadReviews(route.projectId);
    if (!isCurrent()) return;
    const page = document.createDocumentFragment();
    const header = element("header", "page-header");
    const heading = element("div", "");
    heading.append(element("h1", "", "Review history"), element("p", "", `${projectName(route.projectId)} · newest review first.`));
    header.append(heading, tabs(route.projectId));
    page.append(header);
    const list = element("section", "review-list");
    const ordered = [...reviews].sort((left, right) => String(right.date || "").localeCompare(String(left.date || "")));
    if (ordered.length === 0) list.append(emptyState("No night reviews have been recorded for this project."));
    ordered.forEach((review) => list.append(reviewCard(review || {})));
    page.append(list);
    root.replaceChildren(page);
  } catch (error) {
    if (isCurrent()) root.replaceChildren(errorState(error));
  }
}
