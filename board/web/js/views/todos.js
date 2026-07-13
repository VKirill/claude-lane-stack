import { projectHash } from "../router.js";
import { getProjectName, getProjects, getScope, getTodoSelection, loadProject, setTodoSelection, todoId, todoPriority, todoStatus, todoTitle, todosFrom } from "../store.js";
import { element, emptyState, errorState, formatDate, loading } from "../ui.js";
import { priorityBadge } from "../components/badges.js";
import { openTodoDrawer } from "../components/drawer.js";

const priorityRank = { high: 0, medium: 1, low: 2 };

function details(payload) {
  return payload && payload.project && typeof payload.project === "object" ? { ...payload, ...payload.project } : payload || {};
}

function projectName(projectId) {
  return getProjectName(getProjects().find((project) => String(project.id ?? project.projectId ?? project.slug ?? project.name) === projectId));
}

function tabs(projectId) {
  const nav = element("nav", "view-tabs");
  nav.setAttribute("aria-label", "Project views");
  [["board", "Board"], ["todos", "Todos"], ["runs", "Runs"], ["reviews", "Reviews"]].forEach(([section, label]) => {
    const link = element("a", `view-tabs__link${section === "todos" ? " view-tabs__link--active" : ""}`, label);
    link.href = projectHash(projectId, section);
    if (section === "todos") link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  return nav;
}

function groupFor(todo) {
  const status = todoStatus(todo);
  if (["open", "active", "todo"].includes(status)) return "Open";
  if (["incubating", "idea", "backlog"].includes(status)) return "Incubating";
  return "Other";
}

function sortTodos(todos) {
  return [...todos].sort((left, right) => {
    const priority = priorityRank[todoPriority(left)] - priorityRank[todoPriority(right)];
    if (priority !== 0) return priority;
    return todoId(right).localeCompare(todoId(left), undefined, { numeric: true });
  });
}

function todoRow(projectId, todo, index) {
  const row = document.createElement("button");
  row.type = "button";
  row.className = `todo-row${getTodoSelection() === index ? " todo-row--selected" : ""}`;
  row.dataset.todoIndex = String(index);
  row.append(priorityBadge(todoPriority(todo)), element("span", "todo-row__title", todoTitle(todo)));
  const date = todo.date || todo.createdAt || todo.updatedAt || "";
  row.append(element("span", "todo-row__meta", `${todoId(todo)}${date ? ` · ${formatDate(date)}` : ""}`));
  row.addEventListener("click", () => {
    setTodoSelection(index);
    openTodoDrawer(projectId, todoId(todo));
  });
  return row;
}

export async function renderTodos({ root, route, isCurrent }) {
  loading(root, 7);
  try {
    const project = details(await loadProject(route.projectId, getScope(route.projectId)));
    if (!isCurrent()) return;
    const page = document.createDocumentFragment();
    const header = element("header", "page-header");
    const heading = element("div", "");
    heading.append(element("h1", "", "Todos"), element("p", "", `${project.name || project.projectName || projectName(route.projectId)} · use j/k to move through the list.`));
    header.append(heading, tabs(route.projectId));
    page.append(header);
    const groups = { Open: [], Incubating: [], Other: [] };
    sortTodos(todosFrom(project)).forEach((todo) => groups[groupFor(todo)].push(todo));
    let index = 0;
    Object.entries(groups).forEach(([name, todos]) => {
      const section = element("section", "todo-group");
      section.append(element("h2", "section-heading", `${name} (${todos.length})`));
      if (todos.length === 0) {
        section.append(emptyState(`No ${name.toLowerCase()} todos recorded.`));
      } else {
        const list = element("div", "todo-list");
        todos.forEach((todo) => {
          list.append(todoRow(route.projectId, todo, index));
          index += 1;
        });
        section.append(list);
      }
      page.append(section);
    });
    root.replaceChildren(page);
  } catch (error) {
    if (isCurrent()) root.replaceChildren(errorState(error));
  }
}
