"""
Secure Discord OAuth2 Authentication Module
============================================
Implements secure Discord login with:
- OAuth2 authorization code flow
- Secure token handling
- Encrypted session management
- CSRF protection
"""

import os
import secrets
import hashlib
import hmac
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import requests
from functools import wraps

# Cryptography for encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Data will not be encrypted.")

# =============================================================================
# CONFIGURATION
# =============================================================================

DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '')
DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', 'https://pokemon-multi-agent.onrender.com/auth/discord/callback')

# Security settings
SESSION_EXPIRY_HOURS = 24 * 7  # 7 days
TOKEN_BYTES = 32  # 256-bit tokens
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '')

# Discord OAuth URLs
DISCORD_AUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_USER_URL = 'https://discord.com/api/users/@me'

# Database
AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'users.db')


# =============================================================================
# ENCRYPTION
# =============================================================================

def get_encryption_key() -> Optional[bytes]:
    """Derive encryption key from environment variable."""
    if not CRYPTO_AVAILABLE:
        return None
    
    key_material = ENCRYPTION_KEY or 'default-dev-key-change-in-production'
    
    # Use PBKDF2 to derive a proper key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'pokeagent-salt-v1',  # Fixed salt for deterministic key
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_material.encode()))
    return key


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    key = get_encryption_key()
    if not key or not CRYPTO_AVAILABLE:
        return data  # Return as-is if no encryption
    
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted: str) -> str:
    """Decrypt sensitive data."""
    key = get_encryption_key()
    if not key or not CRYPTO_AVAILABLE:
        return encrypted
    
    try:
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # Return as-is if decryption fails


# =============================================================================
# DATABASE
# =============================================================================

def init_auth_db():
    """Initialize the authentication database with secure schema."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT UNIQUE NOT NULL,
            discord_username TEXT,
            discord_avatar TEXT,
            discord_email_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Sessions table (secure token storage)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token_hash TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_valid BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # User data table (encrypted portfolio, settings)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            portfolio_encrypted TEXT,
            settings_encrypted TEXT,
            watchlist_encrypted TEXT,
            autobuy_rules_encrypted TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # OAuth states (CSRF protection)
    c.execute('''
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0
        )
    ''')
    
    # Rate limiting
    c.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Audit log
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token_hash)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_rate_limits_ip ON rate_limits(ip_address, endpoint)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_oauth_states ON oauth_states(state)')
    
    conn.commit()
    conn.close()


# Initialize DB on module load
init_auth_db()


# =============================================================================
# SECURITY UTILITIES
# =============================================================================

def generate_secure_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_email(email: str) -> str:
    """Hash email for privacy (we don't store actual emails)."""
    return hashlib.sha256(email.lower().encode()).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    """Securely compare token hash."""
    return hmac.compare_digest(hash_token(token), stored_hash)


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not isinstance(value, str):
        return ''
    # Remove null bytes and limit length
    value = value.replace('\x00', '')[:max_length]
    return value


def log_audit(user_id: Optional[int], action: str, details: str = '', ip: str = ''):
    """Log security-relevant actions."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT INTO audit_log (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
        (user_id, action, details[:500], ip[:45])
    )
    conn.commit()
    conn.close()


# =============================================================================
# RATE LIMITING
# =============================================================================

def check_rate_limit(ip: str, endpoint: str, max_requests: int = 30, window_seconds: int = 60) -> bool:
    """
    Check if request is within rate limits.
    Returns True if allowed, False if rate limited.
    """
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Clean old entries
    cutoff = datetime.now() - timedelta(seconds=window_seconds)
    c.execute(
        'DELETE FROM rate_limits WHERE timestamp < ?',
        (cutoff,)
    )
    
    # Count recent requests
    c.execute(
        'SELECT COUNT(*) FROM rate_limits WHERE ip_address = ? AND endpoint = ? AND timestamp > ?',
        (ip[:45], endpoint[:100], cutoff)
    )
    count = c.fetchone()[0]
    
    if count >= max_requests:
        conn.close()
        return False
    
    # Log this request
    c.execute(
        'INSERT INTO rate_limits (ip_address, endpoint) VALUES (?, ?)',
        (ip[:45], endpoint[:100])
    )
    conn.commit()
    conn.close()
    return True


# =============================================================================
# OAUTH FLOW
# =============================================================================

def generate_oauth_state() -> str:
    """Generate and store a CSRF-protection state token."""
    state = generate_secure_token()
    expires_at = datetime.now() + timedelta(minutes=10)
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Clean expired states
    c.execute('DELETE FROM oauth_states WHERE expires_at < ?', (datetime.now(),))
    
    # Store new state
    c.execute(
        'INSERT INTO oauth_states (state, expires_at) VALUES (?, ?)',
        (state, expires_at)
    )
    conn.commit()
    conn.close()
    
    return state


def verify_oauth_state(state: str) -> bool:
    """Verify and consume an OAuth state token."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    c.execute(
        'SELECT state FROM oauth_states WHERE state = ? AND expires_at > ? AND used = 0',
        (state, datetime.now())
    )
    result = c.fetchone()
    
    if result:
        # Mark as used (one-time use)
        c.execute('UPDATE oauth_states SET used = 1 WHERE state = ?', (state,))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False


