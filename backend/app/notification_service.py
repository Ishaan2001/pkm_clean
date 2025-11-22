import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import pytz
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from .database import SessionLocal, User, Note, PushSubscription

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# VAPID configuration from environment
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY") 
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:support@example.com")

# Indian timezone
INDIAN_TZ = pytz.timezone('Asia/Kolkata')

class NotificationService:
    """Service for handling push notifications"""
    
    @staticmethod
    def get_vapid_claims() -> Dict[str, str]:
        """Get VAPID claims for push notifications"""
        return {"sub": VAPID_SUBJECT}
    
    @staticmethod
    def get_user_notes_for_today(user_id: int, db: Session) -> Note:
        """
        Get today's note for a user using round-robin selection.
        Uses day of year to ensure consistent selection across all user's devices.
        """
        # Get all notes for this user ordered by creation date for consistency
        user_notes = db.query(Note).filter(
            Note.user_id == user_id
        ).order_by(Note.created_at.asc()).all()
        
        if not user_notes:
            return None
            
        # Get current day of year in Indian timezone
        indian_now = datetime.now(INDIAN_TZ)
        day_of_year = indian_now.timetuple().tm_yday
        
        # Round-robin selection: use modulo to cycle through notes
        note_index = day_of_year % len(user_notes)
        selected_note = user_notes[note_index]
        
        logger.info(f"Selected note {selected_note.id} for user {user_id} "
                   f"(day {day_of_year}, index {note_index} of {len(user_notes)} notes)")
        
        return selected_note
    
    @staticmethod
    def create_notification_payload(note: Note) -> str:
        """Create the notification payload for a note"""
        # Truncate content for notification display
        max_content_length = 120
        content_preview = note.content[:max_content_length]
        if len(note.content) > max_content_length:
            content_preview += "..."
            
        # Use AI summary if available, otherwise use content preview
        body_text = note.ai_summary if note.ai_summary else content_preview
        
        payload = {
            "title": "📝 Daily Note Reminder",
            "body": body_text,
            "icon": "/icon-192.svg",
            "badge": "/icon-192.svg",
            "data": {
                "url": f"/note/{note.id}",
                "noteId": note.id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "actions": [
                {
                    "action": "open",
                    "title": "Open Note"
                },
                {
                    "action": "dismiss",
                    "title": "Dismiss"
                }
            ],
            "requireInteraction": False,
            "silent": False
        }
        
        return json.dumps(payload)
    
    @staticmethod
    def send_push_notification(subscription: PushSubscription, payload: str) -> bool:
        """
        Send a push notification to a specific subscription.
        Returns True if successful, False otherwise.
        """
        try:
            # Create subscription info in the format expected by pywebpush
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key
                }
            }
            
            # Send the notification
            response = webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=NotificationService.get_vapid_claims(),
                ttl=43200  # 12 hours TTL for offline delivery
            )
            
            logger.info(f"Push notification sent successfully to subscription {subscription.id}")
            return True
            
        except WebPushException as e:
            logger.error(f"WebPush error for subscription {subscription.id}: {e}")
            
            # If status code is 410 (Gone), the subscription is no longer valid
            if e.response and e.response.status_code == 410:
                logger.info(f"Subscription {subscription.id} is invalid, marking for removal")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error sending notification to subscription {subscription.id}: {e}")
            
        return False
    
    @staticmethod
    def cleanup_invalid_subscription(subscription_id: int, db: Session):
        """Remove an invalid subscription from the database"""
        try:
            subscription = db.query(PushSubscription).filter(
                PushSubscription.id == subscription_id
            ).first()
            
            if subscription:
                db.delete(subscription)
                db.commit()
                logger.info(f"Removed invalid subscription {subscription_id}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup subscription {subscription_id}: {e}")
    
    @staticmethod
    def send_daily_notifications():
        """
        Main function to send daily notifications to all users.
        Called by the scheduler at 10 AM Indian time daily.
        """
        db = SessionLocal()
        
        try:
            indian_now = datetime.now(INDIAN_TZ)
            logger.info(f"Starting daily notification job at {indian_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Get all active users who have notes
            users_with_notes = db.query(User).join(Note).filter(
                User.is_active == True
            ).distinct().all()
            
            total_notifications_sent = 0
            total_users_processed = 0
            
            for user in users_with_notes:
                try:
                    # Get today's note for this user (round-robin)
                    selected_note = NotificationService.get_user_notes_for_today(user.id, db)
                    
                    if not selected_note:
                        logger.info(f"No notes found for user {user.email}")
                        continue
                    
                    # Get all push subscriptions for this user
                    user_subscriptions = db.query(PushSubscription).filter(
                        PushSubscription.user_id == user.id
                    ).all()
                    
                    if not user_subscriptions:
                        logger.info(f"No push subscriptions found for user {user.email}")
                        continue
                    
                    # Create notification payload
                    payload = NotificationService.create_notification_payload(selected_note)
                    
                    # Send notification to all user's devices (laptop, phone, etc.)
                    user_notifications_sent = 0
                    invalid_subscriptions = []
                    
                    for subscription in user_subscriptions:
                        success = NotificationService.send_push_notification(subscription, payload)
                        
                        if success:
                            user_notifications_sent += 1
                        else:
                            invalid_subscriptions.append(subscription.id)
                    
                    # Cleanup invalid subscriptions
                    for sub_id in invalid_subscriptions:
                        NotificationService.cleanup_invalid_subscription(sub_id, db)
                    
                    total_notifications_sent += user_notifications_sent
                    total_users_processed += 1
                    
                    logger.info(f"Sent {user_notifications_sent} notifications to user {user.email} "
                               f"for note: '{selected_note.content[:50]}...'")
                    
                except Exception as e:
                    logger.error(f"Failed to process notifications for user {user.email}: {e}")
                    continue
            
            logger.info(f"Daily notification job completed. "
                       f"Processed {total_users_processed} users, "
                       f"sent {total_notifications_sent} notifications total")
            
        except Exception as e:
            logger.error(f"Failed to run daily notification job: {e}")
            
        finally:
            db.close()

    @staticmethod
    def validate_vapid_configuration() -> bool:
        """Validate that VAPID keys are properly configured"""
        if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
            logger.error("VAPID keys not configured. Please set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY environment variables.")
            return False
        
        logger.info("VAPID configuration validated successfully")
        return True