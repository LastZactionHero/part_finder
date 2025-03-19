#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

def read_requirements(requirements_file):
    """Read the requirements file."""
    with open(requirements_file, 'r') as f:
        return f.read().strip()

def generate_bom_prompt(requirements):
    """Generate the prompt for Claude to create a BOM."""
    return f"""You are an electronics design expert. I need you to create a Bill of Materials (BOM) for a project with these requirements:

{requirements}

Please create a complete BOM that includes ALL necessary components (including passives, connectors, etc.) to build this project. 

The BOM should be in CSV format with these EXACT columns:
Reference,Value,Description,Footprint,Quantity

Important guidelines:
1. Include ALL necessary components (power, programming, IO, etc.)
2. Use standard footprints (0805 for passives, TQFP/SOIC for ICs when possible)
3. Include decoupling capacitors for ICs
4. Include any necessary connectors (power, programming, IO)
5. Include any necessary voltage regulation
6. Include any necessary crystals/oscillators
7. Include any status LEDs that would be helpful
8. Each component must have its own row with a unique reference designator
9. Use practical, commonly available values
10. Format must be EXACTLY:
    - One header row with: Reference,Value,Description,Footprint,Quantity
    - Each component on its own row
    - No spaces in the CSV values
    - No blank lines
    - No extra text before or after the CSV content

Example format:
Reference,Value,Description,Footprint,Quantity
C1,0.1uF,Decoupling_capacitor,0805,1
R1,10k,Pull-up_resistor,0805,1

Return ONLY the CSV content with exact formatting as shown above."""

def get_claude_bom(requirements, api_key):
    """Call Claude API to generate the BOM."""
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    
    data = {
        'model': 'claude-3-opus-20240229',
        'max_tokens': 4000,
        'messages': [{
            'role': 'user',
            'content': generate_bom_prompt(requirements)
        }]
    }
    
    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise Exception(f"Claude API error: {response.text}")
    
    result = response.json()
    return result['content'][0]['text'].strip()

def save_bom_csv(bom_content, output_file):
    """Save the BOM to a CSV file."""
    with open(output_file, 'w') as f:
        f.write(bom_content)

def process_bom_with_mouser(bom_file, context, output_file):
    """Process the BOM with bom_processor.py."""
    python_path = os.path.expanduser('~/miniconda3/bin/python')
    processor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bom_processor.py')
    
    cmd = [
        python_path,
        processor_path,
        bom_file,
        context,
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error processing BOM: {result.stderr}", file=sys.stderr)
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='Generate and process a BOM from project requirements')
    parser.add_argument('-r', '--requirements', required=True, help='Requirements text file')
    args = parser.parse_args()
    
    # Load API key
    load_dotenv()
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        print("Error: CLAUDE_API_KEY not found in .env file", file=sys.stderr)
        return
    
    try:
        # Read requirements
        requirements = read_requirements(args.requirements)
        print("Generating BOM from requirements...")
        
        # Generate BOM with Claude
        bom_content = get_claude_bom(requirements, claude_api_key)
        
        # Save initial BOM
        requirements_base = Path(args.requirements).stem
        initial_bom = f"{requirements_base}_bom.csv"
        final_bom = f"{requirements_base}_bom_with_parts.csv"
        
        save_bom_csv(bom_content, initial_bom)
        print(f"\nBOM generated and saved to {initial_bom}")
        
        # Process with Mouser
        print("\nProcessing BOM with Mouser...")
        if process_bom_with_mouser(initial_bom, requirements, final_bom):
            print(f"\nComplete! Final BOM with Mouser parts saved to {final_bom}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return

if __name__ == '__main__':
    main() 