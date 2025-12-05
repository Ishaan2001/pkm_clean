from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import json
from pydantic import BaseModel
from datetime import timedelta, datetime, timezone

from . import schemas
from .database import get_db, init_db, Note, Notebook, User, PushSubscription
from .ai_service import summarize_note
from .auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .scheduler import notification_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notes PWA API", version="1.0.0")

# Configure CORS for both development and production
allowed_origins = [
    "http://localhost:5173", 
    "http://localhost:5174", 
    "http://127.0.0.1:5173", 
    "http://127.0.0.1:5174",  # Development
]

# Add additional origins from environment variable (for production)
if os.getenv("FRONTEND_ORIGINS"):
    additional_origins = os.getenv("FRONTEND_ORIGINS").split(",")
    allowed_origins.extend([origin.strip() for origin in additional_origins])

# Custom CORS middleware to handle Vercel subdomains
def is_vercel_origin(origin: str) -> bool:
    """Check if origin is a Vercel deployment"""
    return origin.endswith('.vercel.app') and origin.startswith('https://')

# For production, we'll need to add the specific Vercel URL via FRONTEND_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app$"  # Allow all Vercel apps
)

@app.on_event("startup")
async def startup_event():
    init_db()
    # COMMENTED OUT: Internal scheduler replaced by GitHub Actions direct trigger
    # Start the notification scheduler
    # notification_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    # COMMENTED OUT: Internal scheduler replaced by GitHub Actions direct trigger
    # Stop the notification scheduler
    # notification_scheduler.stop()
    pass

async def generate_summary_task(note_id: int, content: str, db: Session):
    """Background task to generate AI summary"""
    try:
        summary = summarize_note(content)
        if summary:
            note = db.query(Note).filter(Note.id == note_id).first()
            if note:
                note.ai_summary = summary
                db.commit()
                logger.info(f"AI summary generated for note {note_id}")
    except Exception as e:
        logger.error(f"Failed to generate summary for note {note_id}: {e}")

@app.get("/")
async def root():
    return {"message": "Notes PWA API is running"}

