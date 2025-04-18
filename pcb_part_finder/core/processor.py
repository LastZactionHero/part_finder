#!/usr/bin/env python3

import logging
from typing import List, Dict, Any
import datetime # Add datetime import for error handling
from sqlalchemy.orm import Session
# Import necessary CRUD functions and models
from pcb_part_finder.db.models import Project, BomItem, Component, BomItemMatch 
from pcb_part_finder.db.crud import (
    get_or_create_component, 
    create_bom_item_match, 
    update_project_status # Import for error handling
) 
from .data_loader import load_project_data_from_db
# Remove the bulk save function import, no longer needed
# from .output_writer import save_bom_results_to_db 
from . import llm_handler
from . import mouser_api
from .llm_handler import LlmApiError
from .mouser_api import MouserApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_project_from_db(project_id: str, db: Session) -> bool:
    """
    Process a project using data from the database, saving results progressively.
    
    Args:
        project_id: The ID of the project to process
        db: Database session to use for queries and updates
        
    Returns:
        bool: True if processing loop completed, False if an error occurred.
              Note: Individual items might still fail within a successful loop.
    """
    try:
        logger.info(f"Starting processing for project {project_id}")
        
        # Load project data and BOM items
        project, bom_items = load_project_data_from_db(project_id, db)
        
        if not project:
            logger.error(f"Could not load project {project_id} from database")
            return False # Cannot proceed
            
        logger.info(f"Loaded project {project_id} with {len(bom_items)} BOM items")
        
        # Initialize list for selected parts context (still needed for LLM)
        selected_part_details = []

        # Process BOM items with LLM and Mouser API
        for bom_item in bom_items:
            # Reset item-specific variables
            part_info = {
                'Description': bom_item.description or '',
                'Possible MPN': bom_item.notes or '', # Assuming notes field holds input MPN
                'Package': bom_item.package or '',
                'Notes/Source': bom_item.notes or '' # Duplicating notes for context
            }
            search_terms = []
            status = 'pending' # Initial status
            mouser_results = []
            unique_mouser_part_numbers = set()
            chosen_mpn = None
            final_part_details = None
            component_id = None
            
            try:
                # Step 2: Generate Search Terms
                search_prompt = llm_handler.format_search_term_prompt(part_info)
                llm_response_terms = llm_handler.get_llm_response(search_prompt)
                search_terms = llm_handler.parse_search_terms(llm_response_terms)
                if not search_terms:
                    logger.warning(f"No search terms generated for item {bom_item.bom_item_id}")
                    status = 'search_term_failed'

                # Step 3: Perform Mouser Keyword Search
                if status == 'pending' and search_terms:
                    for term in search_terms:
                        results = mouser_api.search_mouser_by_keyword(term)
                        for part in results:
                            mouser_part_number = part.get('MouserPartNumber')
                            if mouser_part_number and mouser_part_number not in unique_mouser_part_numbers:
                                unique_mouser_part_numbers.add(mouser_part_number)
                                mouser_results.append(part)
                    if not mouser_results:
                        logger.warning(f"No unique Mouser results found for item {bom_item.bom_item_id}")
                        status = 'no_keyword_results'

                # Step 4: Evaluate Search Results with LLM
                if status == 'pending' and mouser_results:
                    eval_prompt = llm_handler.format_evaluation_prompt(
                        part_info, project.description, selected_part_details, mouser_results
                    )
                    llm_response_eval = llm_handler.get_llm_response(eval_prompt)
                    chosen_mpn = llm_handler.extract_mpn_from_eval(llm_response_eval)
                    if not chosen_mpn:
                        logger.warning(f"LLM did not select MPN for item {bom_item.bom_item_id}")
                        status = 'evaluation_failed'

                # Step 5: Get Final Part Details from Mouser by MPN
                if status == 'pending' and chosen_mpn:
                    final_part_details = mouser_api.search_mouser_by_mpn(chosen_mpn)
                    if final_part_details:
                        status = 'matched'
                    else:
                        logger.warning(f"Mouser MPN search failed for MPN '{chosen_mpn}' (item {bom_item.bom_item_id})")
                        status = 'mpn_lookup_failed'

            # Catch specific API errors during item processing
            except LlmApiError as e:
                logger.error(f"LLM API error processing item {bom_item.bom_item_id}: {e}")
                status = status if status != 'pending' else 'llm_error' # Keep specific status if set earlier
            except MouserApiError as e:
                logger.error(f"Mouser API error processing item {bom_item.bom_item_id}: {e}")
                status = status if status != 'pending' else 'mouser_error'
            except Exception as item_err: # Catch unexpected errors for this item
                logger.error(f"Unexpected error processing item {bom_item.bom_item_id}: {item_err}", exc_info=True)
                status = 'processing_error'
            
            # Step 6: Format and Store Result (Progressively)
            # --- Start DB interaction for this item ---
            try:
                component_record = None
                if status == 'matched' and final_part_details:
                    # Prepare data for the Component table
                    component_data = {
                        'mouser_part_number': final_part_details.get('Mouser Part Number'),
                        'manufacturer_part_number': final_part_details.get('Manufacturer Part Number'),
                        'manufacturer_name': final_part_details.get('Manufacturer Name'),
                        'description': final_part_details.get('Mouser Description'),
                        'datasheet_url': final_part_details.get('Datasheet URL'),
                        # Ensure price is Decimal compatible or None
                        'price': final_part_details.get('Price'), 
                        'availability': final_part_details.get('Availability'),
                        # Add other Component fields if needed
                    }
                    # Filter out None values before creating/updating
                    component_data = {k: v for k, v in component_data.items() if v is not None}

                    # Get or create the component record
                    component_record = get_or_create_component(db, component_data)
                    if component_record:
                        component_id = component_record.component_id
                        # Add details of the selected part for context
                        selected_part_details.append({
                            'Description': part_info.get('Description', ''),
                            'Manufacturer Part Number': final_part_details.get('Manufacturer Part Number')
                        })
                    else:
                        logger.error(f"Failed to get/create component for item {bom_item.bom_item_id}, MPN {chosen_mpn}")
                        status = 'component_db_error' # Update status if DB interaction failed
                
                # Ensure status is not 'pending' before saving match
                if status == 'pending':
                    logger.error(f"Item {bom_item.bom_item_id} reached save point with 'pending' status. Setting to 'error'.")
                    status = 'error' 
                    
                # Create the BomItemMatch record for THIS item
                # TODO: Consider if we need to delete/update existing matches if reprocessing
                create_bom_item_match(
                    db=db,
                    bom_item_id=bom_item.bom_item_id,
                    component_id=component_id, # Will be None if no match/component created
                    match_status=status 
                )
                
                # Commit the changes for this single item
                db.commit() 
                logger.info(f"Saved result for item {bom_item.bom_item_id} with status: {status}")

            except Exception as db_err:
                logger.error(f"Database error saving result for item {bom_item.bom_item_id}: {db_err}", exc_info=True)
                db.rollback() # Rollback commit for this item
                # We might want to set project status to error here, or just log and continue
                # For now, let the loop continue to try other items.
            # --- End DB interaction for this item ---

        # --- Loop finished ---
        
        # Remove the final bulk save - it's done progressively now
        # success = save_bom_results_to_db(project_id, bom_items_with_matches, db)

        logger.info(f"Finished processing loop for project {project_id}")
        # Return True to indicate the loop finished. The calling code should set final status.
        return True 
        
    except Exception as e:
        # Catch errors occurring outside the item loop (e.g., loading project)
        logger.error(f"Fatal error processing project {project_id}: {e}", exc_info=True)
        db.rollback() # Rollback any potential partial commits
        # Attempt to update project status to 'error'
        try:
            update_project_status(
                db=db,
                project_id=project_id,
                new_status='error',
                end_time=datetime.datetime.utcnow() # Use utcnow
            )
            db.commit()
        except Exception as status_update_err:
            logger.error(f"Failed to update project {project_id} status to 'error': {status_update_err}")
            db.rollback()
        return False # Indicate failure 