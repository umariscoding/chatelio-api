"""
User management endpoints for the hybrid model (guest sessions + registered users)
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any, Optional
from app.models.models import UserRegisterModel, GuestSessionModel
from app.auth import create_user_tokens, create_guest_tokens
from app.auth.dependencies import get_current_user, get_current_user_or_guest, UserContext
from app.db.database import (
    create_company, get_company_by_id, create_user, create_guest_session, 
    get_user_by_id, get_guest_session, mark_guest_converted
)

router = APIRouter(prefix="/users", tags=["user-management"])

@router.post("/guest/create")
async def create_guest_session_endpoint(
    guest_data: GuestSessionModel,
    request: Request
) -> Dict[str, Any]:
    """
    Create a new guest session for anonymous users.
    
    Args:
        guest_data: Guest session data including company_id
        request: FastAPI request object to extract IP/user agent
        
    Returns:
        Dict containing guest session info and tokens
        
    Raises:
        HTTPException: If company not found or session creation fails
    """
    try:
        # Verify company exists
        company = await get_company_by_id(guest_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Extract IP and user agent from request
        ip_address = guest_data.ip_address or (request.client.host if request.client else "unknown")
        user_agent = guest_data.user_agent or request.headers.get("user-agent", "")
        
        # Create guest session
        session = await create_guest_session(
            company_id=guest_data.company_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Generate tokens
        tokens = create_guest_tokens(
            session_id=session["session_id"],
            company_id=guest_data.company_id
        )
        
        return {
            "message": "Guest session created successfully",
            "session": {
                "session_id": session["session_id"],
                "company_id": session["company_id"],
                "expires_at": session["expires_at"]
            },
            "tokens": tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create guest session: {str(e)}"
        )

@router.post("/register")
async def register_user(user_data: UserRegisterModel) -> Dict[str, Any]:
    """
    Register a new user for a company.
    
    Args:
        user_data: User registration information
        
    Returns:
        Dict containing user info and authentication tokens
        
    Raises:
        HTTPException: If company not found or registration fails
    """
    try:
        # Verify company exists
        company = await get_company_by_id(user_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Create user account
        user = await create_user(
            company_id=user_data.company_id,
            email=user_data.email,
            name=user_data.name
        )
        
        # Generate authentication tokens
        tokens = create_user_tokens(
            user_id=user["user_id"],
            company_id=user["company_id"],
            email=user["email"]
        )
        
        return {
            "message": "User registered successfully",
            "user": {
                "user_id": user["user_id"],
                "company_id": user["company_id"],
                "email": user["email"],
                "name": user["name"],
                "is_anonymous": user["is_anonymous"]
            },
            "tokens": tokens
        }
        
    except ValueError as e:
        # Handle duplicate email error
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists in this company"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.post("/convert-guest-to-user")
async def convert_guest_to_user(
    user_data: UserRegisterModel,
    current_user: UserContext = Depends(get_current_user_or_guest)
) -> Dict[str, Any]:
    """
    Convert a guest session to a registered user account.
    This is for the progressive enhancement flow where guests decide to save their chat.
    
    Args:
        user_data: User registration information
        current_user: Current guest user context
        
    Returns:
        Dict containing new user info and tokens
        
    Raises:
        HTTPException: If user is not a guest or conversion fails
    """
    try:
        if not current_user.is_guest():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only guest users can be converted to registered users"
            )
        
        # Verify company matches
        if current_user.company_id != user_data.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company ID mismatch"
            )
        
        # Check if guest session is still valid (not already converted)
        guest_session = await get_guest_session(current_user.user_id)
        if not guest_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest session has expired or already been converted"
            )
        
        # Create registered user account
        user = await create_user(
            company_id=user_data.company_id,
            email=user_data.email,
            name=user_data.name
        )
        
        # Mark the guest session as converted to prevent duplicate conversions
        await mark_guest_converted(current_user.user_id)
        
        # Generate new tokens for the registered user
        tokens = create_user_tokens(
            user_id=user["user_id"],
            company_id=user["company_id"],
            email=user["email"]
        )
        
        # Note: In a production system, you might want to:
        # 1. Transfer chat history from guest session to user account
        # 2. Update existing chats to link to the new user account
        
        return {
            "message": "Guest converted to registered user successfully",
            "user": {
                "user_id": user["user_id"],
                "company_id": user["company_id"],
                "email": user["email"],
                "name": user["name"],
                "is_anonymous": user["is_anonymous"]
            },
            "tokens": tokens,
            "conversion": {
                "from_session_id": current_user.user_id,
                "to_user_id": user["user_id"]
            }
        }
        
    except ValueError as e:
        # Handle duplicate email error from create_user
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists in this company"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Guest conversion failed: {str(e)}"
        )

@router.get("/profile")
async def get_user_profile(current_user: UserContext = Depends(get_current_user_or_guest)) -> Dict[str, Any]:
    """
    Get the current user's profile (works for both guests and registered users).
    
    Args:
        current_user: Current user context
        
    Returns:
        Dict containing user profile information
    """
    try:
        if current_user.is_guest():
            # Get guest session info
            session = await get_guest_session(current_user.user_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Guest session not found or expired"
                )
            
            return {
                "profile": {
                    "session_id": session["session_id"],
                    "company_id": session["company_id"],
                    "user_type": "guest",
                    "expires_at": session["expires_at"]
                }
            }
        else:
            # Get registered user info
            user = await get_user_by_id(current_user.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "profile": {
                    "user_id": user["user_id"],
                    "company_id": user["company_id"],
                    "email": user["email"],
                    "name": user["name"],
                    "user_type": "user",
                    "is_anonymous": user["is_anonymous"]
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )

@router.get("/session/check")
async def check_session_validity(current_user: UserContext = Depends(get_current_user_or_guest)) -> Dict[str, Any]:
    """
    Check if the current session/user is still valid.
    Useful for frontend to verify tokens and session state.
    
    Args:
        current_user: Current user context
        
    Returns:
        Dict containing session validity and user info
    """
    try:
        return {
            "valid": True,
            "user_info": {
                "user_id": current_user.user_id,
                "company_id": current_user.company_id,
                "email": current_user.email,
                "user_type": current_user.user_type
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session check failed: {str(e)}"
        )

@router.get("/company/{company_id}/info")
async def get_company_info(company_id: str) -> Dict[str, Any]:
    """
    Get public company information (for guest users to see company details).
    
    Args:
        company_id: Company identifier
        
    Returns:
        Dict containing public company information
    """
    try:
        company = await get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Return only public information
        return {
            "company": {
                "company_id": company["company_id"],
                "name": company["name"],
                "status": company["status"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company info: {str(e)}"
        )

# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for user management service.
    
    Returns:
        Dict containing health status
    """
    return {
        "status": "healthy",
        "service": "user-management"
    } 