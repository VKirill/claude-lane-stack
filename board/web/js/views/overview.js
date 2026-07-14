import { projectHash } from "../router.js";
import { getProjectId, getProjectName, getProjects, loadProject, loadProjects, loadReviews, taskStatus, tasksFrom, todoStatus, todosFrom } from "../store.js";
import { element, errorState, formatDate, loading } from "../ui.js";
import { badge, statusBadge } from "../components/badges.js";

function details(payload) {
  return payload && payload.project && typeof payload.project === "object" ? { ...payload, ...payload.project } : payload || {};
}

function statusCount(tasks, status) {
  return tasks.filter((task) => taskStatus(task) === status).length;
}

function openTodoCount(todos) {
  return todos.filter((todo) => !["done", "closed", "resolved"].includes(todoStatus(todo))).length;
}

function newestActivity(runs) {
  return runs.map((run) => run && run.lastActivity).filter(Boolean).sort().at(-1) || "";
}

function reviewVerdicts(review) {
  const verdicts = review && review.verdicts;
  return Array.isArray(verdicts) ? verdicts : verdicts ? [verdicts] : [];
}

function hasFailedReview(reviews) {
  return reviews.some((review) => reviewVerdicts(review).some((verdict) => /fail|blocked/i.test(String(verdict))));
}

function isP0(finding) {
  const str = typeof finding === "string" ? finding : `${finding && (finding.level ?? finding.priority) || ""} ${finding && (finding.text ?? finding.title) || ""}`;
  return /(^|\b)P[01]\b/i.test(str);
}

function attentionStrip(items) {
  const strip = element("section", `attention-strip${items.length ? "" : " attention-strip--quiet"}`);
  const header = element("div", "attention-strip__header");
  header.append(element("h2", "", "Needs attention"), badge(String(items.length), items.length ? "blocked" : "neutral"));
  strip.append(header);
  if (items.length === 0) {
    strip.append(element("p", "", "No blocked tasks, failed verdicts, or P0 findings in recent work."));
    return strip;
  }
  const list = element("ul", "attention-strip__list");
  items.slice(0, 12).forEach((item) => {
    const row = element("li", "attention-strip__item");
    row.append(statusBadge(item.kind), element("span", "", item.project), element("span", "", item.text));
    list.append(row);
  });
  strip.append(list);
  return strip;
}

function projectCard(project, projectData, reviews) {
  const data = details(projectData);
  const tasks = tasksFrom(data);
  const todos = todosFrom(data);
  const card = element("a", "project-card");
  card.href = projectHash(getProjectId(project));
  const head = element("div", "project-card__head");
  head.append(element("h3", "", getProjectName(project)));
  const latest = reviews[0];
  if (latest) {
    const verdict = reviewVerdicts(latest)[0] || "review";
    head.append(badge(verdict, /fail|blocked/i.test(String(verdict)) ? "blocked" : "neutral"));
  }
  const stats = element("div", "project-card__stats");
  [
    [statusCount(tasks, "running"), "running"],
    [statusCount(tasks, "blocked"), "blocked"],
    [statusCount(tasks, "done"), "done recent"],
    [openTodoCount(todos), "open todos"],
  ].forEach(([count, label]) => {
    const stat = element("div", "project-card__stat");
    stat.append(element("b", "", count), element("span", "", label));
    stats.append(stat);
  });
  const foot = element("div", "project-card__foot");
  foot.append(element("span", "", `Last activity: ${formatDate(newestActivity(data.runs || []))}`));
  card.append(head, stats, foot);
  return card;
}

export async function renderOverview({ root, isCurrent }) {
  loading(root, 6);
  try {
    await loadProjects();
    const projects = getProjects();
    const loaded = await Promise.all(projects.map(async (project) => {
      const id = getProjectId(project);
      const [projectData, reviews] = await Promise.all([loadProject(id, "recent"), loadReviews(id)]);
      return { project, projectData, reviews };
    }));
    if (!isCurrent()) return;
    const page = document.createDocumentFragment();
    const header = element("header", "page-header");
    const heading = element("div", "");
    heading.append(element("h1", "", "Portfolio overview"), element("p", "", "Recent work across file-backed orchestration projects."));
    header.append(heading);
    page.append(header);
    const attention = [];
    loaded.forEach(({ project, projectData, reviews }) => {
      const name = getProjectName(project);
      tasksFrom(details(projectData)).filter((task) => taskStatus(task) === "blocked").forEach((task) => {
        attention.push({ kind: "blocked", project: name, text: task.title || task.id || "Blocked task" });
      });
      reviews.forEach((review) => {
        reviewVerdicts(review).filter((verdict) => /fail|blocked/i.test(String(verdict))).forEach((verdict) => {
          attention.push({ kind: "blocked", project: name, text: `Review verdict: ${verdict}` });
        });
        (Array.isArray(review.findings) ? review.findings : []).filter(isP0).forEach((finding) => {
          const level = (typeof finding === "string" ? (finding.match(/(^|\b)(P0|P1)\b/i)?.[0] ?? "P0") : finding.level || "P0").toUpperCase();
          const rawText = typeof finding === "string" ? finding : finding.text || finding.title || `${level} finding`;
          const cleanText = rawText.replace(new RegExp(`^\\s*${level}:?\\s*`, "i"), "");
          attention.push({ kind: "blocked", project: name, text: `${level}: ${cleanText}` });
        });
      });
    });
    page.append(attentionStrip(attention));
    const section = element("section", "");
    section.append(element("h2", "section-heading", "Projects"));
    const grid = element("div", "project-grid");
    loaded.forEach(({ project, projectData, reviews }) => grid.append(projectCard(project, projectData, reviews)));
    section.append(grid);
    page.append(section);
    root.replaceChildren(page);
  } catch (error) {
    if (isCurrent()) root.replaceChildren(errorState(error));
  }
}
