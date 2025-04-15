"""Module for loading input data files."""

import csv
import os
from typing import List, Dict, Any
from pcb_part_finder.llm_handler import get_llm_response

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

def get_ideal_csv_path() -> str:
    """Get the path to the ideal CSV format file.
    
    Returns:
        The absolute path to the ideal CSV file.
        
    Raises:
        DataLoaderError: If the ideal CSV file cannot be found.
    """
    # Get the directory of the current module
    module_dir = os.path.dirname(os.path.abspath(__file__))
    ideal_csv_path = os.path.join(module_dir, "ideal_initial_bom.csv")
    
    if not os.path.exists(ideal_csv_path):
        raise DataLoaderError(f"Ideal CSV format file not found at {ideal_csv_path}")
        
    return ideal_csv_path

def reformat_csv_with_llm(malformed_csv_path: str, ideal_csv_path: str) -> str:
    """Reformat a CSV using the LLM.
    
    Args:
        malformed_csv_path: Path to the input CSV file
        ideal_csv_path: Path to the ideal CSV format file
        
    Returns:
        Path to the reformatted CSV file
        
    Raises:
        DataLoaderError: If the reformatting fails
    """
    try:
        # Read the input CSV content
        with open(malformed_csv_path, 'r', encoding='utf-8') as f:
            input_content = f.read()
            
        # Read the ideal CSV content
        with open(ideal_csv_path, 'r', encoding='utf-8') as f:
            ideal_content = f.read()
            
        # Create prompt for the LLM
        prompt = f"""You are a helpful assistant that reformats CSV files. I have an input CSV file and an ideal CSV format. 
Please reformat the input CSV to match the structure of the ideal CSV as closely as possible.

The ideal CSV format is:
{ideal_content}

The input CSV content is:
{input_content}

Please reformat the input CSV to match the structure of the ideal CSV. The output should be a valid CSV with the same columns as the ideal CSV.
If some information is missing or unclear, make your best guess based on the context.
Return ONLY the reformatted CSV content, nothing else."""

        # Get reformatted content from LLM
        reformatted_content = get_llm_response(prompt)
        if not reformatted_content:
            raise DataLoaderError("LLM failed to reformat CSV")
            
        # Save reformatted content to a new file
        reformatted_path = os.path.splitext(malformed_csv_path)[0] + "_reformatted.csv"
        with open(reformatted_path, 'w', encoding='utf-8') as f:
            f.write(reformatted_content)
            
        return reformatted_path
        
    except Exception as e:
        raise DataLoaderError(f"Error reformatting CSV with LLM: {e}")

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
        # Get the path to the ideal CSV from the package directory
        ideal_csv_path = get_ideal_csv_path()
            
        # Always reformat the CSV using the LLM
        reformatted_path = reformat_csv_with_llm(filepath, ideal_csv_path)
        
        # Load the reformatted CSV
        with open(reformatted_path, 'r', encoding='utf-8') as f:
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
    except Exception as e:
        raise DataLoaderError(f"Error processing CSV: {e}") 