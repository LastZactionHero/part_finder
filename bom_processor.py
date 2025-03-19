#!/usr/bin/env python3

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path
import os
import requests
import json
from dotenv import load_dotenv

def get_claude_query(component, context):
    """Get search query from Claude based on component details."""
    prompt = f"""Given this electronic component from a BOM:
Reference: {component['Reference']}
Value: {component['Value']}
Description: {component['Description']}
Footprint: {component['Footprint']}

And this project context: {context}

Generate a simple search query for Mouser Electronics that will return a broad list of potential parts.
Focus on the essential characteristics only - value and package/footprint.
Do not include specific tolerances, voltage ratings, or other detailed specifications.
The goal is to get a wide range of options that can then be filtered by the selection process.

Example:
Instead of: "100uF 16V X7R 0805 ceramic capacitor"
Use: "100uF 0805 capacitor"

Instead of: "1k 1% 125mW 0805 thick film resistor"
Use: "1k 0805 resistor"

Return ONLY the search query, nothing else."""

    headers = {
        "x-api-key": os.getenv("CLAUDE_API_KEY"),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        print(f"Claude API response status: {response.status_code}")
        result = response.json()
        query = result['content'][0]['text'].strip()
        print(f"Generated query: {query}")
        return query
    else:
        print(f"Error from Claude API: {response.status_code}")
        print(response.text)
        return None

def mouser_search(query, context, api_key):
    """Search Mouser API for parts using mouser_search.py."""
    python_path = sys.executable  # Use the current Python interpreter
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouser_search.py')
    cmd = [python_path, script_path, '--query', query, '--verbose']
    if context:
        cmd.extend(['--context', context])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)  # Print verbose output
        
        if result.returncode != 0:
            print(f"Error running mouser_search.py: {result.stderr}", file=sys.stderr)
            return None
        
        # Extract Mouser part number from the verbose output
        for line in result.stdout.split('\n'):
            if line.startswith('Mouser Part Number:'):
                return line.split(':')[1].strip()
        return None
    except Exception as e:
        print(f"Error executing command: {str(e)}", file=sys.stderr)
        return None

def mask_api_key(key):
    """Mask an API key for safe printing."""
    if not key:
        return None
    return f"{key[:8]}...{key[-4:]}"

def process_bom(input_file, context, output_file):
    """Process the BOM file and add Mouser part numbers."""
    # Load API keys
    load_dotenv()
    mouser_api_key = os.getenv('MOUSER_API_KEY')
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    
    if not mouser_api_key:
        print("Error: MOUSER_API_KEY not found in .env file", file=sys.stderr)
        return
    if not claude_api_key:
        print("Error: CLAUDE_API_KEY not found in .env file", file=sys.stderr)
        return
    
    # Read existing parts if output file exists
    existing_parts = {}
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('MouserPartNumber'):
                    existing_parts[row['Reference']] = row['MouserPartNumber']
    
    # Read the BOM
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Create output file with headers
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Reference', 'Value', 'Description', 'Footprint', 'Quantity', 'MouserPartNumber'])
        writer.writeheader()
        
        for row in rows:
            # Skip if we already have a part number
            if row['Reference'] in existing_parts:
                row['MouserPartNumber'] = existing_parts[row['Reference']]
                writer.writerow(row)
                continue
                
            # Get search query from Claude
            print(f"\nProcessing component: {row['Reference']} ({row['Value']})")
            query = get_claude_query(row, context)
            
            if query:
                print(f"Search query: {query}")
                part_number = mouser_search(query, context, mouser_api_key)
                row['MouserPartNumber'] = part_number if part_number else ''
            else:
                print(f"No search query generated for {row['Reference']}")
                row['MouserPartNumber'] = ''
            
            writer.writerow(row)
            time.sleep(1)  # Rate limit for API calls

def main():
    parser = argparse.ArgumentParser(description='Process a BOM CSV and find Mouser parts for each component')
    parser.add_argument('input_csv', help='Input BOM CSV file')
    parser.add_argument('context', help='Context for part selection (e.g., "Atmega32u4 board")')
    parser.add_argument('output_csv', help='Output CSV file with Mouser part numbers')
    args = parser.parse_args()
    
    process_bom(args.input_csv, args.context, args.output_csv)

if __name__ == '__main__':
    main() 