import sys
import os
import datetime

# Add the backend directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from app.db import models

def seed():
    # Ensure tables are created
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing seeded campaigns to prevent duplicates if ran multiple times
        db.query(models.Campaign).delete()
        
        campaigns = [
            models.Campaign(
                name="Q4 Enterprise SaaS Outreach",
                target_files="enterprise-leads-v2.csv",
                status="RUNNING",
                total_leads=1000,
                sent=450,
                opens=236,
                replies=55,
                created_at=datetime.datetime.utcnow()
            ),
            models.Campaign(
                name="Follow-up: Inactive Leads",
                target_files="stale-users-2023.csv",
                status="PAUSED",
                total_leads=2500,
                sent=812,
                opens=309,
                replies=36,
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=2)
            ),
            models.Campaign(
                name="HubSpot List Sync - Oct",
                target_files="direct-crm-import.csv",
                status="COMPLETED",
                total_leads=500,
                sent=500,
                opens=321,
                replies=92,
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=5)
            )
        ]
        
        db.add_all(campaigns)
        db.commit()
        print("Successfully seeded campaigns!")
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
