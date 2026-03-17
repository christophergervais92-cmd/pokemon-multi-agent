// =============================================================================
// AUTHENTICATION SYSTEM
// =============================================================================
// Depends on globals: API, settings, showNotification, optimizedLocalStorageGet,
// optimizedLocalStorageSet, loadSettings, renderPortfolio, renderAutoBuyRules

let currentUser = null;
let sessionToken = localStorage.getItem('session_token') || null;
let syncInProgress = false;
let lastSyncTime = 0;
const SYNC_DEBOUNCE = 2000; // 2 second debounce for saves

// Initialize auth on page load
async function initAuth() {
    // Check for OAuth callback
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state) {
        // Complete OAuth flow
        await completeDiscordLogin(code, state);
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
        return;
    }

    // Check if already logged in
    if (sessionToken) {
        const user = await validateSession();
        if (user) {
            currentUser = user;
            showUserInfo();
            await syncFromServer();
        } else {
            // Invalid session, clear it
            sessionToken = null;
            localStorage.removeItem('session_token');
            showLoginButton();
        }
    } else {
        showLoginButton();
    }
}

function showLoginButton() {
    const loginBtn = document.getElementById('loginBtn');
    const userInfo = document.getElementById('userInfo');
    if (loginBtn) loginBtn.style.display = 'block';
    if (userInfo) userInfo.style.display = 'none';
}

function showUserInfo() {
    const loginBtn = document.getElementById('loginBtn');
    const userInfo = document.getElementById('userInfo');
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');

    if (loginBtn) loginBtn.style.display = 'none';
    if (userInfo) userInfo.style.display = 'flex';

    if (currentUser) {
        if (userAvatar && currentUser.avatar) {
            userAvatar.src = `https://cdn.discordapp.com/avatars/${currentUser.discord_id}/${currentUser.avatar}.png`;
            userAvatar.style.display = 'block';
        } else if (userAvatar) {
            userAvatar.style.display = 'none';
        }
        if (userName) userName.textContent = currentUser.username || 'User';
    }

    updateSyncStatus();
}

async function startDiscordLogin() {
    try {
        const res = await fetch(`${API}/auth/discord`);
        const data = await res.json();

        if (data.url) {
            // Store state for verification
            localStorage.setItem('oauth_state', data.state);
            // Redirect to Discord
            window.location.href = data.url;
        } else {
            showNotification('Discord login not configured', 'error');
        }
    } catch (e) {
        console.error('Login error:', e);
        showNotification('Failed to start login', 'error');
    }
}

async function completeDiscordLogin(code, state) {
    try {
        const res = await fetch(`${API}/auth/discord/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);
        const data = await res.json();

        if (data.success && data.session_token) {
            sessionToken = data.session_token;
            localStorage.setItem('session_token', sessionToken);
            currentUser = data.user;
            showUserInfo();
            showNotification('Logged in successfully!', 'success');

            // Sync data from server
            await syncFromServer();
        } else {
            showNotification(data.error || 'Login failed', 'error');
            showLoginButton();
        }
    } catch (e) {
        console.error('OAuth callback error:', e);
        showNotification('Login failed', 'error');
        showLoginButton();
    }
}

async function validateSession() {
    if (!sessionToken) return null;

    try {
        const res = await fetch(`${API}/auth/me`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });

        if (res.ok) {
            return await res.json();
        }
    } catch (e) {
        console.error('Session validation error:', e);
    }
    return null;
}

async function logout() {
    try {
        await fetch(`${API}/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            }
        });
    } catch (e) {
        console.error('Logout error:', e);
    }

    sessionToken = null;
    currentUser = null;
    localStorage.removeItem('session_token');
    showLoginButton();
    showNotification('Logged out', 'success');
}

// Sync data FROM server (on login/page load)
async function syncFromServer() {
    if (!sessionToken) return;

    try {
        const res = await fetch(`${API}/auth/data`, {
            headers: { 'Authorization': `Bearer ${sessionToken}` }
        });

        if (res.ok) {
            const { data } = await res.json();

            // Merge server data with local (server takes priority)
            if (data.portfolio) {
                localStorage.setItem('portfolio', JSON.stringify(data.portfolio));
            }
            if (data.settings) {
                settings = { ...settings, ...data.settings };
                optimizedLocalStorageSet('settings', settings);
                loadSettings();
            }
            if (data.watchlist) {
                localStorage.setItem('watchlist', JSON.stringify(data.watchlist));
            }
            if (data.autobuy_rules) {
                localStorage.setItem('autoBuyRules', JSON.stringify(data.autobuy_rules));
                renderAutoBuyRules();
            }

            // Re-render portfolio
            renderPortfolio();

            console.log('Synced data from server');
        }
    } catch (e) {
        console.error('Sync from server error:', e);
    }
}

