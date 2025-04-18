"""Project-related endpoints for the PCB Part Finder API."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import datetime
import uuid

from ..schemas import InputBOM, MatchedBOM, MatchedComponent, BOMComponent
from ..db.crud import (
    create_project,
    create_bom_item,
    get_project_by_id,
    get_bom_items_for_project,
    get_queue_info,
    count_queued_projects,
    get_finished_project_data,
    update_project_status
)
from ..db.session import get_db

router = APIRouter(prefix="/project", tags=["projects"])

@router.post("")
async def create_project(
    bom: InputBOM,
    db: Session = Depends(get_db)
):
    """
    Create a new project with BOM data.
    Truncates to 20 components if needed.
    """
    try:
        # Truncate to 20 components if needed
        truncation_info = None
        if len(bom.components) > 20:
            truncation_info = f"BOM truncated from {len(bom.components)} to 20 components"
            bom.components = bom.components[:20]
        
        # Generate project ID using UUID
        project_id = str(uuid.uuid4())
        
        # Create project in database
        db_project = create_project(
            db=db,
            project_id=project_id,
            description=bom.project_description,
            status='queued'
        )
        
        # Create BOM items
        for comp in bom.components:
            create_bom_item(
                db=db,
                item=comp,
                project_id=project_id
            )
        
        # Commit all changes
        db.commit()
        
        return {
            "project_id": project_id,
            "truncation_info": truncation_info
        }
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get project details and BOM data.
    For queued projects, returns position in queue.
    For finished projects, returns matched components.
    """
    # Get project from database
    db_project = get_project_by_id(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Handle queued projects
    if db_project.status == 'queued':
        # Get BOM items
        db_items = get_bom_items_for_project(db=db, project_id=project_id)
        
        # Get queue position
        position, total_in_queue = get_queue_info(db=db, project_id=project_id)
        
        # Reconstruct InputBOM
        components = []
        for db_item in db_items:
            component = BOMComponent(
                qty=db_item.quantity,
                description=db_item.description,
                possible_mpn=db_item.notes,  # notes field used for possible_mpn
                package=db_item.package
            )
            components.append(component)
        
        bom = InputBOM(
            components=components,
            project_description=db_project.description
        )
        
        return {
            "status": "queued",
            "position": position,
            "total_in_queue": total_in_queue,
            "bom": bom.model_dump()
        }
    
    # Handle finished projects
    elif db_project.status == 'finished':
        # Get all BOM items with their matches and components
        results_data = get_finished_project_data(db=db, project_id=project_id)
        
        # Reconstruct matched components
        matched_components = []
        for db_bom_item, db_match, db_component in results_data:
            # Start with base BOM item data
            component_dict = {
                "qty": db_bom_item.quantity,
                "description": db_bom_item.description,
                "possible_mpn": db_bom_item.notes,  # notes field used for possible_mpn
                "package": db_bom_item.package,
                # Initialize match fields as None
                "mouser_part_number": None,
                "manufacturer_part_number": None,
                "manufacturer_name": None,
                "mouser_description": None,
                "datasheet_url": None,
                "price": None,
                "availability": None,
                "match_status": "no_match"
            }
            
            # If we have a match and component, add the match data
            if db_match and db_component:
                component_dict.update({
                    "mouser_part_number": db_component.mouser_part_number,
                    "manufacturer_part_number": db_component.manufacturer_part_number,
                    "manufacturer_name": db_component.manufacturer_name,
                    "mouser_description": db_component.description,
                    "datasheet_url": db_component.datasheet_url,
                    "price": float(db_component.price) if db_component.price else None,
                    "availability": db_component.availability,
                    "match_status": db_match.match_status
                })
            elif db_match:
                # If we have a match but no component, use the match status
                component_dict["match_status"] = db_match.match_status
            
            matched_components.append(MatchedComponent(**component_dict))
        
        # Get match date from project end time
        match_date = (
            db_project.end_time.isoformat() 
            if db_project.end_time 
            else datetime.datetime.now().isoformat()
        )
        
        # Create MatchedBOM
        matched_bom = MatchedBOM(
            components=matched_components,
            project_description=db_project.description,
            match_date=match_date,
            match_status=db_project.status
        )
        
        # Prepare results dictionary
        results = {
            "start_time": (
                db_project.start_time.isoformat() 
                if db_project.start_time 
                else None
            ),
            "end_time": match_date,
            "status": db_project.status
        }
        
        return {
            "status": "finished",
            "bom": matched_bom.model_dump(),
            "results": results
        }
    
    # Handle other statuses
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Project found but status '{db_project.status}' not supported"
        )

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a project by marking it as cancelled in the database.
    Only queued or error-state projects can be deleted.
    """
    # Get the project from database
    db_project = get_project_by_id(db=db, project_id=project_id)
    
    # Check if project exists and is in a deletable state
    if not db_project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )
    
    if db_project.status not in ['queued', 'error']:
        raise HTTPException(
            status_code=404,
            detail="Project cannot be deleted in its current state"
        )
    
    # Update project status to cancelled
    updated = update_project_status(
        db=db,
        project_id=project_id,
        new_status='cancelled'
    )
    
    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Failed to update project status"
        )
    
    return {"status": "cancelled"}

@router.get("/queue/length")
async def get_queue_length(
    db: Session = Depends(get_db)
):
    """
    Get the current length of the processing queue.
    """
    count = count_queued_projects(db=db)
    return {"queue_length": count} 