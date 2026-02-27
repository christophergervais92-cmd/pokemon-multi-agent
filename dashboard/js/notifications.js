// PokeAgent - Alerts & Notifications

function showAlert(data) {
    const container = document.getElementById('alertsContainer');
    const alert = document.createElement('div');
    alert.className = 'alert';
    const buyUrl = data.url || getBuyUrl(data.retailer, data.product_name, '');
    alert.innerHTML = `
        <div class="alert-title">${escapeHtml(data.product_name || 'Deal Found')}</div>
        <div class="alert-body">
            ${escapeHtml(data.retailer || '')} - $${data.price || '??'}
            <br><a href="${buyUrl}" target="_blank" style="color: var(--green);">Buy Now &#8594;</a>
        </div>
    `;
    container.prepend(alert);

    setTimeout(() => alert.remove(), 10000);

    // Desktop notification
    if (settings.notif !== false && Notification.permission === 'granted') {
        new Notification('Deal Alert', { body: `${data.product_name} - $${data.price}` });
    }

    // Sound
    if (settings.sound !== false) playSound();
}

function playSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        gain.gain.value = 0.1;
        osc.start();
        osc.stop(ctx.currentTime + 0.1);
    } catch {}
}