// Sync data TO server (debounced auto-save)
async function syncToServer(dataType, data) {
    if (!sessionToken || syncInProgress) return;

    // Debounce
    const now = Date.now();
    if (now - lastSyncTime < SYNC_DEBOUNCE) {
        setTimeout(() => syncToServer(dataType, data), SYNC_DEBOUNCE);
        return;
    }

    syncInProgress = true;
    lastSyncTime = now;

    try {
        const res = await fetch(`${API}/auth/data/${dataType}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ [dataType]: data })
        });

        if (!res.ok) {
            console.error('Sync to server failed:', await res.text());
        }
    } catch (e) {
        console.error('Sync to server error:', e);
    } finally {
        syncInProgress = false;
    }
}

// Export data to file
function exportUserData() {
    const data = {
        portfolio: optimizedLocalStorageGet('portfolio', []),
        settings: optimizedLocalStorageGet('settings', {}),
        watchlist: optimizedLocalStorageGet('watchlist', []),
        autoBuyRules: optimizedLocalStorageGet('autoBuyRules', []),
        purchaseHistory: optimizedLocalStorageGet('purchaseHistory', []),
        exportDate: new Date().toISOString(),
        version: '1.0'
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pokeagent-backup-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);

    showNotification('Data exported successfully', 'success');
}

// Import data from file
function importUserData(file) {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target.result);

            if (data.portfolio) optimizedLocalStorageSet('portfolio', data.portfolio);
            if (data.settings) {
                settings = { ...settings, ...data.settings };
                optimizedLocalStorageSet('settings', settings);
            }
            if (data.watchlist) optimizedLocalStorageSet('watchlist', data.watchlist);
            if (data.autoBuyRules) optimizedLocalStorageSet('autoBuyRules', data.autoBuyRules);
            if (data.purchaseHistory) localStorage.setItem('purchaseHistory', JSON.stringify(data.purchaseHistory));

            // Sync to server if logged in
            if (sessionToken) {
                if (data.portfolio) await syncToServer('portfolio', data.portfolio);
                if (data.settings) await syncToServer('settings', data.settings);
                if (data.watchlist) await syncToServer('watchlist', data.watchlist);
                if (data.autoBuyRules) await syncToServer('autobuy_rules', data.autoBuyRules);
            }

            // Reload UI
            loadSettings();
            renderPortfolio();
            renderAutoBuyRules();

            showNotification('Data imported successfully!', 'success');
        } catch (err) {
            console.error('Import error:', err);
            showNotification('Invalid backup file', 'error');
        }
    };
    reader.readAsText(file);
}

// Hook into existing save functions to auto-sync
const originalSaveSettings = window.saveSettings || (() => {});
window.saveSettingsWithSync = function() {
    if (typeof originalSaveSettings === 'function') originalSaveSettings();
    if (sessionToken) syncToServer('settings', settings);
};

// Delete all user data
async function deleteAllData() {
    if (!confirm('Are you sure you want to delete ALL your data? This cannot be undone!')) {
        return;
    }
    if (!confirm('This is your LAST CHANCE. All portfolio, settings, and history will be permanently deleted.')) {
        return;
    }

    // Delete from server if logged in
    if (sessionToken) {
        try {
            await fetch(`${API}/auth/delete`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${sessionToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ confirm: true })
            });
        } catch (e) {
            console.error('Delete error:', e);
        }
    }

    // Clear local storage
    localStorage.removeItem('portfolio');
    localStorage.removeItem('settings');
    localStorage.removeItem('watchlist');
    localStorage.removeItem('autoBuyRules');
    localStorage.removeItem('purchaseHistory');
    localStorage.removeItem('session_token');

    // Logout and reload
    sessionToken = null;
    currentUser = null;
    showNotification('All data deleted', 'success');
    setTimeout(() => location.reload(), 1000);
}

// Update sync status display
function updateSyncStatus() {
    const statusEl = document.getElementById('syncStatusText');
    if (!statusEl) return;

    if (sessionToken && currentUser) {
        statusEl.innerHTML = `<span style="color: var(--green);">Synced</span> as <strong>${currentUser.username}</strong> - Changes save automatically`;
    } else {
        statusEl.textContent = 'Not logged in - data stored locally only';
    }
}
