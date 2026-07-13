const API_ROOT = "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson(path) {
  const response = await fetch(`${API_ROOT}${path}`, { headers: { Accept: "application/json" } });
  let data = null;
  try {
    data = await response.json();
  } catch {
    throw new ApiError("The board returned an invalid response.", response.status);
  }
  if (!response.ok) {
    throw new ApiError(data && data.error ? String(data.error) : "The board request failed.", response.status);
  }
  return data;
}

function segment(value) {
  return encodeURIComponent(String(value));
}

export const api = {
  projects() {
    return getJson("/projects");
  },
  project(projectId, scope = "recent") {
    return getJson(`/projects/${segment(projectId)}?scope=${scope === "all" ? "all" : "recent"}`);
  },
  todo(projectId, todoId) {
    return getJson(`/projects/${segment(projectId)}/todos/${segment(todoId)}`);
  },
  task(projectId, run, taskId) {
    return getJson(`/projects/${segment(projectId)}/tasks/${segment(run)}/${segment(taskId)}`);
  },
  reviews(projectId) {
    return getJson(`/projects/${segment(projectId)}/reviews`);
  },
  search(query) {
    return getJson(`/search?q=${encodeURIComponent(query)}`);
  },
};
