#!/usr/bin/env python3

import time
import logging
import sys
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from pcb_part_finder.db.models import Project
from .processor import process_project_from_db

# Configure logging to stdout for Docker compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_next_project() -> str:
    """
    Get the next project from the database queue.
    Returns the project ID or None if no projects are available.
    """
    db = SessionLocal()
    try:
        # Query for the next queued project, ordered by creation date
        project = db.query(Project).filter(
            Project.status == 'queued'
        ).order_by(
            Project.created_at.asc()
        ).first()
        
        if not project:
            logger.info("No projects in queue")
            return None
            
        logger.info(f"Found queued project: {project.project_id}")
        return project.project_id
        
    finally:
        db.close()

def process_queue():
    """
    Main function to process the project queue.
    """
    while True:
        try:
            # Get next project
            project_id = get_next_project()
            if not project_id:
                logger.info("No projects to process, waiting...")
                time.sleep(1)  # Wait 1 second before checking again
                continue
            
            # Update project status to processing
            db = SessionLocal()
            try:
                project = db.query(Project).filter(
                    Project.project_id == project_id
                ).first()
                
                if not project:
                    logger.error(f"Project {project_id} not found in database")
                    continue
                
                project.status = 'processing'
                project.start_time = datetime.now()
                db.commit()
                logger.info(f"Started processing project: {project_id}")
                
            finally:
                db.close()
            
            # Process the project
            try:
                # Process the project using the new database-based processor
                # process_project_from_db now handles its own final status update
                # and returns True if orchestration succeeded, False if setup failed.
                orchestration_succeeded = process_project_from_db(project_id=project_id)
                if not orchestration_succeeded:
                    # The processor already logged the fatal setup error and set status to 'error'
                    logger.error(f"Processing setup failed for project {project_id}. Status should be 'error'.")
                # No further status update needed here; processor handles 'completed',
                # 'completed_with_errors', and fatal 'error' statuses.
                
            except Exception as e:
                # This catches exceptions *outside* of process_project_from_db's main try/except
                # This shouldn't normally happen if process_project_from_db handles its errors,
                # but log it just in case. The project status might be left as 'processing'.
                logger.critical(f"Unexpected error in queue runner *after* calling processor for {project_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in queue processing loop: {e}", exc_info=True) # Log full traceback
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    process_queue() 