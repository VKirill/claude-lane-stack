/**
 * Lane Board - Vanilla JS Frontend Application
 * Dark, terse, flat terminal-flavored read-only UI
 * Zero dependencies, zero build steps, safe rendering.
 */

// Application State
const state = {
  projects: [],
  currentProject: null,
  currentView: 'grid', // 'grid' | 'project'
  activeProjectId: null,
  sseStatus: 'connecting', // 'connecting' | 'connected' | 'disconnected'
  eventSource: null
};

// DOM References
const appContent = document.getElementById('app-content');
const projectCountEl = document.getElementById('project-count');
const sseStatusEl = document.getElementById('sse-status');

// Init application
function init() {
  window.addEventListener('hashchange', handleRoute);
  window.addEventListener('load', () => {
    setupSSE();
    handleRoute();
  });
}

// Router
function handleRoute() {
  const hash = window.location.hash || '#/';
  
  if (hash.startsWith('#/p/')) {
    const id = hash.substring(4);
    if (id) {
      state.currentView = 'project';
      state.activeProjectId = id;
      renderProjectView(id);
      return;
    }
  }
  
  // Default to grid view
  state.currentView = 'grid';
  state.activeProjectId = null;
  if (window.location.hash !== '#/') {
    window.location.hash = '#/';
  }
  renderGridView();
}

// Refresh current view (called on SSE refresh events or manual actions)
async function refreshCurrentView() {
  if (state.currentView === 'grid') {
    await fetchProjectsList();
    renderGridUI();
  } else if (state.currentView === 'project' && state.activeProjectId) {
    // Also refresh project count/list in background to keep top bar updated
    fetchProjectsList().catch(err => console.warn('Failed to background fetch projects list:', err));
    await fetchProjectDetail(state.activeProjectId);
    renderProjectUI();
  }
}

// SSE Connection
function setupSSE() {
  if (state.eventSource) {
    state.eventSource.close();
  }

  updateSSEStatus('connecting');
  
  // Connect to SSE endpoint
  const es = new EventSource('/api/events');
  state.eventSource = es;

  es.onopen = () => {
    updateSSEStatus('connected');
  };

  es.onerror = () => {
    updateSSEStatus('disconnected');
    // Browser automatically retries EventSource, but we handle status display
  };

  es.addEventListener('refresh', (e) => {
    console.log('SSE refresh event received:', e.data);
    refreshCurrentView();
  });
}

function updateSSEStatus(status) {
  state.sseStatus = status;
  sseStatusEl.className = 'status-indicator';
  
  if (status === 'connected') {
    sseStatusEl.classList.add('sse-connected');
    sseStatusEl.textContent = 'SSE: CONNECTED';
  } else if (status === 'connecting') {
    sseStatusEl.classList.add('sse-connecting');
    sseStatusEl.textContent = 'SSE: CONNECTING';
  } else {
    sseStatusEl.classList.add('sse-disconnected');
    sseStatusEl.textContent = 'SSE: DISCONNECTED';
  }
}

// Data Fetching
async function fetchProjectsList() {
  try {
    const response = await fetch('/api/projects');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    state.projects = data.projects || [];
    
    // Update live count in header
    projectCountEl.textContent = `${state.projects.length} project${state.projects.length === 1 ? '' : 's'}`;
  } catch (error) {
    console.error('Error fetching projects list:', error);
    throw error;
  }
}

