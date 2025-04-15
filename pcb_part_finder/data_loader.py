"""Module for loading input data files."""

import csv
from typing import List, Dict, Any

class DataLoaderError(Exception):
    """Custom exception for data loading errors."""
    pass

def load_notes(filepath: str) -> str:
    """Load the project notes file.
    
    Args:
        filepath: Path to the notes file.
        
    Returns:
        The contents of the notes file as a string.
        
    Raises:
        DataLoaderError: If the file cannot be read.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (FileNotFoundError, IOError) as e:
        raise DataLoaderError(f"Error loading notes file: {e}")

def load_input_csv(filepath: str) -> List[Dict[str, Any]]:
    """Load the input CSV file.
    
    Args:
        filepath: Path to the input CSV file.
        
    Returns:
        A list of dictionaries, where each dictionary represents a row from the CSV.
        
    Raises:
        DataLoaderError: If the file cannot be read or is not a valid CSV.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Try to read the first line to check for header
            first_line = f.readline().strip()
            if not first_line:
                raise DataLoaderError("CSV file is empty")
            
            # Check for expected headers
            expected_headers = {"Qty", "Description", "Possible MPN", "Package", "Notes/Source"}
            headers = set(h.strip() for h in first_line.split(','))
            if not expected_headers.issubset(headers):
                missing = expected_headers - headers
                raise DataLoaderError(f"CSV is missing required headers: {', '.join(missing)}")
            
            # Reset file pointer and read the CSV
            f.seek(0)
            reader = csv.DictReader(f)
            try:
                return list(reader)
            except csv.Error as e:
                raise DataLoaderError(f"Error parsing CSV content: {e}")
                
    except (FileNotFoundError, IOError) as e:
        raise DataLoaderError(f"Error loading input CSV: {e}")
    except csv.Error as e:
        raise DataLoaderError(f"Error parsing CSV: {e}") 