from sqlalchemy.orm import Session
from sqlalchemy import func, select, update
from typing import Optional, List, Tuple, Dict
import datetime

from .models import Project, BomItem, Component, BomItemMatch
from ..schemas import InputBOM, BOMComponent

def create_project(
    db: Session,
    project_id: str,
    description: Optional[str] = None,
    status: str = "queued"
) -> Project:
    """
    Create a new project in the database.
    
    Args:
        db: Database session
        project_id: Unique identifier for the project
        description: Optional project description
        status: Project status (defaults to "queued")
        
    Returns:
        The created Project instance
    """
    db_project = Project(
        project_id=project_id,
        description=description,
        status=status
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def create_bom_item(
    db: Session,
    item: BOMComponent,
    project_id: str
) -> BomItem:
    """
    Create a new BOM item in the database.
    
    Args:
        db: Database session
        item: BOMComponent data from the input
        project_id: ID of the project this item belongs to
        
    Returns:
        The created BomItem instance
    """
    db_item = BomItem(
        project_id=project_id,
        quantity=item.qty,
        description=item.description,
        package=item.package,
        notes=item.notes
    )
    db.add(db_item)
    return db_item

def get_project_by_id(
    db: Session,
    project_id: str
) -> Optional[Project]:
    """
    Retrieve a project by its ID.
    
    Args:
        db: Database session
        project_id: ID of the project to retrieve
        
    Returns:
        The Project instance if found, None otherwise
    """
    return db.query(Project).filter(Project.project_id == project_id).first()

def get_bom_items_for_project(
    db: Session,
    project_id: str
) -> List[BomItem]:
    """
    Retrieve all BOM items for a specific project.
    
    Args:
        db: Database session
        project_id: ID of the project
        
    Returns:
        List of BomItem instances for the project
    """
    return db.query(BomItem).filter(BomItem.project_id == project_id).all()

def get_project_status(
    db: Session,
    project_id: str
) -> Optional[str]:
    """
    Get the status of a project.
    
    Args:
        db: Database session
        project_id: ID of the project
        
    Returns:
        The project's status if found, None otherwise
    """
    project = db.query(Project).filter(Project.project_id == project_id).first()
    return project.status if project else None

def get_queue_info(
    db: Session,
    project_id: str
) -> Tuple[int, int]:
    """
    Get the position and total length of the queue for a project.
    
    Args:
        db: Database session
        project_id: ID of the project
        
    Returns:
        Tuple of (position, total_in_queue)
        Returns (0, 0) if project not found or not queued
    """
    # Get the project's creation time
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project or project.status != 'queued':
        return (0, 0)
    
    # Get total number of queued projects
    total_in_queue = db.query(func.count(Project.project_id)).filter(
        Project.status == 'queued'
    ).scalar()
    
    # Get position in queue (number of projects created before this one)
    position = db.query(func.count(Project.project_id)).filter(
        Project.status == 'queued',
        Project.created_at <= project.created_at
    ).scalar()
    
    return (position, total_in_queue)

def count_queued_projects(
    db: Session
) -> int:
    """
    Count the number of projects in the queue.
    
    Args:
        db: Database session
        
    Returns:
        Number of queued projects
    """
    return db.query(func.count(Project.project_id)).filter(
        Project.status == 'queued'
    ).scalar()

def find_next_queued_project(
    db: Session
) -> Optional[Project]:
    """
    Find the next queued project to process, ordered by creation time.
    
    Args:
        db: Database session
        
    Returns:
        The next Project to process, or None if no queued projects exist
    """
    return (
        db.query(Project)
        .filter(Project.status == 'queued')
        .order_by(Project.created_at)
        .first()
    )

def update_project_status(
    db: Session,
    project_id: str,
    new_status: str,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> bool:
    """
    Update a project's status and timestamps.
    Handles all valid status transitions: 'queued' -> 'processing' -> 'finished'/'error'
    
    Args:
        db: Database session
        project_id: ID of the project to update
        new_status: New status to set ('queued', 'processing', 'finished', 'error', 'cancelled')
        start_time: Optional start time to set (typically for 'processing' status)
        end_time: Optional end time to set (typically for 'finished' or 'error' status)
        
    Returns:
        True if project was found and updated, False otherwise
    """
    # Find the project
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        return False
    
    # Validate status transition
    valid_transitions = {
        'queued': ['processing', 'cancelled'],
        'processing': ['finished', 'error', 'cancelled'],
        'finished': ['cancelled'],
        'error': ['cancelled'],
        'cancelled': []
    }
    
    if new_status not in valid_transitions.get(project.status, []):
        return False
    
    # Update fields
    project.status = new_status
    if start_time:
        project.start_time = start_time
    if end_time:
        project.end_time = end_time
    
    db.commit()
    return True

def get_or_create_component(
    db: Session,
    component_data: Dict
) -> Component:
    """
    Get an existing component or create a new one based on Mouser part number.
    Updates existing component's fields if found.
    
    Args:
        db: Database session
        component_data: Dictionary containing component data
        
    Returns:
        The found or created Component instance
    """
    # Try to find existing component
    component = db.query(Component).filter(
        Component.mouser_part_number == component_data['mouser_part_number']
    ).first()
    
    if component:
        # Update fields from component_data
        for key, value in component_data.items():
            if hasattr(component, key):
                setattr(component, key, value)
        component.last_updated = datetime.datetime.utcnow()
    else:
        # Create new component
        component = Component(**component_data)
        db.add(component)
    
    db.commit()
    db.refresh(component)
    return component

def create_bom_item_match(
    db: Session,
    bom_item_id: int,
    component_id: Optional[int],
    match_status: str
) -> BomItemMatch:
    """
    Create a new match between a BOM item and a component.
    Note: This function does not commit the transaction, allowing batch operations.
    
    Args:
        db: Database session
        bom_item_id: ID of the BOM item
        component_id: ID of the matched component (can be None for no match)
        match_status: Status of the match ('matched', 'no_match', 'multiple_matches', etc.)
        
    Returns:
        The created BomItemMatch instance
    """
    match = BomItemMatch(
        bom_item_id=bom_item_id,
        component_id=component_id,
        match_status=match_status
    )
    db.add(match)
    return match

def get_finished_project_data(
    db: Session,
    project_id: str
) -> List[Tuple[BomItem, Optional[BomItemMatch], Optional[Component]]]:
    """
    Get all BOM items and their matches for a finished project.
    
    Args:
        db: Database session
        project_id: ID of the project
        
    Returns:
        List of tuples (BomItem, BomItemMatch, Component)
        BomItemMatch and Component may be None if no match was found
    """
    # Build the query with LEFT OUTER JOINs
    query = (
        db.query(BomItem, BomItemMatch, Component)
        .outerjoin(BomItemMatch, BomItem.bom_item_id == BomItemMatch.bom_item_id)
        .outerjoin(Component, BomItemMatch.component_id == Component.component_id)
        .filter(BomItem.project_id == project_id)
    )
    
    return query.all() 