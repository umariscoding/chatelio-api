from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, func
import time

from app.auth.dependencies import get_current_company, UserContext
from app.db.database import SessionLocal
from app.models.models import (
    Company, CompanyUser, GuestSession, Chat, Message, 
    KnowledgeBase, Document
)

router = APIRouter(prefix="/api/company/analytics", tags=["analytics"])

# Pydantic models for response structure
class ChangeIndicator(BaseModel):
    value: str  # e.g., "+15%" or "-5%"
    type: str   # "increase", "decrease", or "neutral"

class OverviewCard(BaseModel):
    count: int
    change: ChangeIndicator

class MessagesTimePoint(BaseModel):
    date: str
    totalMessages: int

class ChatsTimePoint(BaseModel):
    date: str
    newChats: int

# Simplified analytics - removed unnecessary models

class UserWithStats(BaseModel):
    user_id: str
    email: Optional[str]
    name: Optional[str]
    is_anonymous: bool
    chat_count: int
    message_count: int
    created_at: str

class CompanyUsersResponse(BaseModel):
    users: List[UserWithStats]
    total_users: int
    total_chats: int
    total_messages: int
    company_id: str

class OverviewStats(BaseModel):
    totalMessages: OverviewCard
    users: OverviewCard
    totalChats: OverviewCard
    knowledgeBases: OverviewCard
    guestSessions: OverviewCard

class TimeSeries(BaseModel):
    messagesOverTime: List[MessagesTimePoint]
    chatsOverTime: List[ChatsTimePoint]

class AnalyticsMetadata(BaseModel):
    lastUpdated: str
    queryExecutionTime: float
    companyId: str

class AnalyticsDashboard(BaseModel):
    overview: OverviewStats
    timeSeries: TimeSeries
    metadata: AnalyticsMetadata

def get_company_timezone(company_id: str) -> timezone:
    """
    Get the timezone for a company. 
    For now returns UTC, but can be extended to fetch from company settings.
    
    Args:
        company_id: Company identifier
        
    Returns:
        timezone: Company's timezone (currently always UTC)
    """
    # TODO: Fetch company timezone from database settings
    # For now, default to UTC for all companies
    return timezone.utc

def calculate_change(current: int, previous: int) -> ChangeIndicator:
    """Calculate percentage change between current and previous periods."""
    if previous == 0:
        if current == 0:
            return ChangeIndicator(value="0%", type="neutral")
        else:
            return ChangeIndicator(value="+100%", type="increase")
    
    change_percent = ((current - previous) / previous) * 100
    
    if change_percent > 0:
        return ChangeIndicator(value=f"+{change_percent:.1f}%", type="increase")
    elif change_percent < 0:
        return ChangeIndicator(value=f"{change_percent:.1f}%", type="decrease")
    else:
        return ChangeIndicator(value="0%", type="neutral")

