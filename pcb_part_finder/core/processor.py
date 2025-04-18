#!/usr/bin/env python3

import logging
from typing import List, Dict, Any
import datetime # Add datetime import for error handling
import concurrent.futures # Added for concurrency
import threading # Added for concurrency (though not directly used yet)
# Removed sessionmaker import from sqlalchemy.orm as we'll import SessionLocal
# from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import Session # Keep Session for type hints if needed elsewhere
# Import necessary CRUD functions and models
from pcb_part_finder.db.models import Project, BomItem, Component, BomItemMatch 
from pcb_part_finder.db.crud import (
    get_or_create_component, 
    create_bom_item_match, 
    update_project_status, # Import for error handling
    get_component_by_mpn # Import the new function
) 
# Import the session factory
from pcb_part_finder.core.database import SessionLocal
from .data_loader import load_project_data_from_db
# Remove the bulk save function import, no longer needed
# from .output_writer import save_bom_results_to_db 
from . import llm_handler
from . import mouser_api
from .llm_handler import LlmApiError
from .mouser_api import MouserApiError
from .cache_manager import MouserApiCacheManager # Added

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instantiate the cache manager at the module level
mouser_cache_manager = MouserApiCacheManager()

# Define the worker function stub
def _process_single_bom_item(
    bom_item: BomItem,
    project_name: str,
    project_description: str,
    mouser_cache_manager: MouserApiCacheManager,
    full_bom_list: List[Dict[str, Any]] # Added argument for the full BOM list
    # Removed db_session_factory parameter
) -> str:
    """
    Processes a single BOM item: generates search terms, queries Mouser,
    evaluates results, potentially finds/creates a component record,
    and creates a BomItemMatch linking the BomItem to the Component.

    This function runs in a separate thread managed by ThreadPoolExecutor.
    It creates and manages its own database session using SessionLocal.

    Args:
        bom_item: The specific BomItem ORM object to process.
        project_name: The name of the parent project (for context).
        project_description: The description of the parent project (for context).
        mouser_cache_manager: The shared MouserApiCacheManager instance.
        full_bom_list: A list of dictionaries, each representing a part in the original BOM.
            Used for providing context to the LLM evaluation prompt.

    Returns:
        str: A status string indicating the outcome (e.g., 'matched',
             'search_term_failed', 'no_keyword_results', 'evaluation_failed',
             'mpn_lookup_failed', 'component_db_error', 'llm_error',
             'mouser_error', 'processing_error', 'db_save_error', 'stub_ok').
             Statuses indicating failure should generally start with 'error' or 'fail'.
    """
    # Initialize item-specific variables
    part_info = {
        'Description': bom_item.description or '',
        'Possible MPN': bom_item.notes or '', # Assuming notes field holds input MPN
        'Package': bom_item.package or '',
        'Notes/Source': bom_item.notes or '' # Duplicating notes for context
    }
    status = 'pending' # Initial status
    component_id = None
    component_record = None # Initialize to None

    with SessionLocal() as db: # Create session scope for this worker
        logger.info(f"Worker processing BOM item {bom_item.bom_item_id} using session {id(db)}")
        
        try:
            # Step 2: Generate Search Terms
            search_terms = []
            try:
                search_prompt = llm_handler.format_search_term_prompt(part_info)
                llm_response_terms = llm_handler.get_llm_response(search_prompt)
                search_terms = llm_handler.parse_search_terms(llm_response_terms)
                if not search_terms:
                    logger.warning(f"No search terms generated for item {bom_item.bom_item_id}")
                    status = 'search_term_failed'
            except LlmApiError as e:
                logger.error(f"LLM API error generating search terms for item {bom_item.bom_item_id}: {e}")
                status = 'llm_error'
            except Exception as e:
                logger.error(f"Unexpected error generating search terms for item {bom_item.bom_item_id}: {e}", exc_info=True)
                status = 'processing_error' # Or a more specific status?

            # Step 3: Perform Mouser Keyword Search
            mouser_results = []
            unique_mouser_part_numbers = set()
            if status == 'pending' and search_terms:
                try:
                    for term in search_terms:
                        # Pass cache manager and the worker's db session
                        results = mouser_api.search_mouser_by_keyword(
                            keyword=term,
                            cache_manager=mouser_cache_manager,
                            db=db
                        )
                        for part in results:
                            mouser_part_number = part.get('MouserPartNumber')
                            if mouser_part_number and mouser_part_number not in unique_mouser_part_numbers:
                                unique_mouser_part_numbers.add(mouser_part_number)
                                mouser_results.append(part)
                    if not mouser_results:
                        logger.warning(f"No unique Mouser results found for item {bom_item.bom_item_id}")
                        status = 'no_keyword_results'
                except MouserApiError as e:
                    logger.error(f"Mouser API error during keyword search for item {bom_item.bom_item_id}: {e}")
                    status = 'mouser_error'
                except Exception as e:
                    logger.error(f"Unexpected error during Mouser keyword search for item {bom_item.bom_item_id}: {e}", exc_info=True)
                    status = 'processing_error' 

            # Step 4: Evaluate Search Results with LLM
            chosen_mpn = None
            if status == 'pending' and mouser_results:
                try:
                    eval_prompt = llm_handler.format_evaluation_prompt(
                        part_info, 
                        project_name,
                        project_description, 
                        full_bom_list, # Pass the full BOM list here
                        mouser_results 
                    )
                    llm_response_eval = llm_handler.get_llm_response(eval_prompt)
                    chosen_mpn = llm_handler.extract_mpn_from_eval(llm_response_eval)
                    if not chosen_mpn:
                        logger.warning(f"LLM did not select MPN for item {bom_item.bom_item_id}")
                        status = 'evaluation_failed'
                except LlmApiError as e:
                    logger.error(f"LLM API error during evaluation for item {bom_item.bom_item_id}: {e}")
                    status = 'llm_error'
                except Exception as e:
                    logger.error(f"Unexpected error during LLM evaluation for item {bom_item.bom_item_id}: {e}", exc_info=True)
                    status = 'processing_error' 

            # Step 5: Check DB / Get Final Part Details from Mouser by MPN
            if status == 'pending' and chosen_mpn:
                try:
                    # First, check if the component already exists in our DB
                    component_record = get_component_by_mpn(db, chosen_mpn)
                    if component_record:
                        logger.info(f"Found existing component in DB for MPN {chosen_mpn} (ID: {component_record.component_id}) for item {bom_item.bom_item_id}")
                        status = 'matched'
                        component_id = component_record.component_id
                    else:
                        # If not in DB, call Mouser API
                        logger.info(f"MPN {chosen_mpn} not found in DB for item {bom_item.bom_item_id}, querying Mouser...")
                        final_part_details = mouser_api.search_mouser_by_mpn(
                            mpn=chosen_mpn,
                            cache_manager=mouser_cache_manager,
                            db=db
                        )
                        if final_part_details:
                            # Found via Mouser API, now get/create the component record in DB
                            component_data = {
                                'mouser_part_number': final_part_details.get('Mouser Part Number'),
                                'manufacturer_part_number': final_part_details.get('Manufacturer Part Number'), # Should match chosen_mpn
                                'manufacturer_name': final_part_details.get('Manufacturer Name'),
                                'description': final_part_details.get('Mouser Description'),
                                'datasheet_url': final_part_details.get('Datasheet URL'),
                                'price': final_part_details.get('Price'),
                                'availability': final_part_details.get('Availability'),
                            }
                            component_data = {k: v for k, v in component_data.items() if v is not None}
                            component_record = get_or_create_component(db, component_data)
                            if component_record:
                                logger.info(f"Created/Found component record for MPN {chosen_mpn} (ID: {component_record.component_id}) after Mouser lookup for item {bom_item.bom_item_id}")
                                status = 'matched'
                                component_id = component_record.component_id
                            else:
                                logger.error(f"Failed to get/create component for item {bom_item.bom_item_id}, MPN {chosen_mpn} after Mouser lookup")
                                status = 'component_db_error'
                        else:
                            logger.warning(f"Mouser MPN search failed for MPN '{chosen_mpn}' (item {bom_item.bom_item_id})")
                            status = 'mpn_lookup_failed'
                except MouserApiError as e:
                    logger.error(f"Mouser API error during MPN search for item {bom_item.bom_item_id}, MPN {chosen_mpn}: {e}")
                    status = 'mouser_error'
                except SQLAlchemyError as e:
                    logger.error(f"Database error during component check/creation for item {bom_item.bom_item_id}, MPN {chosen_mpn}: {e}", exc_info=True)
                    status = 'component_db_error' # Reuse status or create a new one like 'db_error'?
                    db.rollback() # Rollback within this step if possible
                except Exception as e:
                    logger.error(f"Unexpected error during component check/creation for item {bom_item.bom_item_id}, MPN {chosen_mpn}: {e}", exc_info=True)
                    status = 'processing_error'
                    db.rollback() # Rollback on unexpected errors too

            # Step 6: Create BomItemMatch record
            # Ensure status is not 'pending' before saving match
            if status == 'pending':
                logger.error(f"Item {bom_item.bom_item_id} reached save point with unexpected 'pending' status. Setting to 'error'.")
                status = 'error'
            
            try:
                # TODO: Consider if we need to delete/update existing matches if reprocessing
                create_bom_item_match(
                    db=db,
                    bom_item_id=bom_item.bom_item_id,
                    component_id=component_id, # Will be None if no match/component created
                    match_status=status
                )
                db.commit() # Commit the match creation for this item
                logger.info(f"Saved result for item {bom_item.bom_item_id} with status: {status}")
            except SQLAlchemyError as db_err:
                logger.error(f"Database error saving final result for item {bom_item.bom_item_id}: {db_err}", exc_info=True)
                db.rollback() # Rollback the match creation commit
                status = 'db_save_error' # Overwrite status to reflect the final failure
            except Exception as e:
                logger.error(f"Unexpected error saving final result for item {bom_item.bom_item_id}: {e}", exc_info=True)
                db.rollback()
                status = 'processing_error' # Or db_save_error?

        except Exception as outer_err: # Catch any unexpected errors in the overall worker logic flow
            logger.error(f"Unhandled exception in worker for item {bom_item.bom_item_id}: {outer_err}", exc_info=True)
            status = 'worker_uncaught_exception'
            try:
                db.rollback() # Attempt rollback if session is still active
            except Exception as rb_err:
                logger.error(f"Error attempting rollback after unhandled worker exception for item {bom_item.bom_item_id}: {rb_err}")

        # Return the final status determined by the processing steps
        return status

