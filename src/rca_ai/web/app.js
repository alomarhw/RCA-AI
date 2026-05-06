const state = { projects: [], selectedProjectId: null };
const $ = (selector) => document.querySelector(selector);

function toast(message, isError = false) {
  const el = $('#toast');
  el.textContent = message;
  el.style.background = isError ? '#991b1b' : '#111827';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 4200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with ${response.status}`);
  }
  return payload;
}

function renderProjects() {
  $('#projectCount').textContent = state.projects.length;
  const list = $('#projects');
  list.innerHTML = '';
  if (state.projects.length === 0) {
    list.innerHTML = '<p class="muted">No projects yet. Create a demo or register an Overleaf project.</p>';
    return;
  }
  for (const project of state.projects) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `project-item ${project.id === state.selectedProjectId ? 'active' : ''}`;
    button.innerHTML = `<strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.status)} · ${escapeHtml(project.overleaf_git_url)}</small>`;
    button.addEventListener('click', () => selectProject(project.id));
    list.appendChild(button);
  }
}

function selectProject(projectId) {
  state.selectedProjectId = projectId;
  const project = state.projects.find((item) => item.id === projectId);
  $('#selectedProjectName').textContent = project ? project.name : 'No project selected';
  renderProjects();
}

async function loadProjects() {
  state.projects = await api('/projects');
  if (!state.selectedProjectId && state.projects.length > 0) {
    state.selectedProjectId = state.projects[0].id;
  }
  if (!state.projects.some((project) => project.id === state.selectedProjectId)) {
    state.selectedProjectId = state.projects[0]?.id || null;
  }
  const selected = state.projects.find((project) => project.id === state.selectedProjectId);
  $('#selectedProjectName').textContent = selected ? selected.name : 'No project selected';
  renderProjects();
}

function requireProject() {
  if (!state.selectedProjectId) {
    throw new Error('Select a project first. You can create a demo paper to get started.');
  }
  return state.selectedProjectId;
}

function formJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function pretty(payload) {
  return JSON.stringify(payload, null, 2);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#039;',
    '"': '&quot;',
  }[char]));
}

$('#refreshProjects').addEventListener('click', async () => {
  try {
    await loadProjects();
    toast('Projects refreshed.');
  } catch (error) {
    toast(error.message, true);
  }
});

$('#createDemo').addEventListener('click', async () => {
  try {
    const project = await api('/demo', { method: 'POST', body: JSON.stringify({ name: 'Demo Research Paper' }) });
    state.selectedProjectId = project.id;
    await loadProjects();
    toast('Demo paper created. You can index it now.');
  } catch (error) {
    toast(error.message, true);
  }
});

$('#projectForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const project = await api('/projects', { method: 'POST', body: JSON.stringify(formJson(event.currentTarget)) });
    state.selectedProjectId = project.id;
    event.currentTarget.reset();
    event.currentTarget.default_branch.value = 'main';
    await loadProjects();
    toast('Project registered.');
  } catch (error) {
    toast(error.message, true);
  }
});

$('#cloneForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const projectId = requireProject();
    const payload = formJson(event.currentTarget);
    await api(`/projects/${projectId}/clone`, { method: 'POST', body: JSON.stringify(payload) });
    await loadProjects();
    toast('Project cloned.');
  } catch (error) {
    toast(error.message, true);
  }
});

$('#indexForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const projectId = requireProject();
    const { root_file } = formJson(event.currentTarget);
    const query = root_file ? `?root_file=${encodeURIComponent(root_file)}` : '';
    const result = await api(`/projects/${projectId}/index${query}`);
    $('#indexOutput').textContent = pretty(result);
    await loadProjects();
    toast('Manuscript indexed.');
  } catch (error) {
    toast(error.message, true);
  }
});

$('#suggestForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const projectId = requireProject();
    const payload = formJson(event.currentTarget);
    payload.root_file = payload.target_file;
    const patch = await api(`/projects/${projectId}/suggest`, { method: 'POST', body: JSON.stringify(payload) });
    $('#patchOutput').textContent = patch.diff || pretty(patch);
    toast('Patch generated.');
  } catch (error) {
    toast(error.message, true);
  }
});

loadProjects().catch((error) => toast(error.message, true));