async function fetchProjectDetail(id) {
  try {
    const response = await fetch(`/api/projects/${id}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Project not found');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    state.currentProject = data;
  } catch (error) {
    console.error(`Error fetching project details for ${id}:`, error);
    throw error;
  }
}

// Renderers
async function renderGridView() {
  renderLoadingState();
  try {
    await fetchProjectsList();
    renderGridUI();
  } catch (error) {
    renderErrorState('Failed to fetch projects grid. Make sure the backend server is running.', error);
  }
}

async function renderProjectView(id) {
  renderLoadingState();
  try {
    // Fetch both to make sure we keep top bar and side info updated
    await Promise.all([
      fetchProjectsList().catch(err => console.warn('Failed to background fetch projects list:', err)),
      fetchProjectDetail(id)
    ]);
    renderProjectUI();
  } catch (error) {
    renderErrorState(`Failed to fetch details for project [${id}].`, error);
  }
}

function renderLoadingState() {
  appContent.innerHTML = '';
  const loading = document.createElement('div');
  loading.className = 'empty-state';
  const title = document.createElement('div');
  title.className = 'empty-state-title';
  title.textContent = 'LOADING DATA...';
  loading.appendChild(title);
  appContent.appendChild(loading);
}

function renderErrorState(message, error) {
  appContent.innerHTML = '';
  
  const container = document.createElement('div');
  container.className = 'error-state';
  
  const title = document.createElement('div');
  title.style.fontWeight = 'bold';
  title.style.marginBottom = '8px';
  title.textContent = `[ERROR] ${message}`;
  container.appendChild(title);
  
  if (error) {
    const details = document.createElement('div');
    details.style.fontSize = '11px';
    details.style.opacity = '0.8';
    details.textContent = error.toString();
    container.appendChild(details);
  }
  
  appContent.appendChild(container);
}

// Render Projects Grid UI
function renderGridUI() {
  appContent.innerHTML = '';
  
  if (state.projects.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    
    const title = document.createElement('div');
    title.className = 'empty-state-title';
    title.textContent = 'NO PROJECTS FOUND';
    empty.appendChild(title);
    
    const desc = document.createElement('div');
    desc.textContent = 'Add workspace directories with .agents/runs in them to populate this board.';
    empty.appendChild(desc);
    
    appContent.appendChild(empty);
    return;
  }
  
  const header = document.createElement('div');
  header.className = 'view-header';
  const h2 = document.createElement('h2');
  h2.textContent = 'ACTIVE PROJECTS';
  header.appendChild(h2);
  appContent.appendChild(header);
  
  const grid = document.createElement('div');
  grid.className = 'projects-grid';
  
  state.projects.forEach(project => {
    const card = document.createElement('div');
    card.className = 'project-card';
    card.addEventListener('click', () => {
      window.location.hash = `#/p/${project.id}`;
    });
    
    // Header (name & review dot)
    const cardHeader = document.createElement('div');
    cardHeader.className = 'project-card-header';
    
    const name = document.createElement('div');
    name.className = 'project-name mono-accent';
    name.textContent = project.name;
    cardHeader.appendChild(name);
    
    const dot = document.createElement('div');
    dot.className = 'review-dot';
    if (project.review) {
      if (project.review.failed > 0) {
        dot.classList.add('failed');
        dot.title = `Night review: ${project.review.failed} failed verdicts`;
      } else {
        dot.classList.add('passed');
        dot.title = 'Night review: All verdicts passed';
      }
    } else {
      dot.classList.add('none');
      dot.title = 'No night review yet';
    }
    cardHeader.appendChild(dot);
    card.appendChild(cardHeader);
    
    // Status counts chips
    const chipsContainer = document.createElement('div');
    chipsContainer.className = 'status-chips';
    
    const counts = project.taskCounts || { pending: 0, running: 0, done: 0, blocked: 0, stalled: 0 };
    const statuses = ['pending', 'running', 'done', 'blocked', 'stalled'];
    
    statuses.forEach(status => {
      const chip = document.createElement('span');
      chip.className = `chip ${status}`;
      chip.textContent = `${status} ${counts[status] || 0}`;
      chipsContainer.appendChild(chip);
    });
    card.appendChild(chipsContainer);
    
    // Progress preview (2 Now lines, Blocked line if any)
    const previewContainer = document.createElement('div');
    previewContainer.className = 'card-progress-preview';
    
    const nowBullets = project.progressNow || [];
    const blockedBullets = project.progressBlocked || [];
    
    // First 2 Now bullets
    if (nowBullets.length > 0) {
      const bulletLimit = Math.min(nowBullets.length, 2);
      for (let i = 0; i < bulletLimit; i++) {
        const line = document.createElement('div');
        line.className = 'preview-now';
        line.textContent = `> ${nowBullets[i]}`;
        previewContainer.appendChild(line);
      }
    } else {
      const noProgress = document.createElement('div');
      noProgress.className = 'preview-now';
      noProgress.style.fontStyle = 'italic';
      noProgress.textContent = 'No current progress bullets';
      previewContainer.appendChild(noProgress);
    }
    
    // Red Blocked line if any blocked entries exist
    if (blockedBullets.length > 0) {
      const blockedLine = document.createElement('div');
      blockedLine.className = 'preview-blocked';
      blockedLine.textContent = `! Blocked: ${blockedBullets[0]}`;
      previewContainer.appendChild(blockedLine);
    }
    
    card.appendChild(previewContainer);
    
    // Footer / Card Meta (Todos count)
    const meta = document.createElement('div');
    meta.className = 'card-meta';
    
    const todoInfo = document.createElement('span');
    todoInfo.textContent = `TODOS: ${project.todoOpenCount || 0} open`;
    meta.appendChild(todoInfo);
    
    const pathInfo = document.createElement('span');
    pathInfo.style.fontSize = '10px';
    pathInfo.style.opacity = '0.5';
    // Just show basename or short representation of path if too long
    const shortPath = project.path ? project.path.replace(/^\/home\/ubuntu/, '~') : '';
    pathInfo.textContent = shortPath;
    meta.appendChild(pathInfo);
    
    card.appendChild(meta);
    grid.appendChild(card);
  });
  
  appContent.appendChild(grid);
}

