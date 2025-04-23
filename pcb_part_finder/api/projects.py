"""Project-related endpoints for the PCB Part Finder API."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import datetime
import uuid
import logging
import json
from pydantic import ValidationError
from decimal import Decimal

from ..schemas import InputBOM, MatchedBOM, MatchedComponent, BOMComponent, PotentialMatch
from ..db.crud import (
    create_project as crud_create_project,
    create_bom_item,
    get_project_by_id,
    get_bom_items_for_project,
    get_queue_info,
    count_queued_projects,
    get_finished_project_data,
    update_project_status,
    get_potential_matches_for_bom_item,
    get_component_by_mpn
)
from ..db.session import get_db
from ..db.models import Component
from ..core.llm_handler import get_llm_response, LlmApiError
from ..core.mouser_api import search_mouser_by_mpn
from ..core.cache_manager import MouserApiCacheManager

router = APIRouter(prefix="/project", tags=["projects"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_bom_reformat_prompt(raw_components: str) -> str:
    """Format the prompt for the LLM to reformat BOM components.
    
    Args:
        raw_components: JSON string of the raw component list
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a helpful assistant that reformats Bill of Materials (BOM) data into a standardized format. 
Your task is to convert the following BOM data into a list of components matching this schema:
{{
    "qty": int,
    "description": str,
    "package": str,
    "possible_mpn": Optional[str],
    "notes": Optional[str]
}}

Input BOM data:
{raw_components}

Rules:
1. Map any quantity field to "qty" (convert to integer)
2. Map any description, value, or name field to "description"
3. Map any footprint, package, or similar field to "package"
4. Map any manufacturer part number, MPN, or similar field to "possible_mpn"
5. Map any additional notes, datasheet URLs, or other metadata to "notes"
6. If a field is missing, use appropriate defaults (1 for qty, "unknown" for package)
7. Return ONLY a valid JSON array of objects matching the schema above
8. Do not include any explanatory text, just the JSON

