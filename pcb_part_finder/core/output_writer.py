"""Module for writing output data to CSV files."""

import csv
from typing import List, Dict, Any
import logging
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pcb_part_finder.db.models import BomItem, Component, BomItemMatch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the output CSV header
OUTPUT_HEADER = [
    'Qty',
    'Description',
    'Possible MPN',
    'Package',
    'Notes/Source',
    'Mouser Part Number',
    'Manufacturer Part Number',
    'Manufacturer Name',
    'Mouser Description',
    'Datasheet URL',
    'Price',
    'Availability',
    'Match Status'
]

class OutputWriterError(Exception):
    """Custom exception for output writing errors."""
    pass

def initialize_output_csv(filepath: str, header: List[str]) -> None:
    """Initialize the output CSV file with the header row.
    
    Args:
        filepath: Path to the output CSV file.
        header: List of column headers.
        
    Raises:
        OutputWriterError: If the file cannot be created or written to.
    """
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    except IOError as e:
        raise OutputWriterError(f"Error initializing output CSV: {e}")

def append_row_to_csv(filepath: str, data_dict: Dict[str, Any], header: List[str]) -> None:
    """Append a row of data to the output CSV file.
    
    Args:
        filepath: Path to the output CSV file.
        data_dict: Dictionary containing the row data.
        header: List of column headers to ensure correct field order.
        
    Raises:
        OutputWriterError: If the file cannot be written to or if data_dict is missing required fields.
    """
    try:
        # Verify all required fields are present
        missing_fields = [field for field in header if field not in data_dict]
        if missing_fields:
            raise OutputWriterError(f"Data missing required fields: {', '.join(missing_fields)}")
        
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writerow(data_dict)
    except IOError as e:
        raise OutputWriterError(f"Error appending to output CSV: {e}")
    except csv.Error as e:
        raise OutputWriterError(f"Error writing CSV row: {e}")

def write_output_csv(filepath: str, data_rows: List[Dict[str, Any]]) -> None:
    """Write multiple rows of data to a CSV file.
    
    Args:
        filepath: Path to the output CSV file.
        data_rows: List of dictionaries containing the row data.
        
    Raises:
        OutputWriterError: If the file cannot be written to or if any row is missing required fields.
    """
    try:
        # Initialize the CSV with header
        initialize_output_csv(filepath, OUTPUT_HEADER)
        
        # Write each row
        for row in data_rows:
            append_row_to_csv(filepath, row, OUTPUT_HEADER)
    except OutputWriterError as e:
        raise OutputWriterError(f"Error writing output CSV: {e}")

def save_bom_results_to_db(project_id: str, bom_items_with_matches: List[Dict], db: Session) -> bool:
    """
    Save BOM processing results to the database.
    
    Args:
        project_id: The ID of the project being processed
        bom_items_with_matches: List of dictionaries containing BOM items and their matches
        db: Database session to use for queries and updates
        
    Returns:
        bool: True if saving was successful, False otherwise
    """
    try:
        logger.info(f"Saving results for project {project_id} with {len(bom_items_with_matches)} items")
        
        for item_data in bom_items_with_matches:
            # Get the original BOM item
            bom_item = db.query(BomItem).filter(
                BomItem.project_id == project_id,
                BomItem.bom_item_id == item_data['bom_item_id']
            ).first()
            
            if not bom_item:
                logger.error(f"BOM item {item_data['bom_item_id']} not found for project {project_id}")
                continue
                
            # Process each match for this BOM item
            for match_data in item_data.get('matches', []):
                # Find or create the Component
                component = db.query(Component).filter(
                    Component.mouser_part_number == match_data['mouser_part_number']
                ).first()
                
                if not component and match_data.get('mouser_part_number'):
                    # Convert price string to Decimal, handle errors/Nones
                    price_value = match_data.get('price')
                    price_decimal = None
                    if price_value and price_value != 'N/A':
                        try:
                            price_decimal = Decimal(price_value)
                        except InvalidOperation:
                            logger.warning(f"Could not convert price '{price_value}' to Decimal for component {match_data.get('mouser_part_number')}")
                    
                    # Create new component
                    component = Component(
                        mouser_part_number=match_data['mouser_part_number'],
                        manufacturer_name=match_data.get('manufacturer_name'),
                        description=match_data.get('description'),
                        datasheet_url=match_data.get('datasheet_url'),
                        price=price_decimal,
                        availability=match_data.get('availability')
                    )
                    db.add(component)
                    try:
                        db.flush()  # Get the component ID without committing
                    except IntegrityError as e:
                        db.rollback()
                        logger.error(f"Integrity error creating component for Mouser PN {match_data.get('mouser_part_number')}: {e}")
                        # Try fetching again in case of race condition
                        component = db.query(Component).filter(
                            Component.mouser_part_number == match_data['mouser_part_number']
                        ).first()
                        if not component:
                           logger.error("Component still not found after rollback, skipping match.")
                           continue
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Error flushing new component {match_data.get('mouser_part_number')}: {e}")
                        continue

                # Create the BomItemMatch only if we have a component
                if component:
                    match = BomItemMatch(
                        bom_item_id=bom_item.bom_item_id,
                        component_id=component.component_id,
                        match_status=match_data.get('match_status', 'unknown')
                    )
                    db.add(match)
                else:
                    # If component creation failed or wasn't attempted (e.g., no MPN in match_data)
                    # Create a match entry without a component link to record the status
                    match = BomItemMatch(
                        bom_item_id=bom_item.bom_item_id,
                        component_id=None,
                        match_status=match_data.get('match_status', 'error')
                    )
                    db.add(match)
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully saved results for project {project_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving results for project {project_id}: {str(e)}")
        db.rollback()
        return False 