@router.get("/dashboard")
async def get_dashboard_analytics(
    user: UserContext = Depends(get_current_company)
) -> AnalyticsDashboard:
    """
    Get comprehensive dashboard analytics for the company.
    Returns overview statistics, time series data, user analytics, and knowledge base metrics.
    """
    start_time = time.time()
    
    db = SessionLocal()
    try:
        company_id = user.company_id
        
        # Define time periods with proper timezone handling
        tz = get_company_timezone(company_id)
        
        # Get current time in the company's timezone
        now = datetime.now(tz)
        
        # Calculate time periods relative to the target timezone
        last_30_days = now - timedelta(days=30)
        last_60_days = now - timedelta(days=60)
        last_7_days = now - timedelta(days=7)
        last_14_days = now - timedelta(days=14)
        
        # ============================================================================
        # OVERVIEW STATISTICS
        # ============================================================================
        
        # Total messages (last 7 days vs previous 7 days)
        current_messages = db.query(func.count(Message.id)).filter(
            Message.company_id == company_id,
            Message.created_at >= last_7_days
        ).scalar() or 0
        
        previous_messages = db.query(func.count(Message.id)).filter(
            Message.company_id == company_id,
            Message.created_at >= last_14_days,
            Message.created_at < last_7_days
        ).scalar() or 0
        
        # Users registered in last 7 days vs previous 7 days
        current_users = db.query(func.count(CompanyUser.id)).filter(
            CompanyUser.company_id == company_id,
            CompanyUser.created_at >= last_7_days
        ).scalar() or 0
        
        # Previous period users (users registered 7-14 days ago)
        previous_users = db.query(func.count(CompanyUser.id)).filter(
            CompanyUser.company_id == company_id,
            CompanyUser.created_at >= last_14_days,
            CompanyUser.created_at < last_7_days
        ).scalar() or 0
        
        # Total chats (last 7 days vs previous 7 days)
        current_chats = db.query(func.count(Chat.id)).filter(
            Chat.company_id == company_id,
            Chat.created_at >= last_7_days,
            Chat.is_deleted == False
        ).scalar() or 0
        
        previous_chats = db.query(func.count(Chat.id)).filter(
            Chat.company_id == company_id,
            Chat.created_at >= last_14_days,
            Chat.created_at < last_7_days,
            Chat.is_deleted == False
        ).scalar() or 0
        
        # Knowledge bases (last 7 days vs previous 7 days)
        current_kb = db.query(func.count(KnowledgeBase.id)).filter(
            KnowledgeBase.company_id == company_id,
            KnowledgeBase.created_at >= last_7_days
        ).scalar() or 0
        
        previous_kb = db.query(func.count(KnowledgeBase.id)).filter(
            KnowledgeBase.company_id == company_id,
            KnowledgeBase.created_at >= last_14_days,
            KnowledgeBase.created_at < last_7_days
        ).scalar() or 0
        
        # Guest sessions created in last 7 days vs previous 7 days
        current_guest_sessions = db.query(func.count(GuestSession.id)).filter(
            GuestSession.company_id == company_id,
            GuestSession.created_at >= last_7_days
        ).scalar() or 0
        
        # Previous period guest sessions (created 7-14 days ago)
        previous_guest_sessions = db.query(func.count(GuestSession.id)).filter(
            GuestSession.company_id == company_id,
            GuestSession.created_at >= last_14_days,
            GuestSession.created_at < last_7_days
        ).scalar() or 0
        
        overview = OverviewStats(
            totalMessages=OverviewCard(
                count=current_messages,
                change=calculate_change(current_messages, previous_messages)
            ),
            users=OverviewCard(
                count=current_users,
                change=calculate_change(current_users, previous_users)
            ),
            totalChats=OverviewCard(
                count=current_chats,
                change=calculate_change(current_chats, previous_chats)
            ),
            knowledgeBases=OverviewCard(
                count=current_kb,
                change=calculate_change(current_kb, previous_kb)
            ),
            guestSessions=OverviewCard(
                count=current_guest_sessions,
                change=calculate_change(current_guest_sessions, previous_guest_sessions)
            )
        )
        
        # ============================================================================
        # TIME SERIES DATA
        # ============================================================================
        
        # Daily message counts for last 7 days
        messages_over_time = []
        for i in range(7):
            # Calculate day boundaries in the target timezone
            target_date = now.date() - timedelta(days=i)
            # Create timezone-aware datetime for start of day
            day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
            day_end = day_start + timedelta(days=1)
            day_date = target_date.strftime("%Y-%m-%d")
            
            # Total messages (all types)
            # Note: Assuming database stores timestamps in UTC
            total_msgs = db.query(func.count(Message.id)).filter(
                Message.company_id == company_id,
                Message.created_at >= day_start,
                Message.created_at < day_end
            ).scalar() or 0
            
            messages_over_time.append(MessagesTimePoint(
                date=day_date,
                totalMessages=total_msgs
            ))
        
        messages_over_time.reverse()  # Chronological order
        
        # Daily new chat creation for last 7 days
        chats_over_time = []
        for i in range(7):
            # Calculate day boundaries in the target timezone
            target_date = now.date() - timedelta(days=i)
            # Create timezone-aware datetime for start of day
            day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
            day_end = day_start + timedelta(days=1)
            day_date = target_date.strftime("%Y-%m-%d")
            
            new_chats = db.query(func.count(Chat.id)).filter(
                Chat.company_id == company_id,
                Chat.created_at >= day_start,
                Chat.created_at < day_end,
                Chat.is_deleted == False
            ).scalar() or 0
            
            chats_over_time.append(ChatsTimePoint(
                date=day_date,
                newChats=new_chats
            ))
        
        chats_over_time.reverse()  # Chronological order
        
        time_series = TimeSeries(
            messagesOverTime=messages_over_time,
            chatsOverTime=chats_over_time
        )
        
        # Simplified analytics - only high-level overview and time series
        
        # ============================================================================
        # METADATA
        # ============================================================================
        
        query_time = time.time() - start_time
        metadata = AnalyticsMetadata(
            lastUpdated=now.isoformat(),
            queryExecutionTime=round(query_time, 3),
            companyId=company_id
        )
        
        return AnalyticsDashboard(
            overview=overview,
            timeSeries=time_series,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch analytics data: {str(e)}"
        )
    finally:
        db.close()

