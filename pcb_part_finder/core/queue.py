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
            success = False
            try:
                # Process the project using the new database-based processor
                success = process_project_from_db(project_id=project_id, db=db)
                
            except Exception as e:
                logger.error(f"Error processing project {project_id}: {str(e)}")
                success = False
                
            finally:
                # Update project status based on processing outcome
                db = SessionLocal()
                try:
                    project = db.query(Project).filter(
                        Project.project_id == project_id
                    ).first()
                    
                    if project:
                        project.status = 'complete' if success else 'failed'
                        project.end_time = datetime.now()
                        db.commit()
                        logger.info(f"Updated project {project_id} status to {project.status}")
                    else:
                        logger.error(f"Project {project_id} not found when updating status")
                        
                finally:
                    db.close()
            
        except Exception as e:
            logger.error(f"Error in queue processing: {str(e)}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    process_queue() 