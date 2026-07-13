function matches(taskOrTodo, query) {
  return [taskOrTodo?.id, taskOrTodo?.title]
    .some((value) => String(value ?? '').toLowerCase().includes(query));
}

function resultLimit(cap) {
  const limit = Number(cap);
  return Number.isInteger(limit) && limit >= 0 ? limit : 50;
}

/** Search already-built snapshots so HTTP and filesystem work stay outside matching. */
export function searchAcrossProjects(snapshots, query, { cap = 50 } = {}) {
  const normalizedQuery = String(query ?? '').trim().toLowerCase();
  if (!normalizedQuery) return [];

  const results = [];
  const limit = resultLimit(cap);
  if (limit === 0) return results;
  for (const snapshot of Array.isArray(snapshots) ? snapshots : []) {
    const project = snapshot?.project ?? {};
    for (const run of Array.isArray(snapshot?.runs) ? snapshot.runs : []) {
      for (const task of Array.isArray(run?.tasks) ? run.tasks : []) {
        if (!matches(task, normalizedQuery)) continue;
        results.push({
          type: 'task',
          projectId: project.id,
          projectName: project.name,
          id: task.id,
          title: task.title,
          status: task.status,
          run: task.run ?? run.slug,
        });
        if (results.length >= limit) return results;
      }
    }
    for (const todo of Array.isArray(snapshot?.todos) ? snapshot.todos : []) {
      if (!matches(todo, normalizedQuery)) continue;
      results.push({
        type: 'todo',
        projectId: project.id,
        projectName: project.name,
        id: todo.id,
        title: todo.title,
        status: todo.status,
      });
      if (results.length >= limit) return results;
    }
  }
  return results;
}