Return the reformatted BOM as a JSON array with no other text. It will the parsed directly."""

@router.post("")
async def create_project(
    raw_data: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new project with BOM data.
    If component data is invalid, it's captured in the description field.
    Truncates to 20 components if needed.
    """
    processed_components = []
    errors = []
    try:
        # Extract project details (optional based on schema)
        project_name = raw_data.get("project_name")
        project_description = raw_data.get("project_description")
        
        raw_components = raw_data.get("components", [])
        
        if not isinstance(raw_components, list):
             raise HTTPException(status_code=400, detail="Input 'components' must be a list.")

        # Attempt to reformat components using LLM
        use_llm_output = False
        try:
            # Convert raw components to JSON string for LLM
            raw_components_json = json.dumps(raw_components)
            prompt = format_bom_reformat_prompt(raw_components_json)
            
            # Get reformatted components from LLM
            llm_response = get_llm_response(prompt)
            if llm_response:
                logger.info(f"Raw LLM response: {llm_response}")
                # Extract JSON from markdown code blocks if present
                if llm_response.startswith("```json"):
                    # Find the content between the first and last backticks
                    json_content = llm_response.split("```json")[1].split("```")[0].strip()
                    llm_response = json_content
                # Try to parse the LLM response as JSON
                reformatted_components = json.loads(llm_response)
                if isinstance(reformatted_components, list):
                    use_llm_output = True
                    logger.info("Successfully reformatted components using LLM")
                else:
                    logger.warning("LLM response was not a list")
        except (LlmApiError, json.JSONDecodeError) as e:
            logger.warning(f"LLM reformatting failed: {e}. Falling back to direct processing.")

        # Process components, applying fallback for invalid ones
        components_to_process = reformatted_components if use_llm_output else raw_components
        for i, comp_data in enumerate(components_to_process):
            if not isinstance(comp_data, dict):
                 logger.warning(f"Component item at index {i} is not a dictionary, skipping.")
                 errors.append(f"Item at index {i} is not a dictionary: {comp_data}")
                 # Create a fallback even for non-dict items
                 fallback_desc = f"Invalid component data (not a dictionary): {json.dumps(comp_data)}"
                 processed_components.append(BOMComponent(
                     qty=1, 
                     description=fallback_desc, 
                     package="unknown", 
                     possible_mpn=None, 
                     notes=None
                 ))
                 continue

            try:
                # Try to validate against the BOMComponent schema
                validated_comp = BOMComponent.model_validate(comp_data)
                processed_components.append(validated_comp)
            except ValidationError as e:
                logger.warning(f"Validation failed for component at index {i}: {e}. Creating fallback.")
                # Create fallback description containing original data
                fallback_desc = f"Original Data (validation failed): {json.dumps(comp_data)}"
                errors.append(f"Validation failed for component {i}: {e}")
                
                # Create fallback component
                processed_components.append(BOMComponent(
                    qty=comp_data.get("qty", 1) if isinstance(comp_data.get("qty"), int) else 1, # Try to get qty, else default 1
                    description=fallback_desc,
                    package=str(comp_data.get("package", "unknown")), # Try to get package, else default 'unknown'
                    possible_mpn=str(comp_data.get("possible_mpn")) if "possible_mpn" in comp_data else None,
                    notes=str(comp_data.get("notes")) if "notes" in comp_data else None
                ))

        # Truncate to 20 components if needed (after processing)
        truncation_info = None
        if len(processed_components) > 20:
            truncation_info = f"BOM truncated from {len(processed_components)} to 20 components after processing."
            logger.info(truncation_info)
            processed_components = processed_components[:20]
        
        # Generate project ID using UUID
        project_id = str(uuid.uuid4())
        
        logger.info(f"Creating project {project_id} with name: {project_name} and description: {project_description}")
        logger.info(f"Processed BOM has {len(processed_components)} components.")
        if errors:
             logger.warning(f"Encountered {len(errors)} issues during component processing for project {project_id}.")

        # Create project in database
        db_project = crud_create_project(
            db=db,
            project_id=project_id,
            name=project_name,
            description=project_description,
            status='queued'
        )
        logger.info(f"Project entry created for {project_id}")
        
        # Create BOM items using processed components
        for i, comp in enumerate(processed_components):
            logger.info(f"Creating BOM item {i+1}/{len(processed_components)} for project {project_id}: Qty={comp.qty}, Desc={comp.description[:50]}...")
            create_bom_item(
                db=db,
                item=comp,
                project_id=project_id
            )
        logger.info(f"All BOM items created for {project_id}")
        
        # Commit all changes
        db.commit()
        logger.info(f"Project {project_id} committed successfully.")
        
        return {
            "project_id": project_id,
            "truncation_info": truncation_info,
            "processing_warnings": errors if errors else None
        }
    except Exception as e:
        # Rollback on error
        db.rollback()
        logger.error(f"Error creating project: {e}", exc_info=True)
        # Check if it's an HTTPException we raised intentionally
        if isinstance(e, HTTPException):
             raise e
        # Otherwise, return a generic 500 error
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get project details and BOM data.
    For queued projects, returns position in queue.
    For finished projects, returns matched components and potential matches.
    """
    # Get project from database
    db_project = get_project_by_id(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create a Mouser API cache manager
    mouser_cache_manager = MouserApiCacheManager()

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
            project_name=db_project.name,
            components=components,
            project_description=db_project.description
        )
        
        return {
            "status": "queued",
            "position": position,
            "total_in_queue": total_in_queue,
            "bom": bom.model_dump()
        }
    
    # Handle processing projects
    elif db_project.status == 'processing':
        # Get all BOM items with their current matches and components
        results_data = get_finished_project_data(db=db, project_id=project_id)
        
        # Reconstruct matched components (even if not fully matched yet)
        matched_components = []
        for db_bom_item, db_match, db_component in results_data:
            # Start with base BOM item data
            component_dict = {
                "qty": db_bom_item.quantity,
                "description": db_bom_item.description,
                "possible_mpn": db_bom_item.notes,  # notes field used for possible_mpn
                "package": db_bom_item.package,
                "mouser_part_number": None,
                "manufacturer_part_number": None,
                "manufacturer_name": None,
                "mouser_description": None,
                "datasheet_url": None,
                "price": None,
                "availability": None,
                "match_status": "pending", # Default status for processing items
                "potential_matches": None
            }
            
            # Set the match status based on db_match presence first
            if db_match:
                component_dict["match_status"] = db_match.match_status
            
            # If we have a match and component, add the component data
            if db_match and db_component:
                # Convert price to float for API response
                api_price = None
                if db_component.price is not None:
                    try:
                        # Try to convert Decimal to float
                        api_price = float(db_component.price)
                        logging.info(f"Successfully converted price {db_component.price} to float: {api_price}")
                    except (ValueError, TypeError) as e:
                        logging.error(f"Failed to convert price {db_component.price} to float: {e}")
                
                component_dict.update({
                    "mouser_part_number": db_component.mouser_part_number,
                    "manufacturer_part_number": db_component.manufacturer_part_number,
                    "manufacturer_name": db_component.manufacturer_name,
                    "mouser_description": db_component.description,
                    "datasheet_url": db_component.datasheet_url,
                    "price": api_price,
                    "availability": db_component.availability,
                })
            
            # Get potential matches for this BOM item
            db_potential_matches = get_potential_matches_for_bom_item(db=db, bom_item_id=db_bom_item.bom_item_id)
            if db_potential_matches:
                potential_matches = []
                for db_potential in db_potential_matches:
                    # Get component details if available
                    linked_component = None
                    
                    # First check if component_id is already set on the potential match
                    if db_potential.component_id:
                        # Use the directly linked component if available
                        linked_component = db.query(Component).get(db_potential.component_id)
                    
                    # If no direct link, try to find by MPN
                    if not linked_component:
                        linked_component = get_component_by_mpn(db, db_potential.manufacturer_part_number)
                    
                    # Create potential match dict
                    potential_match = {
                        "rank": db_potential.rank,
                        "manufacturer_part_number": db_potential.manufacturer_part_number,
                        "reason": db_potential.reason,
                        "selection_state": db_potential.selection_state,
                        "mouser_part_number": None,
                        "manufacturer_name": None,
                        "mouser_description": None,
                        "datasheet_url": None,
                        "price": None,
                        "availability": None,
                        "component_id": None
                    }
                    
                    # Add component details if found in database
                    if linked_component:
                        # Convert price to float for API response
                        api_price = None
                        if linked_component.price is not None:
                            try:
                                # Try to convert Decimal to float
                                api_price = float(linked_component.price)
                                logging.info(f"Successfully converted price {linked_component.price} to float: {api_price}")
                            except (ValueError, TypeError) as e:
                                logging.error(f"Failed to convert price {linked_component.price} to float: {e}")
                                
                        potential_match.update({
                            "mouser_part_number": linked_component.mouser_part_number,
                            "manufacturer_name": linked_component.manufacturer_name,
                            "mouser_description": linked_component.description,
                            "datasheet_url": linked_component.datasheet_url,
                            "price": api_price,
                            "availability": linked_component.availability,
                            "component_id": linked_component.component_id
                        })
                    else:
                        # If not in database, try to fetch from Mouser API
                        try:
                            mouser_data = search_mouser_by_mpn(
                                mpn=db_potential.manufacturer_part_number,
                                cache_manager=mouser_cache_manager,
                                db=db
                            )
                            if mouser_data:
                                # Convert price if needed
                                price = mouser_data.get('Price')
                                logging.info(f"===== PROJECT PRICE DEBUG =====")
                                logging.info(f"MPN: {db_potential.manufacturer_part_number}")
                                logging.info(f"Raw mouser_data price: {mouser_data.get('Price')}")
                                logging.info(f"Price type: {type(mouser_data.get('Price'))}")
                                logging.info(f"Final price value: {price}")
                                logging.info(f"===== END PROJECT PRICE DEBUG =====")
                                # Price is already a float or None from mouser_api.py
                                
                                potential_match.update({
                                    "mouser_part_number": mouser_data.get('Mouser Part Number'),
                                    "manufacturer_name": mouser_data.get('Manufacturer Name'),
                                    "mouser_description": mouser_data.get('Mouser Description'),
                                    "datasheet_url": mouser_data.get('Datasheet URL'),
                                    "price": price,
                                    "availability": mouser_data.get('Availability')
                                })
                                
                                # First check if component already exists in database
                                existing_component = db.query(Component).filter(
                                    Component.mouser_part_number == mouser_data.get('Mouser Part Number')
                                ).first()
                                
                                if existing_component:
                                    # Use existing component
                                    logging.info(f"Found existing component for mouser part number {mouser_data.get('Mouser Part Number')}")
                                    component_id = existing_component.component_id
                                    potential_match["component_id"] = component_id
                                    
                                    # Update component data to ensure it's current
                                    existing_component.manufacturer_part_number = db_potential.manufacturer_part_number
                                    existing_component.manufacturer_name = mouser_data.get('Manufacturer Name')
                                    existing_component.description = mouser_data.get('Mouser Description')
                                    existing_component.datasheet_url = mouser_data.get('Datasheet URL')
                                    # Convert price to Decimal for database storage
                                    if price is not None:
                                        existing_component.price = Decimal(str(price))
                                    else:
                                        existing_component.price = None
                                    existing_component.availability = mouser_data.get('Availability')
                                    existing_component.last_updated = datetime.datetime.now()
                                    
                                    # Update the potential match record with the component_id
                                    db_potential.component_id = component_id
                                    db.flush()
                                else:
                                    # Create a new component record in the database
                                    new_component = Component(
                                        mouser_part_number=mouser_data.get('Mouser Part Number'),
                                        manufacturer_part_number=db_potential.manufacturer_part_number,
                                        manufacturer_name=mouser_data.get('Manufacturer Name'),
                                        description=mouser_data.get('Mouser Description'),
                                        datasheet_url=mouser_data.get('Datasheet URL'),
                                        # Convert price to Decimal for database storage
                                        price=Decimal(str(price)) if price is not None else None,
                                        availability=mouser_data.get('Availability')
                                    )
                                    db.add(new_component)
                                    db.flush()  # Get the component ID without committing
                                    potential_match["component_id"] = new_component.component_id
                                    
                                    # Update the potential match record with the component_id
                                    db_potential.component_id = new_component.component_id
                                    db.flush()
                        except Exception as e:
                            logger.warning(f"Failed to fetch component details from Mouser for MPN {db_potential.manufacturer_part_number}: {e}")
                            # Continue with partial data
                    
                    potential_matches.append(PotentialMatch(**potential_match))
                
                component_dict["potential_matches"] = potential_matches
            
            matched_components.append(MatchedComponent(**component_dict))
            
        # Create MatchedBOM (partially filled)
        # Use current time for match_date as it's ongoing
        current_time_iso = datetime.datetime.now().isoformat()
        matched_bom = MatchedBOM(
            components=matched_components,
            project_description=db_project.description,
            match_date=current_time_iso, # Indicate it's an in-progress snapshot
            match_status=db_project.status, # Keep 'processing' status
            project_name=db_project.name
        )
        
        return {
            "status": "processing",
            "bom": matched_bom.model_dump()
        }
    
    # Handle errored projects
    elif db_project.status == 'error':
        # Similar to processing, return the original BOM and indicate error status
        db_items = get_bom_items_for_project(db=db, project_id=project_id)
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
            project_name=db_project.name,
            components=components,
            project_description=db_project.description
        )
        
        return {
            "status": "error",
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
                "mouser_part_number": None,
                "manufacturer_part_number": None,
                "manufacturer_name": None,
                "mouser_description": None,
                "datasheet_url": None,
                "price": None,
                "availability": None,
                "match_status": "no_match_record", # Default status if no match record found
                "potential_matches": None
            }
            
            # Set the match status based on db_match presence first
            if db_match:
                component_dict["match_status"] = db_match.match_status
            
            # If we have a match and component, add the component data
            if db_match and db_component:
                # Convert price to float for API response
                api_price = None
                if db_component.price is not None:
                    try:
                        # Try to convert Decimal to float
                        api_price = float(db_component.price)
                        logging.info(f"Successfully converted price {db_component.price} to float: {api_price}")
                    except (ValueError, TypeError) as e:
                        logging.error(f"Failed to convert price {db_component.price} to float: {e}")
                
                component_dict.update({
                    "mouser_part_number": db_component.mouser_part_number,
                    "manufacturer_part_number": db_component.manufacturer_part_number,
                    "manufacturer_name": db_component.manufacturer_name,
                    "mouser_description": db_component.description,
                    "datasheet_url": db_component.datasheet_url,
                    "price": api_price,
                    "availability": db_component.availability,
                })
            
            # Get potential matches for this BOM item
            db_potential_matches = get_potential_matches_for_bom_item(db=db, bom_item_id=db_bom_item.bom_item_id)
            if db_potential_matches:
                potential_matches = []
                for db_potential in db_potential_matches:
                    # Get component details if available
                    linked_component = None
                    
                    # First check if component_id is already set on the potential match
                    if db_potential.component_id:
                        # Use the directly linked component if available
                        linked_component = db.query(Component).get(db_potential.component_id)
                    
                    # If no direct link, try to find by MPN
                    if not linked_component:
                        linked_component = get_component_by_mpn(db, db_potential.manufacturer_part_number)
                    
                    # Create potential match dict
                    potential_match = {
                        "rank": db_potential.rank,
                        "manufacturer_part_number": db_potential.manufacturer_part_number,
                        "reason": db_potential.reason,
                        "selection_state": db_potential.selection_state,
                        "mouser_part_number": None,
                        "manufacturer_name": None,
                        "mouser_description": None,
                        "datasheet_url": None,
                        "price": None,
                        "availability": None,
                        "component_id": None
                    }
                    
                    # Add component details if found in database
                    if linked_component:
                        # Convert price to float for API response
                        api_price = None
                        if linked_component.price is not None:
                            try:
                                # Try to convert Decimal to float
                                api_price = float(linked_component.price)
                                logging.info(f"Successfully converted price {linked_component.price} to float: {api_price}")
                            except (ValueError, TypeError) as e:
                                logging.error(f"Failed to convert price {linked_component.price} to float: {e}")
                                
                        potential_match.update({
                            "mouser_part_number": linked_component.mouser_part_number,
                            "manufacturer_name": linked_component.manufacturer_name,
                            "mouser_description": linked_component.description,
                            "datasheet_url": linked_component.datasheet_url,
                            "price": api_price,
                            "availability": linked_component.availability,
                            "component_id": linked_component.component_id
                        })
                    else:
                        # If not in database, try to fetch from Mouser API
                        try:
                            mouser_data = search_mouser_by_mpn(
                                mpn=db_potential.manufacturer_part_number,
                                cache_manager=mouser_cache_manager,
                                db=db
                            )
                            if mouser_data:
                                # Convert price if needed
                                price = mouser_data.get('Price')
                                logging.info(f"===== PROJECT PRICE DEBUG =====")
                                logging.info(f"MPN: {db_potential.manufacturer_part_number}")
                                logging.info(f"Raw mouser_data price: {mouser_data.get('Price')}")
                                logging.info(f"Price type: {type(mouser_data.get('Price'))}")
                                logging.info(f"Final price value: {price}")
                                logging.info(f"===== END PROJECT PRICE DEBUG =====")
                                # Price is already a float or None from mouser_api.py
                                
                                potential_match.update({
                                    "mouser_part_number": mouser_data.get('Mouser Part Number'),
                                    "manufacturer_name": mouser_data.get('Manufacturer Name'),
                                    "mouser_description": mouser_data.get('Mouser Description'),
                                    "datasheet_url": mouser_data.get('Datasheet URL'),
                                    "price": price,
                                    "availability": mouser_data.get('Availability')
                                })
                                
                                # First check if component already exists in database
                                existing_component = db.query(Component).filter(
                                    Component.mouser_part_number == mouser_data.get('Mouser Part Number')
                                ).first()
                                
                                if existing_component:
                                    # Use existing component
                                    logging.info(f"Found existing component for mouser part number {mouser_data.get('Mouser Part Number')}")
                                    component_id = existing_component.component_id
                                    potential_match["component_id"] = component_id
                                    
                                    # Update component data to ensure it's current
                                    existing_component.manufacturer_part_number = db_potential.manufacturer_part_number
                                    existing_component.manufacturer_name = mouser_data.get('Manufacturer Name')
                                    existing_component.description = mouser_data.get('Mouser Description')
                                    existing_component.datasheet_url = mouser_data.get('Datasheet URL')
                                    # Convert price to Decimal for database storage
                                    if price is not None:
                                        existing_component.price = Decimal(str(price))
                                    else:
                                        existing_component.price = None
                                    existing_component.availability = mouser_data.get('Availability')
                                    existing_component.last_updated = datetime.datetime.now()
                                    
                                    # Update the potential match record with the component_id
                                    db_potential.component_id = component_id
                                    db.flush()
                                else:
                                    # Create a new component record in the database
                                    new_component = Component(
                                        mouser_part_number=mouser_data.get('Mouser Part Number'),
                                        manufacturer_part_number=db_potential.manufacturer_part_number,
                                        manufacturer_name=mouser_data.get('Manufacturer Name'),
                                        description=mouser_data.get('Mouser Description'),
                                        datasheet_url=mouser_data.get('Datasheet URL'),
                                        # Convert price to Decimal for database storage
                                        price=Decimal(str(price)) if price is not None else None,
                                        availability=mouser_data.get('Availability')
                                    )
                                    db.add(new_component)
                                    db.flush()  # Get the component ID without committing
                                    potential_match["component_id"] = new_component.component_id
                                    
                                    # Update the potential match record with the component_id
                                    db_potential.component_id = new_component.component_id
                                    db.flush()
                        except Exception as e:
                            logger.warning(f"Failed to fetch component details from Mouser for MPN {db_potential.manufacturer_part_number}: {e}")
                            # Continue with partial data
                    
                    potential_matches.append(PotentialMatch(**potential_match))
                
                component_dict["potential_matches"] = potential_matches
            
            matched_components.append(MatchedComponent(**component_dict))
        
        # Get match date from project end time
        match_date = (
            db_project.end_time.isoformat() 
            if db_project.end_time 
            else datetime.datetime.now().isoformat()
        )
        
        # Create MatchedBOM
        matched_bom = MatchedBOM(
            project_name=db_project.name,
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