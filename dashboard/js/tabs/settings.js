// PokeAgent - Settings Tab
// =============================================================================
// Settings management: ZIP code, address, payment providers (Stripe/PayPal),
// notification/sound toggles, and live-scanner control.
//
// Global dependencies:
//   settings              - Object (persisted via optimizedLocalStorageSet)
//   API                   - String (base API URL, set from settings.api)
//   api(path, opts)       - Fetch wrapper for backend calls
//   showNotification(msg, type) - Toast notification helper
//   optimizedLocalStorageSet(key, value) - Debounced localStorage writer
// =============================================================================

function loadSettings() {
    if (settings.zip) {
        document.getElementById('settingsZip').value = settings.zip;
        document.getElementById('stockZip').value = settings.zip;
    }
    if (settings.api) {
        const apiInput = document.getElementById('settingsApi');
        if (apiInput) {
            apiInput.value = settings.api;
        }
        API = settings.api;
    } else {
        // Check localStorage for 'api' key (legacy)
        const savedApi = localStorage.getItem('api');
        if (savedApi) {
            const apiInput = document.getElementById('settingsApi');
            if (apiInput) {
                apiInput.value = savedApi;
            }
            settings.api = savedApi;
            API = savedApi;
            optimizedLocalStorageSet('settings', settings);
        }
    }
    if (settings.notif === false) document.getElementById('toggleNotif').classList.remove('active');
    if (settings.sound === false) document.getElementById('toggleSound').classList.remove('active');
    if (settings.scanner) document.getElementById('toggleScanner').classList.add('active');

    // Load address and payment on settings page load
    setTimeout(loadAddressAndPayment, 100);
}

function toggleSetting(name) {
    const toggle = document.getElementById('toggle' + name.charAt(0).toUpperCase() + name.slice(1));
    toggle.classList.toggle('active');
    settings[name] = toggle.classList.contains('active');
    optimizedLocalStorageSet('settings', settings);
}

async function toggleScanner() {
    const toggle = document.getElementById('toggleScanner');
    const active = toggle.classList.contains('active');

    if (active) {
        await api('/live/scanner/stop', { method: 'POST' });
        toggle.classList.remove('active');
    } else {
        await api('/live/scanner/start', { method: 'POST' });
        toggle.classList.add('active');
    }

    settings.scanner = !active;
    optimizedLocalStorageSet('settings', settings);
}

function saveZip() {
    settings.zip = document.getElementById('settingsZip').value;
    document.getElementById('stockZip').value = settings.zip;
    optimizedLocalStorageSet('settings', settings);
    alert('ZIP code saved');
}

function saveAddress() {
    settings.address = {
        name: document.getElementById('settingsName').value,
        address1: document.getElementById('settingsAddress1').value,
        address2: document.getElementById('settingsAddress2').value,
        city: document.getElementById('settingsCity').value,
        state: document.getElementById('settingsState').value,
        zip: document.getElementById('settingsZipShip').value,
        phone: document.getElementById('settingsPhone').value,
    };
    optimizedLocalStorageSet('settings', settings);
    alert('Address saved');
}

function savePayment() {
    // Redirect to Stripe/PayPal - no longer storing card info directly
    showNotification('Please use Stripe or PayPal to securely add a payment method', 'info');
}

function clearPayment() {
    disconnectStripe();
    disconnectPaypal();
}

// =============================================================================
// STRIPE & PAYPAL SECURE PAYMENT INTEGRATION
// =============================================================================

function connectStripe() {
    // Demo mode - in production, this would use Stripe Checkout
    showNotification('Stripe connection demo - configure keys for live payments', 'info');

    // Simulate successful card addition
    const demoCard = {
        provider: 'stripe',
        last4: '4242',
        brand: 'visa',
        expMonth: 12,
        expYear: 2028,
        connectedAt: new Date().toISOString()
    };

    settings.stripePayment = demoCard;
    optimizedLocalStorageSet('settings', settings);

    updatePaymentDisplay();
    showNotification('Card connected via Stripe', 'success');
}

function disconnectStripe() {
    if (confirm('Remove this card from your account?')) {
        delete settings.stripePayment;
        optimizedLocalStorageSet('settings', settings);
        updatePaymentDisplay();
        showNotification('Stripe card removed', 'success');
    }
}

function connectPaypal() {
    // Demo mode - in production, this would use PayPal OAuth
    const email = prompt('Enter your PayPal email:');
    if (email && email.includes('@')) {
        settings.paypalPayment = {
            provider: 'paypal',
            email: email,
            connectedAt: new Date().toISOString()
        };

        optimizedLocalStorageSet('settings', settings);
        updatePaymentDisplay();
        showNotification('PayPal connected', 'success');
    }
}

function disconnectPaypal() {
    if (confirm('Disconnect PayPal from your account?')) {
        delete settings.paypalPayment;
        optimizedLocalStorageSet('settings', settings);
        updatePaymentDisplay();
        showNotification('PayPal disconnected', 'success');
    }
}

function updatePaymentDisplay() {
    // Stripe
    const stripeEl = document.getElementById('stripeConnected');
    const stripeBtn = document.getElementById('addStripeBtn');
    if (stripeEl && settings.stripePayment) {
        stripeEl.style.display = 'block';
        if (stripeBtn) stripeBtn.style.display = 'none';
        const display = document.getElementById('stripeCardDisplay');
        if (display) display.textContent = `${(settings.stripePayment.brand || 'Card').toUpperCase()} •••• ${settings.stripePayment.last4}`;
    } else if (stripeEl) {
        stripeEl.style.display = 'none';
        if (stripeBtn) stripeBtn.style.display = 'flex';
    }

    // PayPal
    const paypalEl = document.getElementById('paypalConnected');
    const paypalBtn = document.getElementById('addPaypalBtn');
    if (paypalEl && settings.paypalPayment) {
        paypalEl.style.display = 'block';
        if (paypalBtn) paypalBtn.style.display = 'none';
        const display = document.getElementById('paypalEmailDisplay');
        if (display) display.textContent = settings.paypalPayment.email;
    } else if (paypalEl) {
        paypalEl.style.display = 'none';
        if (paypalBtn) paypalBtn.style.display = 'flex';
    }
}

function loadAddressAndPayment() {
    if (settings.address) {
        document.getElementById('settingsName').value = settings.address.name || '';
        document.getElementById('settingsAddress1').value = settings.address.address1 || '';
        document.getElementById('settingsAddress2').value = settings.address.address2 || '';
        document.getElementById('settingsCity').value = settings.address.city || '';
        document.getElementById('settingsState').value = settings.address.state || '';
        document.getElementById('settingsZipShip').value = settings.address.zip || '';
        document.getElementById('settingsPhone').value = settings.address.phone || '';
    }
    // Load Stripe & PayPal connected status
    updatePaymentDisplay();
}
