#!/usr/bin/env python3

import os
import json
import time
import logging
import shutil
import sys
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from pcb_part_finder.main import main as process_project

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_next_project() -> str:
    """
    Get the next project from the queue directory.
    Returns the project name or None if no projects are available.
    """
    queue_dir = Path("projects/queue")
    if not queue_dir.exists():
        logger.error("Queue directory does not exist")
        return None
    
    projects = sorted([p for p in queue_dir.iterdir() if p.is_dir()])
    if not projects:
        logger.info("No projects in queue")
        return None
    
    return projects[0].name

def validate_project_files(project_path: Path) -> bool:
    """
    Validate that a project has the required files.
    Returns True if valid, False otherwise.
    """
    required_files = ["initial_bom.csv", "project_details.txt"]
    for file in required_files:
        if not (project_path / file).exists():
            logger.error(f"Missing required file: {file}")
            return False
    return True

def create_results_file(project_path: Path, status: str, start_time: datetime, end_time: datetime) -> None:
    """
    Create a results.json file with processing status and timestamps.
    """
    results = {
        "status": status,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    with open(project_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

def process_queue():
    """
    Main function to process the project queue.
    """
    while True:
        try:
            # Get next project
            project_name = get_next_project()
            if not project_name:
                logger.info("No projects to process, waiting...")
                time.sleep(1)  # Wait 1 minute before checking again
                continue
            
            logger.info(f"Processing project: {project_name}")
            
            # Set up paths
            queue_path = Path("projects/queue") / project_name
            finished_path = Path("projects/finished") / project_name
            
            # Validate project files
            if not validate_project_files(queue_path):
                logger.error(f"Invalid project files for {project_name}")
                # Move to finished with error status
                finished_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(queue_path), str(finished_path))
                create_results_file(
                    finished_path,
                    "failed",
                    datetime.now(),
                    datetime.now()
                )
                continue
            
            # Process the project
            start_time = datetime.now()
            try:
                # Save original sys.argv
                original_argv = sys.argv
                
                # Set up command line arguments for the main function
                sys.argv = [
                    "process_queue.py",
                    "--input", str(queue_path / "initial_bom.csv"),
                    "--notes", str(queue_path / "project_details.txt"),
                    "--output", str(queue_path / "bom_matched.csv")
                ]
                
                # Call the main processing function
                process_project()
                
                # Restore original sys.argv
                sys.argv = original_argv
                
                status = "complete"
            except Exception as e:
                logger.error(f"Error processing project {project_name}: {str(e)}")
                status = "failed"
            
            end_time = datetime.now()
            
            # Move to finished directory
            finished_path.mkdir(parents=True, exist_ok=True)
            # Move contents instead of the directory itself
            for item in queue_path.iterdir():
                shutil.move(str(item), str(finished_path))
            # Remove the now empty queue directory
            queue_path.rmdir()
            
            # Create results file
            create_results_file(
                finished_path,
                status,
                start_time,
                end_time
            )
            
            logger.info(f"Finished processing project: {project_name} (status: {status})")
            
        except Exception as e:
            logger.error(f"Error in queue processing: {str(e)}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    process_queue() 