@router.get("/users")
async def get_company_users_with_stats(
    user: UserContext = Depends(get_current_company)
) -> CompanyUsersResponse:
    """
    Get all users for the company along with their chat and message counts.
    Returns detailed user statistics including number of chats and messages per user.
    """
    start_time = time.time()
    
    db = SessionLocal()
    try:
        company_id = user.company_id
        
        # Get all users for the company with their stats
        users_query = db.query(
            CompanyUser.user_id,
            CompanyUser.email,
            CompanyUser.name,
            CompanyUser.is_anonymous,
            CompanyUser.created_at,
            func.count(func.distinct(Chat.chat_id)).label('chat_count'),
            func.count(Message.id).label('message_count')
        ).outerjoin(
            Chat, (Chat.user_id == CompanyUser.user_id) & (Chat.is_deleted == False)
        ).outerjoin(
            Message, Message.chat_id == Chat.chat_id
        ).filter(
            CompanyUser.company_id == company_id
        ).group_by(
            CompanyUser.user_id,
            CompanyUser.email,
            CompanyUser.name,
            CompanyUser.is_anonymous,
            CompanyUser.created_at
        ).order_by(
            CompanyUser.created_at.desc()
        ).all()
        
        # Format user data
        users_with_stats = []
        for user_data in users_query:
            users_with_stats.append(UserWithStats(
                user_id=user_data.user_id,
                email=user_data.email,
                name=user_data.name,
                is_anonymous=user_data.is_anonymous,
                chat_count=user_data.chat_count or 0,
                message_count=user_data.message_count or 0,
                created_at=user_data.created_at.isoformat()
            ))
        
        # Get overall company totals
        total_users = len(users_with_stats)
        
        # Total chats - only count chats from non-anonymous users
        total_chats = db.query(func.count(Chat.id)).join(
            CompanyUser, Chat.user_id == CompanyUser.user_id
        ).filter(
            Chat.company_id == company_id,
            Chat.is_deleted == False,
            CompanyUser.is_anonymous == False
        ).scalar() or 0
        
        # Total messages - only count messages from chats by non-anonymous users
        total_messages = db.query(func.count(Message.id)).join(
            Chat, Message.chat_id == Chat.chat_id
        ).join(
            CompanyUser, Chat.user_id == CompanyUser.user_id
        ).filter(
            Message.company_id == company_id,
            CompanyUser.is_anonymous == False
        ).scalar() or 0
        
        return CompanyUsersResponse(
            users=users_with_stats,
            total_users=total_users,
            total_chats=total_chats,
            total_messages=total_messages,
            company_id=company_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch company users with stats: {str(e)}"
        )
    finally:
        db.close()
