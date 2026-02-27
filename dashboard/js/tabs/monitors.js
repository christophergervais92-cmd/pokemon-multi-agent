// =============================================================================
// MONITORS (Refract-Style Task Groups)
// =============================================================================
// All functions reference globals from other modules:
//   API, sessionToken, currentUser, settings,
//   showNotification, optimizedLocalStorageSet, syncToServer

let monitorGroupId = null;
let monitorGroupName = null;
let monitorTasks = [];
let monitorsPollTimer = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tasksHeaders(extra = {}) {
    return {
        'Content-Type': 'application/json',
        ...(sessionToken ? { 'Authorization': `Bearer ${sessionToken}` } : {}),
        ...extra
    };
}

async function tasksFetch(path, options = {}) {
    const res = await fetch(`${API}${path}`, {
        cache: 'no-cache',
        ...options,
        headers: tasksHeaders(options.headers || {})
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
}

function _sanitizeTaskName(retailer, query) {
    const base = `${retailer}-${query}`.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return (base || `task-${Date.now()}`).slice(0, 64);
}

function formatIsoShort(isoStr) {
    if (!isoStr) return '\u2014';
    try {
        const d = new Date(isoStr);
        if (Number.isNaN(d.getTime())) return '\u2014';
        return d.toLocaleString();
    } catch {
        return '\u2014';
    }
}

// ---------------------------------------------------------------------------
// Monitor Group
// ---------------------------------------------------------------------------

async function ensureMonitorGroup() {
    if (!currentUser || !sessionToken) return null;
    monitorGroupName = `u-${currentUser.discord_id}-monitors`;

    const groupsRes = await tasksFetch('/tasks/groups');
    const groups = groupsRes.groups || [];
    let group = groups.find(g => g.name === monitorGroupName) || null;

    if (!group) {
        const zip = document.getElementById('monitorZip')?.value?.trim() || settings.zip || '90210';
        const interval = parseInt(document.getElementById('monitorInterval')?.value || '60', 10) || 60;
        const webhook = document.getElementById('monitorsWebhookUrl')?.value?.trim() || settings.alertWebhookUrl || '';

        try {
            const created = await tasksFetch('/tasks/groups', {
                method: 'POST',
                body: JSON.stringify({
                    name: monitorGroupName,
                    default_interval_seconds: interval,
                    default_zip_code: zip,
                    enabled: true,
                    notify_webhook_url: webhook
                })
            });
            const groupsRes2 = await tasksFetch('/tasks/groups');
            group = (groupsRes2.groups || []).find(g => g.id === created.group_id) || (groupsRes2.groups || []).find(g => g.name === monitorGroupName) || null;
        } catch (e) {
            // If group already exists (race/duplicate), we'll just re-list.
            const groupsRes2 = await tasksFetch('/tasks/groups');
            group = (groupsRes2.groups || []).find(g => g.name === monitorGroupName) || null;
        }
    }

    monitorGroupId = group?.id || null;

    const webhookInput = document.getElementById('monitorsWebhookUrl');
    if (webhookInput && group) {
        webhookInput.value = group.notify_webhook_url || settings.alertWebhookUrl || '';
    }

    const statusEl = document.getElementById('monitorsWebhookStatus');
    if (statusEl) {
        statusEl.textContent = monitorGroupId ? `Group: ${monitorGroupName}` : 'Failed to load monitor group.';
    }

    return group;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

async function saveMonitorGroupSettings() {
    if (!monitorGroupId) {
        await ensureMonitorGroup();
    }
    if (!monitorGroupId) {
        showNotification('Monitor group not ready. Try again.', 'error');
        return;
    }

    const webhook = document.getElementById('monitorsWebhookUrl')?.value?.trim() || '';
    const zip = document.getElementById('monitorZip')?.value?.trim() || settings.zip || '90210';
    const interval = parseInt(document.getElementById('monitorInterval')?.value || '60', 10) || 60;

    await tasksFetch(`/tasks/groups/${monitorGroupId}`, {
        method: 'PUT',
        body: JSON.stringify({
            default_zip_code: zip,
            default_interval_seconds: interval,
            notify_webhook_url: webhook
        })
    });

    // Persist locally as a convenience (also syncs with Discord login).
    settings.alertWebhookUrl = webhook;
    optimizedLocalStorageSet('settings', settings);
    if (sessionToken) {
        syncToServer('settings', settings);
    }

    showNotification('Monitor settings saved', 'success');
    await loadMonitors();
}

// ---------------------------------------------------------------------------
// Create / Load / Toggle Tasks
// ---------------------------------------------------------------------------

async function createMonitorTask() {
    if (!currentUser || !sessionToken) {
        showNotification('Login with Discord first', 'error');
        return;
    }

    if (!monitorGroupId) {
        await ensureMonitorGroup();
    }
    if (!monitorGroupId) {
        showNotification('Monitor group not ready. Try again.', 'error');
        return;
    }

    const query = document.getElementById('monitorQuery')?.value?.trim() || '';
    const retailer = document.getElementById('monitorRetailer')?.value || 'target';
    const zip = document.getElementById('monitorZip')?.value?.trim() || settings.zip || '90210';
    const interval = parseInt(document.getElementById('monitorInterval')?.value || '60', 10) || 60;

    if (!query) {
        showNotification('Enter a search query', 'error');
        return;
    }

    const name = _sanitizeTaskName(retailer, query);
    await tasksFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify({
            group_id: monitorGroupId,
            name,
            retailer,
            query,
            zip_code: zip,
            interval_seconds: interval,
            enabled: true
        })
    });

    const qEl = document.getElementById('monitorQuery');
    if (qEl) qEl.value = '';
    showNotification('Monitor added', 'success');
    await loadMonitors();
}

async function loadMonitors() {
    const listEl = document.getElementById('monitorsList');
    if (!listEl) return;

    if (!currentUser || !sessionToken) {
        listEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 0.75rem;">Login to view monitors.</div>';
        return;
    }

    if (!monitorGroupId) {
        await ensureMonitorGroup();
    }
    if (!monitorGroupId) {
        listEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 0.75rem;">Failed to load monitor group.</div>';
        return;
    }

    const res = await tasksFetch(`/tasks?group_id=${encodeURIComponent(monitorGroupId)}`);
    monitorTasks = res.tasks || [];

    if (!monitorTasks.length) {
        listEl.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; padding: 0.75rem;">No monitors yet. Add one above.</div>';
        return;
    }

    listEl.innerHTML = monitorTasks.map(t => {
        const enabled = !!t.enabled;
        const status = t.last_status || '\u2014';
        const statusColor = status === 'ok' ? 'var(--green)' : status === 'error' ? 'var(--red)' : 'var(--text-muted)';

        return `
            <div class="card" style="margin-bottom: 0.75rem; background: var(--bg); border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap;">
                    <div style="min-width: 240px; flex: 1;">
                        <div style="font-weight: 600; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                            <span>${t.name || `${t.retailer}:${t.query}`}</span>
                            <span class="rule-status" style="background: ${enabled ? 'rgba(34, 197, 94, 0.12)' : 'rgba(248, 113, 113, 0.12)'}; color: ${enabled ? 'var(--green)' : 'var(--red)'};">
                                ${enabled ? 'Enabled' : 'Paused'}
                            </span>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                            Retailer: <strong style="color: var(--text-secondary);">${t.retailer}</strong> • Query: <span style="font-family: 'Space Mono', monospace;">${t.query}</span>
                        </div>
                        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
                            <span>ZIP: <strong style="color: var(--text-secondary);">${t.zip_code || '\u2014'}</strong></span>
                            <span>Interval: <strong style="color: var(--text-secondary);">${t.interval_seconds || '\u2014'}s</strong></span>
                            <span>Last run: <strong style="color: var(--text-secondary);">${formatIsoShort(t.last_run_at)}</strong></span>
                            <span>Status: <strong style="color: ${statusColor};">${status}</strong></span>
                        </div>
                        ${t.last_error ? `<div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--red);">Error: ${t.last_error}</div>` : ''}
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button class="btn btn-sm btn-outline" onclick="toggleMonitorTask(${t.id}, ${enabled ? 'false' : 'true'})">
                            ${enabled ? 'Pause' : 'Enable'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    await refreshRunnerStatus();
}

async function toggleMonitorTask(taskId, enable) {
    try {
        await tasksFetch(`/tasks/${taskId}/${enable ? 'enable' : 'disable'}`, { method: 'POST' });
        await loadMonitors();
    } catch (e) {
        showNotification(e.message || 'Failed to update task', 'error');
    }
}

// ---------------------------------------------------------------------------
// Runner Status
// ---------------------------------------------------------------------------

async function refreshRunnerStatus() {
    const el = document.getElementById('runnerStatus');
    if (!el) return;

    let hb = null;
    let inProc = null;
    try { hb = await tasksFetch('/tasks/runner/heartbeat'); } catch {}
    try { inProc = await tasksFetch('/tasks/runner/status'); } catch {}

    const workerAlive = hb?.alive;
    const age = hb?.age_seconds;
    const hbText = hb?.last_heartbeat_at ? new Date(hb.last_heartbeat_at).toLocaleTimeString() : '\u2014';

    const workerLine = workerAlive
        ? `<span style="color: var(--green); font-weight: 700;">Worker Online</span> • last heartbeat ${hbText} (${age}s ago)`
        : `<span style="color: var(--text-muted); font-weight: 700;">Worker Offline</span> • deploy a runner with <span style="font-family: 'Space Mono', monospace;">python3 agents/run_task_runner.py</span>`;

    const inProcLine = (inProc && typeof inProc.running === 'boolean')
        ? `In-process runner: <strong style="color: ${inProc.running ? 'var(--green)' : 'var(--text-muted)'};">${inProc.running ? 'Running' : 'Stopped'}</strong>`
        : `In-process runner: <strong style="color: var(--text-muted);">Unknown</strong>`;

    el.innerHTML = `<div>${workerLine}</div><div style="margin-top: 0.25rem;">${inProcLine}</div>`;
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------

function startMonitorsPolling() {
    if (monitorsPollTimer) clearInterval(monitorsPollTimer);
    monitorsPollTimer = setInterval(() => {
        if (document.getElementById('monitors')?.classList.contains('active')) {
            refreshRunnerStatus();
        }
    }, 10000);
}

// ---------------------------------------------------------------------------
// In-Process Runner (Dev)
// ---------------------------------------------------------------------------

async function startInProcessRunner() {
    try {
        await tasksFetch('/tasks/runner/start', { method: 'POST' });
        showNotification('Runner started (dev mode)', 'success');
        await refreshRunnerStatus();
    } catch (e) {
        showNotification(e.message || 'Failed to start runner', 'error');
    }
}

async function stopInProcessRunner() {
    try {
        await tasksFetch('/tasks/runner/stop', { method: 'POST' });
        showNotification('Runner stopped', 'success');
        await refreshRunnerStatus();
    } catch (e) {
        showNotification(e.message || 'Failed to stop runner', 'error');
    }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function initMonitors() {
    const gate = document.getElementById('monitorsAuthGate');
    const app = document.getElementById('monitorsApp');
    if (!gate || !app) return;

    if (!currentUser || !sessionToken) {
        gate.style.display = 'block';
        app.style.display = 'none';
        return;
    }

    gate.style.display = 'none';
    app.style.display = 'block';

    const zipEl = document.getElementById('monitorZip');
    if (zipEl && !zipEl.value) zipEl.value = settings.zip || '90210';
    const intervalEl = document.getElementById('monitorInterval');
    if (intervalEl && !intervalEl.value) intervalEl.value = '60';

    await ensureMonitorGroup();
    await loadMonitors();
    startMonitorsPolling();
}
