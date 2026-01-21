"""
Authentication Module
=====================
Secure Discord OAuth2 authentication for PokeAgent.
"""

from .discord_oauth import (
    # OAuth flow
    get_discord_auth_url,
    exchange_code_for_token,
    get_discord_user,
    verify_oauth_state,
    
    # User management
    get_or_create_user,
    
    # Session management
    create_session,
    validate_session,
    invalidate_session,
    invalidate_all_sessions,
    
    # User data (encrypted)
    save_user_data,
    get_user_data,
    get_all_user_data,
    delete_user_data,
    
    # Security utilities
    check_rate_limit,
    sanitize_input,
    log_audit,
    
    # Decorators
    require_auth,
    optional_auth,
)

__all__ = [
    'get_discord_auth_url',
    'exchange_code_for_token',
    'get_discord_user',
    'verify_oauth_state',
    'get_or_create_user',
    'create_session',
    'validate_session',
    'invalidate_session',
    'invalidate_all_sessions',
    'save_user_data',
    'get_user_data',
    'get_all_user_data',
    'delete_user_data',
    'check_rate_limit',
    'sanitize_input',
    'log_audit',
    'require_auth',
    'optional_auth',
]
