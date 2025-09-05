"""
Authentication module for multi-tenant chatbot platform
"""

from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    create_company_tokens,
    create_user_tokens,
    create_guest_tokens,
    refresh_access_token,
    decode_token,
    get_current_user_info,
    is_company_token,
    is_user_token,
    is_guest_token,
    verify_password,
    get_password_hash
)

from .dependencies import (
    UserContext,
    get_current_user,
    get_current_company,
    get_current_user_or_guest,
    get_company_context,
    optional_auth,
    require_company_auth,
    require_user_auth,
    require_any_auth,
    company_required,
    user_required
)

__all__ = [
    # JWT utilities
    "create_access_token",
    "create_refresh_token", 
    "verify_token",
    "create_company_tokens",
    "create_user_tokens",
    "create_guest_tokens",
    "refresh_access_token",
    "decode_token",
    "get_current_user_info",
    "is_company_token",
    "is_user_token", 
    "is_guest_token",
    "verify_password",
    "get_password_hash",
    
    # Dependencies
    "UserContext",
    "get_current_user",
    "get_current_company",
    "get_current_user_or_guest",
    "get_company_context",
    "optional_auth",
    "require_company_auth",
    "require_user_auth",
    "require_any_auth",
    "company_required",
    "user_required"
] 