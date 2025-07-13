"""
Authentication endpoints for company management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any
from app.models.models import CompanyRegisterModel, CompanyLoginModel
from app.auth import (
    create_company_tokens, verify_password, get_password_hash,
    refresh_access_token, get_current_user_info
)
from app.auth.dependencies import get_current_company, UserContext
from app.db.database import (
    create_company, authenticate_company, get_company_by_id
)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

class RefreshTokenModel(BaseModel):
    refresh_token: str

@router.post("/company/register")
async def register_company(company_data: CompanyRegisterModel) -> Dict[str, Any]:
    """
    Register a new company account.
    
    Args:
        company_data: Company registration information
        
    Returns:
        Dict containing company info and authentication tokens
        
    Raises:
        HTTPException: If company already exists or registration fails
    """
    try:
        # Create company account
        company = await create_company(
            name=company_data.name,
            email=company_data.email,
            password=company_data.password
        )
        
        # Generate authentication tokens
        tokens = create_company_tokens(
            company_id=company["company_id"],
            email=company["email"]
        )
        
        return {
            "message": "Company registered successfully",
            "company": {
                "company_id": company["company_id"],
                "name": company["name"],
                "email": company["email"],
                "plan": company["plan"],
                "status": company["status"]
            },
            "tokens": tokens
        }
        
    except ValueError as e:
        # Company already exists
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Other registration errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/company/login")
async def login_company(login_data: CompanyLoginModel) -> Dict[str, Any]:
    """
    Authenticate a company and return tokens.
    
    Args:
        login_data: Company login credentials
        
    Returns:
        Dict containing company info and authentication tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Authenticate company
        company = await authenticate_company(
            email=login_data.email,
            password=login_data.password
        )
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate authentication tokens
        tokens = create_company_tokens(
            company_id=company["company_id"],
            email=company["email"]
        )
        
        return {
            "message": "Login successful",
            "company": company,
            "tokens": tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/company/profile")
async def get_company_profile(current_company: UserContext = Depends(get_current_company)) -> Dict[str, Any]:
    """
    Get the authenticated company's profile information.
    
    Args:
        current_company: Authenticated company context
        
    Returns:
        Dict containing company profile information
    """
    try:
        company = await get_company_by_id(current_company.company_id)
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        return {
            "company": company
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )

@router.post("/refresh")
async def refresh_tokens(refresh_data: RefreshTokenModel) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Request body containing refresh token
        
    Returns:
        Dict containing new access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        refresh_token = refresh_data.refresh_token
        
        # Generate new access token
        new_access_token = refresh_access_token(refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # JWT signature verification failures should return 401, not 500
        error_message = str(e)
        if "signature" in error_message.lower() or "invalid" in error_message.lower() or "decode" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token refresh failed: {error_message}"
            )

@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        credentials: HTTP Bearer token
        
    Returns:
        Dict containing user information from token
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        token = credentials.credentials
        
        # Get user info from token
        user_info = get_current_user_info(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            "valid": True,
            "user_info": user_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # JWT signature verification failures should return 401, not 500
        error_message = str(e)
        if "signature" in error_message.lower() or "invalid" in error_message.lower() or "decode" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token verification failed: {error_message}"
            )

@router.post("/company/logout")
async def logout_company(current_company: UserContext = Depends(get_current_company)) -> Dict[str, Any]:
    """
    Logout a company (client-side token invalidation).
    
    Args:
        current_company: Authenticated company context
        
    Returns:
        Dict containing logout confirmation
    """
    # Note: JWT tokens are stateless, so logout is primarily client-side
    # In a production system, you might want to implement token blacklisting
    
    return {
        "message": "Logout successful",
        "company_id": current_company.company_id
    }

# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for authentication service.
    
    Returns:
        Dict containing health status
    """
    return {
        "status": "healthy",
        "service": "authentication"
    } 