# Authentication endpoints
@app.post("/api/auth/signup", response_model=schemas.Token)
async def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """User registration"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    logger.info(f"New user registered: {db_user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=schemas.Token)
async def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return current_user

@app.post("/api/auth/logout")
async def logout():
    """Logout (client-side token removal)"""
    return {"message": "Successfully logged out"}

@app.post("/api/notes", response_model=schemas.Note)
async def create_note(
    note: schemas.NoteCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new note and generate AI summary in background"""
    db_note = Note(content=note.content, user_id=current_user.id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    
    # Generate AI summary in background
    background_tasks.add_task(generate_summary_task, db_note.id, note.content, db)
    
    return db_note

@app.get("/api/notes", response_model=List[schemas.Note])
async def get_notes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all notes for current user"""
    notes = db.query(Note).filter(Note.user_id == current_user.id).order_by(Note.updated_at.desc()).offset(skip).limit(limit).all()
    return notes

@app.get("/api/notes/{note_id}", response_model=schemas.Note)
async def get_note(
    note_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific note by ID"""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.put("/api/notes/{note_id}", response_model=schemas.Note)
async def update_note(
    note_id: int, 
    note_update: schemas.NoteUpdate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a note and optionally regenerate AI summary"""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    
    note.content = note_update.content
    db.commit()
    db.refresh(note)
    
    # Regenerate AI summary if requested
    if note_update.regenerate_summary:
        background_tasks.add_task(generate_summary_task, note.id, note_update.content, db)
    
    return note

@app.delete("/api/notes/{note_id}")
async def delete_note(
    note_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a note"""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully"}


# Notebook endpoints
@app.get("/api/notebooks", response_model=List[schemas.Notebook])
async def get_notebooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all notebooks with note counts for current user"""
    from sqlalchemy import func
    notebooks = (
        db.query(
            Notebook,
            func.count(Note.id).label('note_count')
        )
        .filter(Notebook.user_id == current_user.id)
        .outerjoin(Notebook.notes)
        .group_by(Notebook.id)
        .order_by(Notebook.updated_at.desc())
        .all()
    )
    
    result = []
    for notebook, note_count in notebooks:
        notebook_dict = {
            "id": notebook.id,
            "title": notebook.title,
            "created_at": notebook.created_at,
            "updated_at": notebook.updated_at,
            "note_count": note_count
        }
        result.append(notebook_dict)
    
    return result

@app.post("/api/notebooks", response_model=schemas.Notebook)
async def create_notebook(
    notebook: schemas.NotebookCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new notebook"""
    db_notebook = Notebook(title=notebook.title, user_id=current_user.id)
    db.add(db_notebook)
    db.commit()
    db.refresh(db_notebook)
    
    # Add note_count field
    result = {
        "id": db_notebook.id,
        "title": db_notebook.title,
        "created_at": db_notebook.created_at,
        "updated_at": db_notebook.updated_at,
        "note_count": 0
    }
    return result

@app.get("/api/notebooks/{notebook_id}", response_model=schemas.NotebookWithNotes)
async def get_notebook(
    notebook_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific notebook with its notes"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    # Sort the notes by updated_at descending (newest first)
    sorted_notes = sorted(notebook.notes, key=lambda note: note.updated_at, reverse=True)
    
    # Create a copy of the notebook with sorted notes
    notebook_dict = {
        "id": notebook.id,
        "title": notebook.title,
        "created_at": notebook.created_at,
        "updated_at": notebook.updated_at,
        "notes": sorted_notes
    }
    
    return notebook_dict

@app.put("/api/notebooks/{notebook_id}", response_model=schemas.Notebook)
async def update_notebook(
    notebook_id: int, 
    notebook_update: schemas.NotebookUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a notebook title"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    notebook.title = notebook_update.title
    db.commit()
    db.refresh(notebook)
    
    # Get note count
    from sqlalchemy import func
    note_count = db.query(func.count(Note.id)).join(Notebook.notes).filter(Notebook.id == notebook_id).scalar() or 0
    
    result = {
        "id": notebook.id,
        "title": notebook.title,
        "created_at": notebook.created_at,
        "updated_at": notebook.updated_at,
        "note_count": note_count
    }
    return result

@app.delete("/api/notebooks/{notebook_id}")
async def delete_notebook(
    notebook_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a notebook (notes are not deleted, only the association)"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    db.delete(notebook)
    db.commit()
    return {"message": "Notebook deleted successfully"}

@app.get("/api/notebooks/{notebook_id}/notes", response_model=List[schemas.Note])
async def get_notebook_notes(
    notebook_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all notes in a specific notebook"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook.notes

@app.post("/api/notebooks/{notebook_id}/notes/{note_id}")
async def add_note_to_notebook(
    notebook_id: int, 
    note_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a note to a notebook"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    note = db.query(Note).filter(
        Note.id == note_id, 
        Note.user_id == current_user.id
    ).first()
    
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note not in notebook.notes:
        notebook.notes.append(note)
        db.commit()
        return {"message": "Note added to notebook successfully"}
    else:
        return {"message": "Note is already in this notebook"}

@app.delete("/api/notebooks/{notebook_id}/notes/{note_id}")
async def remove_note_from_notebook(
    notebook_id: int, 
    note_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a note from a notebook"""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id, 
        Notebook.user_id == current_user.id
    ).first()
    note = db.query(Note).filter(
        Note.id == note_id, 
        Note.user_id == current_user.id
    ).first()
    
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note in notebook.notes:
        notebook.notes.remove(note)
        db.commit()
        return {"message": "Note removed from notebook successfully"}
    else:
        return {"message": "Note is not in this notebook"}

# Search endpoint
@app.get("/api/search", response_model=schemas.SearchResult)
async def search_notes(
    q: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search notes by content and AI summary"""
    if not q.strip():
        return {"notes": [], "total_count": 0}
    
    search_term = f"%{q.lower()}%"
    notes = db.query(Note).filter(
        Note.user_id == current_user.id,
        (Note.content.ilike(search_term) | Note.ai_summary.ilike(search_term))
    ).all()
    
    return {"notes": notes, "total_count": len(notes)}

# Push Notification endpoints
@app.post("/api/push/subscribe", response_model=schemas.PushSubscriptionResponse)
async def subscribe_to_push_notifications(
    subscription_data: schemas.PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Subscribe user's device for push notifications"""
    try:
        # Check if this endpoint is already subscribed for this user
        existing_sub = db.query(PushSubscription).filter(
            PushSubscription.endpoint == subscription_data.endpoint,
            PushSubscription.user_id == current_user.id
        ).first()

        if existing_sub:
            # Update existing subscription with new keys (in case they changed)
            existing_sub.p256dh_key = subscription_data.keys.p256dh
            existing_sub.auth_key = subscription_data.keys.auth
            existing_sub.user_agent = subscription_data.user_agent
            db.commit()
            db.refresh(existing_sub)
            
            logger.info(f"Updated push subscription for user {current_user.email}")
            return schemas.PushSubscriptionResponse(
                message="Push notifications updated successfully",
                subscription_id=existing_sub.id
            )
        
        # Create new subscription
        new_subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=subscription_data.endpoint,
            p256dh_key=subscription_data.keys.p256dh,
            auth_key=subscription_data.keys.auth,
            user_agent=subscription_data.user_agent
        )
        
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        
        logger.info(f"Created new push subscription for user {current_user.email}")
        return schemas.PushSubscriptionResponse(
            message="Push notifications enabled successfully",
            subscription_id=new_subscription.id
        )
        
    except Exception as e:
        logger.error(f"Failed to subscribe user {current_user.email} to push notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable push notifications"
        )

@app.delete("/api/push/unsubscribe")
async def unsubscribe_from_push_notifications(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Unsubscribe user's device from push notifications"""
    subscription = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint,
        PushSubscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    db.delete(subscription)
    db.commit()
    
    logger.info(f"Unsubscribed device from push notifications for user {current_user.email}")
    return {"message": "Push notifications disabled successfully"}

@app.get("/api/push/subscriptions")
async def get_user_push_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all push subscriptions for the current user"""
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id
    ).all()
    
    return {
        "subscriptions": [
            {
                "id": sub.id,
                "endpoint": sub.endpoint[:50] + "..." if len(sub.endpoint) > 50 else sub.endpoint,
                "user_agent": sub.user_agent,
                "created_at": sub.created_at
            }
            for sub in subscriptions
        ],
        "total_count": len(subscriptions)
    }

# Scheduler management endpoints (for debugging)
@app.get("/api/push/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get notification scheduler status (debug endpoint)"""
    return {
        "status": "disabled",
        "message": "Internal scheduler disabled - using GitHub Actions direct trigger",
        "trigger_method": "github_actions_direct_api_call"
    }

@app.post("/api/push/test-notification")
async def trigger_test_notification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a test notification to the current logged-in user"""
    from .notification_service import NotificationService
    
    try:
        # Get user's push subscriptions
        subscriptions = db.query(PushSubscription).filter(
            PushSubscription.user_id == current_user.id
        ).all()
        
        if not subscriptions:
            raise HTTPException(
                status_code=400,
                detail="No push subscriptions found for your account. Please enable notifications first."
            )
        
        # Get a random note from user for testing
        user_note = db.query(Note).filter(
            Note.user_id == current_user.id
        ).first()
        
        if not user_note:
            # Send generic test notification if no notes
            notification_data = {
                'title': 'Knowledge Base - Test Notification',
                'body': f'Hello {current_user.first_name or "User"}! Push notifications are working correctly. 🎉',
                'icon': '/icon-192.svg',
                'badge': '/icon-192.svg',
                'tag': 'test-notification',
                'data': {
                    'type': 'test',
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': current_user.id
                }
            }
        else:
            # Send test notification with actual note
            notification_data = {
                'title': 'Knowledge Base - Test Notification',
                'body': f'Test note: {user_note.content[:100]}{"..." if len(user_note.content) > 100 else ""}',
                'icon': '/icon-192.svg',
                'badge': '/icon-192.svg',
                'tag': 'test-notification',
                'data': {
                    'type': 'test',
                    'noteId': user_note.id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': current_user.id
                }
            }
        
        # Send notification to all user's devices
        notifications_sent = 0
        # Convert notification data to JSON string (required by send_push_notification)
        notification_payload = json.dumps(notification_data)
        
        for subscription in subscriptions:
            success = NotificationService.send_push_notification(subscription, notification_payload)
            if success:
                notifications_sent += 1
        
        return {
            "message": f"Test notification sent successfully to {notifications_sent} device(s)",
            "devices": len(subscriptions),
            "successful": notifications_sent,
            "user_email": current_user.email
        }
        
    except Exception as e:
        logger.error(f"Failed to send test notification to user {current_user.email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test notification: {str(e)}"
        )

@app.get("/api/wake-server")
async def wake_server():
    """
    Public endpoint to wake up the server from Render sleep mode.
    Designed to be called by external cron services at 9:55 AM IST.
    Does NOT send notifications - just ensures server is awake for the 10 AM scheduler.
    """
    try:
        # Log the wake-up call
        current_time = datetime.utcnow()
        ist_time = current_time.replace(tzinfo=timezone.utc).astimezone(
            timezone(timedelta(hours=5, minutes=30))  # IST offset
        )
        
        logger.info(f"Server wake-up triggered by external cron service at {ist_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        # Get scheduler status to confirm it's running
        scheduler_status = notification_scheduler.get_status()
        
        # Return comprehensive status to confirm server is fully awake
        return {
            "status": "awake",
            "message": "Server successfully awakened by external cron service",
            "current_time_utc": current_time.isoformat(),
            "current_time_ist": ist_time.strftime('%Y-%m-%d %H:%M:%S IST'),
            "scheduler_status": scheduler_status,
            "purpose": "Ensuring server is awake for 10 AM IST daily notification scheduler",
            "next_notification_time": "10:00 AM IST (internal scheduler will handle)",
            "triggered_by": "external_cron_service"
        }
        
    except Exception as e:
        logger.error(f"Error in wake-server endpoint: {e}")
        # Still return success to ensure external cron service knows server is awake
        return {
            "status": "awake_with_warning", 
            "message": f"Server awake but encountered minor issue: {str(e)}",
            "current_time_utc": datetime.utcnow().isoformat()
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/minimal-wake")
async def minimal_wake():
    """Ultra-minimal endpoint for cron-job.org with size restrictions"""
    logger.info("Minimal wake-up triggered by external cron service")
    return "OK"

@app.post("/api/push/send-daily-notifications")
async def trigger_daily_notifications():
    """
    Direct endpoint to trigger daily notifications.
    Called by GitHub Actions instead of relying on internal scheduler.
    This ensures notifications are sent even if GitHub Actions runs late.
    """
    from .notification_service import NotificationService
    
    try:
        # Log the trigger time
        current_time = datetime.utcnow()
        ist_time = current_time.replace(tzinfo=timezone.utc).astimezone(
            timezone(timedelta(hours=5, minutes=30))  # IST offset
        )
        
        logger.info(f"Daily notifications triggered by GitHub Actions at {ist_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        # Directly trigger the notification sending
        NotificationService.send_daily_notifications()
        
        return {
            "status": "success",
            "message": "Daily notifications sent successfully",
            "triggered_at_utc": current_time.isoformat(),
            "triggered_at_ist": ist_time.strftime('%Y-%m-%d %H:%M:%S IST'),
            "triggered_by": "github_actions_direct_trigger"
        }
        
    except Exception as e:
        logger.error(f"Failed to send daily notifications via GitHub Actions trigger: {e}")
        return {
            "status": "error",
            "message": f"Failed to send daily notifications: {str(e)}",
            "triggered_at_utc": datetime.utcnow().isoformat()
        }