"""Module for writing output data to CSV files."""

import csv
from typing import List, Dict, Any

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