def get_discord_auth_url() -> Dict[str, str]:
    """Generate Discord OAuth authorization URL with CSRF protection."""
    if not DISCORD_CLIENT_ID:
        return {'error': 'Discord OAuth not configured'}
    
    state = generate_oauth_state()
    
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify',  # Minimal scope - only get user ID and username
        'state': state,
        'prompt': 'consent'
    }
    
    url = f"{DISCORD_AUTH_URL}?{urlencode(params)}"
    return {'url': url, 'state': state}


def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """Exchange authorization code for access token."""
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return None
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Token exchange error: {e}")
        return None


def get_discord_user(access_token: str) -> Optional[Dict[str, Any]]:
    """Get user info from Discord API."""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(DISCORD_USER_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Discord user fetch error: {e}")
        return None


# =============================================================================
# USER & SESSION MANAGEMENT
# =============================================================================

def get_or_create_user(discord_user: Dict[str, Any]) -> Optional[int]:
    """Get or create user from Discord data. Returns user_id."""
    discord_id = str(discord_user.get('id', ''))
    username = sanitize_input(discord_user.get('username', ''))
    avatar = sanitize_input(discord_user.get('avatar', '') or '')
    email = discord_user.get('email', '')
    email_hash = hash_email(email) if email else None
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Try to find existing user
    c.execute('SELECT id FROM users WHERE discord_id = ?', (discord_id,))
    result = c.fetchone()
    
    if result:
        user_id = result[0]
        # Update last login and info
        c.execute(
            'UPDATE users SET last_login = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
            (datetime.now(), username, avatar, user_id)
        )
    else:
        # Create new user
        c.execute(
            'INSERT INTO users (discord_id, discord_username, discord_avatar, discord_email_hash, last_login) VALUES (?, ?, ?, ?, ?)',
            (discord_id, username, avatar, email_hash, datetime.now())
        )
        user_id = c.lastrowid
        
        # Create empty user_data entry
        c.execute(
            'INSERT INTO user_data (user_id) VALUES (?)',
            (user_id,)
        )
    
    conn.commit()
    conn.close()
    return user_id


def create_session(user_id: int, ip: str = '', user_agent: str = '') -> str:
    """Create a new session and return the session token."""
    token = generate_secure_token()
    token_hash = hash_token(token)
    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Invalidate old sessions for this user (limit to 5 active sessions)
    c.execute(
        '''DELETE FROM sessions WHERE user_id = ? AND id NOT IN 
           (SELECT id FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 4)''',
        (user_id, user_id)
    )
    
    # Create new session
    c.execute(
        'INSERT INTO sessions (user_id, session_token_hash, expires_at, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)',
        (user_id, token_hash, expires_at, ip[:45], user_agent[:500])
    )
    
    conn.commit()
    conn.close()
    
    return token


def validate_session(token: str) -> Optional[Dict[str, Any]]:
    """Validate a session token and return user info if valid."""
    if not token:
        return None
    
    token_hash = hash_token(token)
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT u.id, u.discord_id, u.discord_username, u.discord_avatar, s.expires_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token_hash = ? AND s.is_valid = 1 AND s.expires_at > ? AND u.is_active = 1
    ''', (token_hash, datetime.now()))
    
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'user_id': result[0],
            'discord_id': result[1],
            'username': result[2],
            'avatar': result[3],
            'expires_at': result[4]
        }
    return None


def invalidate_session(token: str) -> bool:
    """Invalidate a session (logout)."""
    token_hash = hash_token(token)
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE sessions SET is_valid = 0 WHERE session_token_hash = ?', (token_hash,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def invalidate_all_sessions(user_id: int) -> int:
    """Invalidate all sessions for a user (logout everywhere)."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE sessions SET is_valid = 0 WHERE user_id = ?', (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected


# =============================================================================
# USER DATA (ENCRYPTED)
# =============================================================================

def save_user_data(user_id: int, data_type: str, data: Any) -> bool:
    """Save encrypted user data."""
    if data_type not in ['portfolio', 'settings', 'watchlist', 'autobuy_rules']:
        return False
    
    encrypted = encrypt_data(json.dumps(data))
    column = f"{data_type}_encrypted"
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    c.execute(
        f'UPDATE user_data SET {column} = ?, updated_at = ? WHERE user_id = ?',
        (encrypted, datetime.now(), user_id)
    )
    
    conn.commit()
    conn.close()
    return True


def get_user_data(user_id: int, data_type: str) -> Any:
    """Get decrypted user data."""
    if data_type not in ['portfolio', 'settings', 'watchlist', 'autobuy_rules']:
        return None
    
    column = f"{data_type}_encrypted"
    
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    c.execute(f'SELECT {column} FROM user_data WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        try:
            decrypted = decrypt_data(result[0])
            return json.loads(decrypted)
        except Exception:
            return None
    return None


def get_all_user_data(user_id: int) -> Dict[str, Any]:
    """Get all user data at once (for sync)."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    c.execute(
        'SELECT portfolio_encrypted, settings_encrypted, watchlist_encrypted, autobuy_rules_encrypted FROM user_data WHERE user_id = ?',
        (user_id,)
    )
    result = c.fetchone()
    conn.close()
    
    if not result:
        return {}
    
    data = {}
    columns = ['portfolio', 'settings', 'watchlist', 'autobuy_rules']
    
    for i, col in enumerate(columns):
        if result[i]:
            try:
                data[col] = json.loads(decrypt_data(result[i]))
            except Exception:
                data[col] = None
        else:
            data[col] = None
    
    return data


def delete_user_data(user_id: int) -> bool:
    """Delete all user data (GDPR compliance)."""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Delete user data
    c.execute('DELETE FROM user_data WHERE user_id = ?', (user_id,))
    
    # Invalidate all sessions
    c.execute('UPDATE sessions SET is_valid = 0 WHERE user_id = ?', (user_id,))
    
    # Mark user as inactive (soft delete)
    c.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
    
    # Log deletion
    log_audit(user_id, 'USER_DATA_DELETED', 'User requested data deletion')
    
    conn.commit()
    conn.close()
    return True


# =============================================================================
# FLASK DECORATOR FOR AUTH
# =============================================================================

def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            token = request.cookies.get('session_token', '')
        
        user = validate_session(token)
        if not user:
            return jsonify({'error': 'Unauthorized', 'code': 'AUTH_REQUIRED'}), 401
        
        # Add user to request context
        request.user = user
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """Decorator for routes that optionally use authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            token = request.cookies.get('session_token', '')
        
        request.user = validate_session(token)
        return f(*args, **kwargs)
    
    return decorated_function