// Render Project Detail UI
function renderProjectUI() {
  appContent.innerHTML = '';
  
  const detail = state.currentProject;
  if (!detail || !detail.project) {
    renderErrorState('Project detail structure is invalid or empty.', null);
    return;
  }
  
  const projectInfo = detail.project;
  
  // Back Link
  const back = document.createElement('a');
  back.href = '#/';
  back.className = 'back-link';
  back.textContent = '◀ BACK TO PROJECTS';
  appContent.appendChild(back);
  
  // Header
  const header = document.createElement('div');
  header.className = 'view-header';
  const h2 = document.createElement('h2');
  h2.textContent = projectInfo.name;
  header.appendChild(h2);
  
  const path = document.createElement('div');
  path.className = 'path-sub';
  path.textContent = projectInfo.path || '';
  header.appendChild(path);
  appContent.appendChild(header);
  
  // Layout columns container
  const layout = document.createElement('div');
  layout.className = 'project-detail-layout';
  
  // Kanban board section
  const kanban = document.createElement('div');
  kanban.className = 'kanban-board';
  
  // Group all tasks from runs by status
  const tasksByStatus = {
    pending: [],
    running: [],
    done: [],
    blocked: [],
    stalled: []
  };
  
  const runs = detail.runs || [];
  runs.forEach(run => {
    const runTasks = run.tasks || [];
    runTasks.forEach(task => {
      let status = (task.status || 'pending').toLowerCase();
      if (!tasksByStatus[status]) {
        status = 'pending'; // Fallback per SPEC
      }
      // Attach run slug to task for rendering
      tasksByStatus[status].push({
        ...task,
        runSlug: run.slug
      });
    });
  });
  
  // Render Kanban Columns
  const statusNames = ['pending', 'running', 'done', 'blocked', 'stalled'];
  statusNames.forEach(status => {
    const col = document.createElement('div');
    col.className = 'kanban-column';
    
    // Column Header
    const colHeader = document.createElement('div');
    colHeader.className = 'kanban-column-header';
    
    const colTitle = document.createElement('span');
    colTitle.className = 'column-title';
    colTitle.textContent = status;
    colHeader.appendChild(colTitle);
    
    const colCount = document.createElement('span');
    colCount.className = 'column-count';
    const list = tasksByStatus[status];
    colCount.textContent = `[${list.length}]`;
    colHeader.appendChild(colCount);
    
    col.appendChild(colHeader);
    
    // Column tasks
    const tasksContainer = document.createElement('div');
    tasksContainer.className = 'kanban-tasks';
    
    if (list.length === 0) {
      const emptyTasks = document.createElement('div');
      emptyTasks.style.fontSize = '11px';
      emptyTasks.style.color = 'var(--text-muted)';
      emptyTasks.style.textAlign = 'center';
      emptyTasks.style.padding = '20px 0';
      emptyTasks.style.fontStyle = 'italic';
      emptyTasks.textContent = 'Empty';
      tasksContainer.appendChild(emptyTasks);
    } else {
      list.forEach(task => {
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        
        // Task Title
        const title = document.createElement('div');
        title.className = 'task-title';
        title.textContent = task.title || task.id || 'Untitled Task';
        taskCard.appendChild(title);
        
        // Task Badges
        const badgesContainer = document.createElement('div');
        badgesContainer.className = 'task-badges';
        
        // Run Slug Tag
        if (task.runSlug) {
          const runBadge = document.createElement('span');
          runBadge.className = 'task-badge run-slug';
          runBadge.textContent = task.runSlug;
          badgesContainer.appendChild(runBadge);
        }
        
        // Risk Badge
        if (task.risk) {
          const riskBadge = document.createElement('span');
          const riskClass = `risk-${task.risk.toLowerCase()}`;
          riskBadge.className = `task-badge ${riskClass}`;
          riskBadge.textContent = `risk: ${task.risk}`;
          badgesContainer.appendChild(riskBadge);
        }
        
        // Verify Badge
        if (task.verify) {
          const verifyBadge = document.createElement('span');
          verifyBadge.className = 'task-badge';
          verifyBadge.textContent = `verify: ${task.verify}`;
          badgesContainer.appendChild(verifyBadge);
        }
        
        taskCard.appendChild(badgesContainer);
        tasksContainer.appendChild(taskCard);
      });
    }
    
    col.appendChild(tasksContainer);
    kanban.appendChild(col);
  });
  layout.appendChild(kanban);
  
  // Side panel section
  const panel = document.createElement('div');
  panel.className = 'side-panel';
  
  // 1. PROGRESS Section
  const progressSec = document.createElement('div');
  progressSec.className = 'panel-section';
  
  const progressTitle = document.createElement('div');
  progressTitle.className = 'panel-section-title';
  progressTitle.textContent = 'PROGRESS';
  progressSec.appendChild(progressTitle);
  
  const progData = detail.progress || { now: [], blocked: [], next: [] };
  const hasProgress = (progData.now && progData.now.length > 0) || 
                      (progData.blocked && progData.blocked.length > 0) || 
                      (progData.next && progData.next.length > 0);
  
  if (!hasProgress) {
    const emptyProg = document.createElement('div');
    emptyProg.style.fontStyle = 'italic';
    emptyProg.style.color = 'var(--text-muted)';
    emptyProg.textContent = 'No progress data found in PROGRESS.md.';
    progressSec.appendChild(emptyProg);
  } else {
    const listGroup = document.createElement('div');
    listGroup.className = 'progress-list-group';
    
    // NOW
    if (progData.now && progData.now.length > 0) {
      const nowWrap = document.createElement('div');
      const subTitle = document.createElement('div');
      subTitle.className = 'progress-subgroup-title';
      subTitle.textContent = 'NOW';
      nowWrap.appendChild(subTitle);
      
      const ul = document.createElement('ul');
      ul.className = 'bullet-list';
      progData.now.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        ul.appendChild(li);
      });
      nowWrap.appendChild(ul);
      listGroup.appendChild(nowWrap);
    }
    
    // BLOCKED
    if (progData.blocked && progData.blocked.length > 0) {
      const blockedWrap = document.createElement('div');
      const subTitle = document.createElement('div');
      subTitle.className = 'progress-subgroup-title blocked-title';
      subTitle.textContent = 'BLOCKED';
      blockedWrap.appendChild(subTitle);
      
      const ul = document.createElement('ul');
      ul.className = 'bullet-list blocked-bullets';
      progData.blocked.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        ul.appendChild(li);
      });
      blockedWrap.appendChild(ul);
      listGroup.appendChild(blockedWrap);
    }
    
    // NEXT
    if (progData.next && progData.next.length > 0) {
      const nextWrap = document.createElement('div');
      const subTitle = document.createElement('div');
      subTitle.className = 'progress-subgroup-title';
      subTitle.textContent = 'NEXT';
      nextWrap.appendChild(subTitle);
      
      const ul = document.createElement('ul');
      ul.className = 'bullet-list';
      progData.next.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        ul.appendChild(li);
      });
      nextWrap.appendChild(ul);
      listGroup.appendChild(nextWrap);
    }
    
    progressSec.appendChild(listGroup);
  }
  panel.appendChild(progressSec);
  
  // 2. TODOS Section
  const todosSec = document.createElement('div');
  todosSec.className = 'panel-section';
  
  const todosTitle = document.createElement('div');
  todosTitle.className = 'panel-section-title';
  todosTitle.textContent = 'TODOS';
  todosSec.appendChild(todosTitle);
  
  const rawTodos = detail.todos || [];
  
  if (rawTodos.length === 0) {
    const emptyTodos = document.createElement('div');
    emptyTodos.style.fontStyle = 'italic';
    emptyTodos.style.color = 'var(--text-muted)';
    emptyTodos.textContent = 'No todos found.';
    todosSec.appendChild(emptyTodos);
  } else {
    // Sort: open items first
    // Helper to determine if todo is open
    const isOpen = (todo) => {
      const status = (todo.status || '').toLowerCase();
      return status !== 'done' && status !== 'completed' && status !== 'closed' && status !== 'x';
    };
    
    const sortedTodos = [...rawTodos].sort((a, b) => {
      const aOpen = isOpen(a);
      const bOpen = isOpen(b);
      if (aOpen && !bOpen) return -1;
      if (!aOpen && bOpen) return 1;
      return 0;
    });
    
    const todoList = document.createElement('div');
    todoList.className = 'todo-list';
    
    sortedTodos.forEach(todo => {
      const item = document.createElement('div');
      item.className = 'todo-item';
      if (!isOpen(todo)) {
        item.classList.add('completed');
      }
      
      const text = document.createElement('span');
      text.className = 'todo-title';
      // Format text to show status if not done, or show title
      text.textContent = todo.title || todo.id || 'Untitled Todo';
      item.appendChild(text);
      
      if (todo.priority) {
        const priorityVal = todo.priority.toLowerCase();
        const prioBadge = document.createElement('span');
        prioBadge.className = `todo-priority ${priorityVal}`;
        prioBadge.textContent = todo.priority;
        item.appendChild(prioBadge);
      }
      
      todoList.appendChild(item);
    });
    
    todosSec.appendChild(todoList);
  }
  panel.appendChild(todosSec);
  
  // 3. NIGHT REVIEW Section
  const reviewSec = document.createElement('div');
  reviewSec.className = 'panel-section';
  
  const reviewTitle = document.createElement('div');
  reviewTitle.className = 'panel-section-title';
  reviewTitle.textContent = 'NIGHT REVIEW';
  reviewSec.appendChild(reviewTitle);
  
  const rev = detail.review;
  
  if (!rev) {
    const emptyRev = document.createElement('div');
    emptyRev.style.fontStyle = 'italic';
    emptyRev.style.color = 'var(--text-muted)';
    emptyRev.textContent = 'No review data found.';
    reviewSec.appendChild(emptyRev);
  } else {
    // Date
    if (rev.date) {
      const dateDiv = document.createElement('div');
      dateDiv.className = 'review-meta';
      dateDiv.textContent = `Date: ${rev.date}`;
      reviewSec.appendChild(dateDiv);
    }
    
    // Verdict Chips per scope
    const verdicts = rev.verdicts || [];
    if (verdicts.length > 0) {
      const chips = document.createElement('div');
      chips.className = 'verdict-chips';
      verdicts.forEach(v => {
        const verdictVal = (v.verdict || '').toLowerCase();
        const chip = document.createElement('span');
        chip.className = `verdict-chip ${verdictVal === 'passed' ? 'passed' : 'failed'}`;
        chip.textContent = `${v.scope}: ${v.verdict}`;
        chips.appendChild(chip);
      });
      reviewSec.appendChild(chips);
    }
    
    // Findings P0/P1
    const findings = rev.findings || [];
    if (findings.length > 0) {
      const list = document.createElement('div');
      list.className = 'findings-list';
      findings.forEach(f => {
        const item = document.createElement('div');
        const level = (f.level || 'P1').toUpperCase();
        item.className = `finding-item ${level === 'P0' ? 'p0' : 'p1'}`;
        item.textContent = `[${level}] ${f.text}`;
        list.appendChild(item);
      });
      reviewSec.appendChild(list);
    }
    
    // Morning fix plan checklist lines
    const plan = rev.fixPlan || [];
    if (plan.length > 0) {
      const title = document.createElement('div');
      title.className = 'fix-plan-title';
      title.textContent = 'Morning Fix Plan';
      reviewSec.appendChild(title);
      
      const list = document.createElement('div');
      list.className = 'fix-plan-list';
      plan.forEach((item, index) => {
        const line = document.createElement('label');
        line.className = 'checklist-line';
        
        const check = document.createElement('input');
        check.type = 'checkbox';
        check.disabled = true;
        line.appendChild(check);
        
        const labelText = document.createElement('span');
        labelText.textContent = item;
        line.appendChild(labelText);
        
        list.appendChild(line);
      });
      reviewSec.appendChild(list);
    }
  }
  panel.appendChild(reviewSec);
  
  layout.appendChild(panel);
  appContent.appendChild(layout);
}

// Run application
init();
