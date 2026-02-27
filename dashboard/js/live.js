// PokeAgent - Live Connection (SSE / WebSocket / Polling)

let sseRetries = 0;
const MAX_SSE_RETRIES = 3;

// Connection check
async function checkConnection() {
    try {
        const res = await fetch(`${API}/health`);
        if (res.ok) {
            document.getElementById('statusDot').classList.remove('offline');
            document.getElementById('statusText').textContent = 'Connected';
            return true;
        }
    } catch {}
    document.getElementById('statusDot').classList.add('offline');
    document.getElementById('statusText').textContent = 'Offline';
    return false;
}

// Live SSE connection (local only, Render free tier doesn't support persistent connections)
function connectLive() {
    if (API !== LOCAL_API) {
        console.log('SSE disabled on deployed version - using polling instead');
        setInterval(async () => {
            try {
                const res = await fetch(`${API}/live/history?limit=5`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.alerts && data.alerts.length > 0) {
                        const lastSeen = localStorage.getItem('lastAlertId') || '0';
                        data.alerts.forEach(alert => {
                            if (alert.id > lastSeen) {
                                showAlert(alert.data || alert);
                                localStorage.setItem('lastAlertId', alert.id);
                            }
                        });
                    }
                }
            } catch {}
        }, 30000);
        return;
    }

    if (liveConnection) liveConnection.close();

    liveConnection = new EventSource(`${API}/live/stream`);

    liveConnection.addEventListener('alert', e => {
        const data = JSON.parse(e.data);
        showAlert(data);
        sseRetries = 0;
    });

    liveConnection.addEventListener('connected', () => {
        document.getElementById('statusText').textContent = 'Live';
        sseRetries = 0;
    });

    liveConnection.onerror = () => {
        sseRetries++;
        if (sseRetries <= MAX_SSE_RETRIES) {
            document.getElementById('statusText').textContent = 'Reconnecting...';
            setTimeout(connectLive, 5000);
        } else {
            console.log('SSE connection failed, falling back to polling');
            document.getElementById('statusText').textContent = 'Connected';
            liveConnection.close();
        }
    };
}

// OpenClaw WebSocket connection (for future use)
let openclawWs = null;

function connectOpenClaw() {
    if (BACKEND_MODE !== 'openclaw') return;

    const wsUrl = OPENCLAW_GATEWAY;
    console.log('[OpenClaw] Connecting to Gateway:', wsUrl);

    openclawWs = new WebSocket(wsUrl);

    openclawWs.onopen = () => {
        console.log('[OpenClaw] Connected to Gateway');
        document.getElementById('statusDot').classList.remove('offline');
        document.getElementById('statusText').textContent = 'Live (OpenClaw)';
    };

    openclawWs.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'alert') {
                showAlert(msg.data);
            } else if (msg.type === 'notification') {
                showNotification(msg.message, msg.level || 'info');
            }
        } catch (e) {
            console.warn('[OpenClaw] Invalid message:', e);
        }
    };

    openclawWs.onclose = () => {
        console.log('[OpenClaw] Disconnected, reconnecting in 5s...');
        document.getElementById('statusText').textContent = 'Reconnecting...';
        setTimeout(connectOpenClaw, 5000);
    };

    openclawWs.onerror = (e) => {
        console.error('[OpenClaw] WebSocket error:', e);
    };
}
