import logging
import pytz
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .notification_service import NotificationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Indian timezone
INDIAN_TZ = pytz.timezone('Asia/Kolkata')

class NotificationScheduler:
    """Scheduler for daily push notifications"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=INDIAN_TZ)
        
    def start(self):
        """Start the notification scheduler"""
        try:
            # Validate VAPID configuration before starting
            if not NotificationService.validate_vapid_configuration():
                logger.error("Cannot start scheduler: VAPID keys not configured properly")
                return False
            
            # Schedule daily notifications at 10:00 AM Indian time
            self.scheduler.add_job(
                func=NotificationService.send_daily_notifications,
                trigger=CronTrigger(
                    hour=1,  # 10 AM
                    minute=0,  # At the top of the hour
                    timezone=INDIAN_TZ
                ),
                id='daily_notifications',
                name='Daily Note Notifications',
                replace_existing=True,
                max_instances=1  # Prevent overlapping jobs
            )
            
            # For testing purposes, you can also add a more frequent job
            # Uncomment the following lines to test with a 2-minute interval:
            # self.scheduler.add_job(
            #     func=NotificationService.send_daily_notifications,
            #     trigger='interval',
            #     minutes=2,
            #     id='test_notifications',
            #     name='Test Notifications (Every 2 minutes)',
            #     replace_existing=True,
            #     max_instances=1
            # )
            
            self.scheduler.start()
            
            # Get next run time for logging
            next_run = self.scheduler.get_job('daily_notifications').next_run_time
            logger.info(f"Notification scheduler started successfully")
            logger.info(f"Next daily notification scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start notification scheduler: {e}")
            return False
    
    def stop(self):
        """Stop the notification scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Notification scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def get_status(self) -> dict:
        """Get scheduler status and job information"""
        try:
            if not self.scheduler.running:
                return {"status": "stopped", "jobs": []}
            
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
            
            return {
                "status": "running",
                "timezone": str(INDIAN_TZ),
                "current_time": datetime.now(INDIAN_TZ).isoformat(),
                "jobs": jobs
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {"status": "error", "error": str(e)}
    
    def trigger_test_notification(self):
        """Manually trigger a test notification (for debugging)"""
        try:
            logger.info("Manually triggering test notification...")
            NotificationService.send_daily_notifications()
            return True
        except Exception as e:
            logger.error(f"Failed to trigger test notification: {e}")
            return False

# Global scheduler instance
notification_scheduler = NotificationScheduler()