def process_project_from_db(
    project_id: str,
    # Removed db_session_factory parameter from signature
    max_workers: int = 5
) -> bool:
    """
    Processes a project by finding matching components for its Bill of Materials (BOM) items.
    It loads project data, then processes each BOM item concurrently using a ThreadPoolExecutor.
    Each worker thread handles one BOM item independently, using its own database session.

    Results (BomItemMatch records) are intended to be created by the worker function.
    This function orchestrates the workers, collects their final statuses, and updates
    the overall project status ('completed', 'completed_with_errors', or 'error').

    Note: The previous concept of shared `selected_part_details` context across items
    has been removed due to the complexities of managing shared state in concurrency.
    Each item is processed based on its own info and the project description.

    Args:
        project_id: The ID of the project to process
        max_workers: The maximum number of worker threads to use for processing BOM items.

    Returns:
        bool: True if the project processing setup and task orchestration completed
              successfully (even if some individual BOM items failed processing).
              False if a fatal error occurred during the initial setup (e.g., loading
              project data or creating the thread pool), preventing processing from starting.
    """
    project = None
    bom_items = [] # Initialize bom_items
    try:
        logger.info(f"Starting processing for project {project_id} using up to {max_workers} workers.")

        # Load project data and BOM items using a dedicated session
        with SessionLocal() as db: # Use SessionLocal here
            project, bom_items = load_project_data_from_db(project_id, db)

        if not project:
            logger.error(f"Could not load project {project_id} from database")
            # No need to update status here, as it likely never started
            return False # Cannot proceed
            
        logger.info(f"Loaded project {project_id} with {len(bom_items)} BOM items")
        
        if bom_items:
            # Initialize list for selected parts context (still needed for LLM) - Rethink concurrency implications later
            # selected_part_details = [] # Removed for now, needs thread-safe handling if required across items

            # Prepare lists/dicts for collecting results
            results = []
            failed_item_ids = []
            future_to_bom_item_id = {}

            # Convert BomItem objects to simple dictionaries for passing to worker
            # Include fields needed by the LLM prompt for the BOM list context
            bom_list_as_dicts = [
                {
                    'Description': item.description or 'N/A',
                    'Package': item.package or 'N/A',
                    'Possible MPN': item.notes or 'N/A' # Assuming notes field holds input MPN
                } for item in bom_items
            ]

            # Use ThreadPoolExecutor for concurrent processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tasks for each BOM item
                logger.info(f"Submitting {len(bom_items)} tasks to the executor for project {project_id}.")
                for bom_item in bom_items:
                    future = executor.submit(
                        _process_single_bom_item,
                        bom_item,
                        project.name,
                        project.description,
                        mouser_cache_manager, # Pass the shared cache manager
                        bom_list_as_dicts # Pass the converted full BOM list
                    )
                    future_to_bom_item_id[future] = bom_item.bom_item_id

                # Process results as they complete
                processed_count = 0
                for future in concurrent.futures.as_completed(future_to_bom_item_id):
                    bom_item_id = future_to_bom_item_id[future]
                    processed_count += 1
                    try:
                        status = future.result() # Get result or raise exception
                        results.append(status)
                        logger.info(f"({processed_count}/{len(bom_items)}) Item {bom_item_id} completed with status: {status}")
                        # Define failure criteria (adjust as needed)
                        if isinstance(status, str) and (
                            status.startswith('error') or 
                            status.startswith('fail') or 
                            status == 'component_db_error' or 
                            status == 'mpn_lookup_failed' or
                            status == 'llm_error' or
                            status == 'mouser_error' or
                            status == 'processing_error'
                            # Add other failure statuses from _process_single_bom_item
                            ):
                            failed_item_ids.append(bom_item_id)

                    except Exception as exc:
                        logger.error(f"({processed_count}/{len(bom_items)}) Item {bom_item_id} generated an uncaught exception: {exc}", exc_info=True)
                        failed_item_ids.append(bom_item_id)
                        results.append('worker_exception') # Store generic failure status

                # Log summary after processing all items
                logger.info(f"Finished processing all {len(bom_items)} items for project {project_id}.")
                if failed_item_ids:
                    logger.warning(f"Project {project_id} had {len(failed_item_ids)} failed items: {failed_item_ids}")
                else:
                    logger.info(f"Project {project_id} completed with no failed items.")

            # --- All tasks submitted and processed --- 
            # Determine final project status based on collected results
            final_project_status = 'finished' # Use 'finished' regardless of individual errors

            logger.info(f"Processing finished for project {project_id}. Final Status: {final_project_status}. Failed items ({len(failed_item_ids)}): {failed_item_ids}")

            # Update the project status in the database using a new session
            try:
                with SessionLocal() as db:
                    update_project_status(
                        db=db,
                        project_id=project_id, # project_id is available from the function args
                        new_status=final_project_status,
                        end_time=datetime.datetime.utcnow()
                    )
                    db.commit()
                logger.info(f"Successfully updated project {project_id} status to '{final_project_status}'")
            except Exception as status_update_err:
                logger.error(f"Failed to update final project status for {project_id} to '{final_project_status}': {status_update_err}", exc_info=True)
                # Do not re-raise, allow function to return True if setup was ok

        else:
            logger.info(f"Project {project_id} has no BOM items to process.")
            # TODO: Consider updating project status to 'completed' or similar here?
            # Update status to finished if no items
            final_project_status = 'finished' # Align with frontend
            try:
                with SessionLocal() as db:
                    update_project_status(
                        db=db,
                        project_id=project_id,
                        new_status=final_project_status,
                        end_time=datetime.datetime.utcnow()
                    )
                    db.commit()
                logger.info(f"Successfully updated project {project_id} (no items) status to '{final_project_status}'")
            except Exception as status_update_err:
                logger.error(f"Failed to update final project status for {project_id} (no items) to '{final_project_status}': {status_update_err}", exc_info=True)

        # --- Loop/Executor finished or no items --- 

        # Return True because the setup and task submission/processing loop completed (even if some items failed).
        # False is returned only if a fatal error occurred during setup.
        return True

    except Exception as e:
        # Catch fatal errors occurring during setup (loading, executor creation)
        logger.error(f"Fatal error setting up processing for project {project_id}: {e}", exc_info=True)
        final_project_status = 'error' # Status in case of fatal setup error
        # Attempt to update project status to 'error' using a new session
        try:
            with SessionLocal() as db_err: # Use SessionLocal here too
                 # Ensure project was loaded before trying to access its ID
                 # Use the project_id passed into the function, as project might be None
                 if project_id:
                     update_project_status(
                         db=db_err,
                         project_id=project_id,
                         new_status=final_project_status,
                         end_time=datetime.datetime.utcnow() # Use utcnow
                     )
                     db_err.commit()
                     logger.info(f"Successfully updated project {project_id} status to '{final_project_status}' after setup error.")
                 else:
                     # If project loading failed, we might not have the ID easily,
                     # log that status update couldn't happen.
                     logger.error(f"Could not update project status to '{final_project_status}' as project_id was missing.")

        except Exception as status_update_err:
            logger.error(f"Failed to update project {project_id} status to '{final_project_status}' after fatal setup error: {status_update_err}", exc_info=True)
            # db_err.rollback() happens automatically exiting 'with' block on error

        return False # Indicate fatal setup failure 