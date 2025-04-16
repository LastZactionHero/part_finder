#!/usr/bin/env python3

import argparse
import os
import sys
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from pcb_part_finder.core.data_loader import load_input_csv, DataLoaderError
from pcb_part_finder.output_writer import (
    initialize_output_csv,
    append_row_to_csv,
    OUTPUT_HEADER,
    OutputWriterError,
    write_output_csv
)
from pcb_part_finder.mouser_api import search_mouser_by_keyword, search_mouser_by_mpn
from pcb_part_finder.llm_handler import (
    get_llm_response,
    format_search_term_prompt,
    parse_search_terms,
    format_evaluation_prompt,
    extract_mpn_from_eval,
    LlmApiError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='PCB Part Finder Tool')
    parser.add_argument('--input', required=True, help='Path to input CSV file')
    parser.add_argument('--notes', required=True, help='Path to project notes file')
    parser.add_argument('--output', default='bom_matched.csv', help='Path to output CSV file')
    return parser.parse_args()

def validate_file_paths(args):
    """Validate that the provided file paths exist."""
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.notes):
        print(f"Error: Notes file not found: {args.notes}", file=sys.stderr)
        sys.exit(1)

def process_part(part_info: Dict[str, str], project_notes: str, selected_parts: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Process a single part to find the best match on Mouser.
    
    Args:
        part_info: Dictionary containing part information from the input CSV
        project_notes: Content of the project notes file
        selected_parts: List of previously selected parts
        
    Returns:
        Dictionary containing the matched part information
    """
    logger.info(f"Processing part: {part_info['Description']}")
    
    # Initialize default output with original part info and unmatched status
    output_data = {
        **part_info,
        'Mouser Part Number': '',
        'Manufacturer Part Number': '',
        'Manufacturer Name': '',
        'Mouser Description': '',
        'Datasheet URL': '',
        'Price': '',
        'Availability': '',
        'Match Status': 'No Match'
    }
    
    # Generate search terms using LLM
    try:
        search_prompt = format_search_term_prompt(part_info)
        search_response = get_llm_response(search_prompt)
        search_terms = parse_search_terms(search_response)
        logger.info(f"Generated search terms: {search_terms}")
    except LlmApiError as e:
        logger.error(f"Error generating search terms: {e}")
        output_data['Match Status'] = 'LLM Search Term Failed'
        return output_data
    
    # Search Mouser with each term
    all_results = []
    for term in search_terms:
        try:
            results = search_mouser_by_keyword(term)
            if results and isinstance(results, list):
                logger.info(f"Found {len(results)} results for search term: {term}")
                all_results.extend(results)
            else:
                logger.warning(f"No valid results returned for search term: {term}")
        except Exception as e:
            logger.error(f"Error searching Mouser for term '{term}': {e}")
    
    if not all_results:
        logger.warning(f"No results found for part: {part_info['Description']}")
        output_data['Match Status'] = 'No Mouser Matches'
        return output_data
    
    # Evaluate results using LLM
    try:
        # Format the results for the evaluation prompt
        logger.info(f"Starting to format {len(all_results)} results for evaluation")
        formatted_results = []
        for idx, result in enumerate(all_results):
            logger.debug(f"Processing result {idx + 1}/{len(all_results)}")
            if not isinstance(result, dict):
                logger.warning(f"Skipping invalid result: {result}")
                continue

            formatted_result = {
                'Manufacturer': result['Manufacturer'] if 'Manufacturer' in result else '',
                'ManufacturerPartNumber': result['ManufacturerPartNumber'] if 'ManufacturerPartNumber' in result else '',
                'MouserPartNumber': result['MouserPartNumber'] if 'MouserPartNumber' in result else '',
                'Description': result['Description'] if 'Description' in result else '',
                'DataSheetUrl': result['DataSheetUrl'] if 'DataSheetUrl' in result else '',
                'Price': result['Price'] if 'Price' in result else '',
                'Availability': result['Availability'] if 'Availability' in result else ''
            }
            logger.debug(f"Formatted result {idx + 1}: {formatted_result}")
            formatted_results.append(formatted_result)
        
        logger.info(f"Finished formatting results. Total valid results: {len(formatted_results)}")
        if not formatted_results:
            logger.warning("No valid results to evaluate")
            output_data['Match Status'] = 'No Mouser Matches'
            return output_data
            
        logger.info("Preparing evaluation prompt")
        eval_prompt = format_evaluation_prompt(part_info, project_notes, selected_parts, formatted_results)
        logger.debug(f"Evaluation prompt length: {len(eval_prompt)}")
        
        logger.info("Sending evaluation prompt to LLM")
        eval_response = get_llm_response(eval_prompt)
        logger.debug(f"Received LLM response: {eval_response}")
        
        logger.info("Extracting MPN from evaluation response")
        selected_mpn = extract_mpn_from_eval(eval_response)
        logger.info(f"Extracted MPN: {selected_mpn}")
        
        if not selected_mpn:
            logger.warning("No part selected from evaluation")
            output_data['Match Status'] = 'LLM Selection Failed'
            return output_data
            
        logger.info(f"Fetching detailed information for MPN: {selected_mpn}")
        detailed_part = search_mouser_by_mpn(selected_mpn)
        logger.debug(f"Detailed part info: {detailed_part}")
        
        if not detailed_part:
            logger.warning(f"Could not find detailed information for selected part: {selected_mpn}")
            output_data['Match Status'] = 'Mouser Detail Not Found'
            return output_data
            
        logger.info("Updating output data with Mouser details")
        output_data.update(detailed_part)
        output_data['Match Status'] = 'Matched'
        
        logger.info(f"Successfully matched part: {output_data['Description']}")
        return output_data
        
    except LlmApiError as e:
        logger.error(f"Error evaluating parts: {e}")
        output_data['Match Status'] = 'LLM Evaluation Failed'
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error processing part: {e}")
        output_data['Match Status'] = 'Processing Error'
        sys.exit(1)

def main():
    """Main entry point for the PCB Part Finder tool."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    args = parse_args()
    validate_file_paths(args)
    
    # Check for required API keys
    if not os.getenv('MOUSER_API_KEY'):
        print("Error: MOUSER_API_KEY environment variable not set", file=sys.stderr)
        logger.error("MOUSER_API_KEY environment variable not set")
        sys.exit(1)
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    try:
        # Load input data
        parts = load_input_csv(args.input)
        with open(args.notes, 'r') as f:
            project_notes = f.read()
        
        print(f"Loaded project notes from {args.notes}")
        print(f"Loaded {len(parts)} parts from {args.input}")
        logger.info(f"Loaded project notes from {args.notes}")
        logger.info(f"Loaded {len(parts)} parts from {args.input}")
        
        # Initialize output CSV
        initialize_output_csv(args.output, OUTPUT_HEADER)
        print(f"Initialized output CSV at {args.output}")
        logger.info(f"Initialized output CSV at {args.output}")
        
        # Process each part
        selected_parts = []
        
        for part in parts:
            matched_part = process_part(part, project_notes, selected_parts)
            
            # Write the matched part to CSV immediately
            try:
                append_row_to_csv(args.output, matched_part, OUTPUT_HEADER)
                print(f"Wrote matched part to output CSV: {matched_part.get('Description', 'Unknown')}")
                logger.info(f"Wrote matched part to output CSV: {matched_part.get('Description', 'Unknown')}")
            except OutputWriterError as e:
                print(f"Error writing output: {e}", file=sys.stderr)
                logger.error(f"Error writing output: {e}")
                sys.exit(1)
            
            if matched_part.get('Match Status') == 'Matched':
                selected_parts.append(matched_part)
        
        print(f"Processing complete. Output saved to {args.output}")
        logger.info(f"Processing complete. Output saved to {args.output}")
        
    except DataLoaderError as e:
        print(f"Error loading input data: {e}", file=sys.stderr)
        logger.error(f"Error loading input data: {e}")
        sys.exit(1)
    except OutputWriterError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        logger.error(f"Error writing output: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running part finder: {e}", file=sys.stderr)
        logger.error(f"Error running part finder: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 