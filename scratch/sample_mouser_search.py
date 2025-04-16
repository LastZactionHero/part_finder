#!/usr/bin/env python3

import argparse
import json
import os
import requests
from dotenv import load_dotenv
import re
import sys

def search_mouser_parts(keyword, api_key):
    url = f'https://api.mouser.com/api/v1/search/keyword?apiKey={api_key}'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'SearchByKeywordRequest': {
            'keyword': keyword,
            'records': 0,
            'startingRecord': 0,
            'searchOptions': 'string',
            'searchWithYourSignUpLanguage': 'string'
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def get_claude_recommendation(parts, query, context, api_key):
    # Format the parts list for Claude
    parts_text = "Here are the parts:\n\n"
    for part in parts:
        parts_text += f"Manufacturer: {part['Manufacturer']}\n"
        parts_text += f"Part Number: {part['ManufacturerPartNumber']}\n"
        parts_text += f"Description: {part['Description']}\n"
        if part.get('PriceBreaks'):
            parts_text += f"Price: {part['PriceBreaks'][0]['Price']}\n"
        parts_text += "---\n"

    context_text = f"\nContext: This part will be used for {context}." if context else ""

    prompt = f"""Here is a list of parts for the query "{query}". Please evaluate this list and select a single part that best fits our use case. When selecting from this list, balance for a part that's cheaper, from a known vendor, documentation and footprints, and common or well documented.{context_text}

{parts_text}

Return your answer in the following format so it can be easily parsed. Use EXACTLY the part number as shown in the list above, do not add manufacturer name or any other text:
[ManufacturerPartNumber:95J3R0E]"""

    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    
    data = {
        'model': 'claude-3-sonnet-20240229',
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    
    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise Exception(f"Claude API error: {response.text}")
    
    result = response.json()
    return result['content'][0]['text']

def extract_manufacturer_part_number(claude_response):
    # Extract the part number from the format [ManufacturerPartNumber:XXXXX]
    match = re.search(r'\[ManufacturerPartNumber:([^\]]+)\]', claude_response)
    if match:
        return match.group(1)
    return None

def main():
    parser = argparse.ArgumentParser(description='Search for Mouser parts')
    parser.add_argument('-q', '--query', required=True, help='Search query (e.g., "500ohm smd 0805 resistor")')
    parser.add_argument('-c', '--context', help='Context for part selection (e.g., "Atmega32u4 oscillator")')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print detailed information about the part selection')
    args = parser.parse_args()

    # Load API keys from .env file
    load_dotenv()
    mouser_api_key = os.getenv('MOUSER_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

    if not mouser_api_key:
        print("Error: MOUSER_API_KEY not found in .env file", file=sys.stderr)
        return

    if not anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY not found in .env file", file=sys.stderr)
        return

    try:
        # Get parts from Mouser
        result = search_mouser_parts(args.query, mouser_api_key)
        
        if result.get('Errors'):
            print(f"Error: {result['Errors']}", file=sys.stderr)
            return

        parts = result.get('SearchResults', {}).get('Parts', [])
        if not parts:
            print("No parts found matching your search criteria.", file=sys.stderr)
            return

        # Get Claude's recommendation
        claude_response = get_claude_recommendation(parts, args.query, args.context, anthropic_api_key)
        if args.verbose:
            print("\nClaude's response:")
            print(claude_response)
        
        recommended_part_number = extract_manufacturer_part_number(claude_response)
        if args.verbose:
            print(f"\nExtracted part number: {recommended_part_number}")

        if not recommended_part_number:
            print("Could not parse Claude's recommendation", file=sys.stderr)
            return

        # Find and display the recommended part
        recommended_part = next((part for part in parts if part['ManufacturerPartNumber'] == recommended_part_number), None)
        
        if recommended_part:
            if args.verbose:
                print("\nRecommended Part:")
                print(f"Mouser Part Number: {recommended_part['MouserPartNumber']}")
                print(f"Description: {recommended_part['Description']}")
                print(f"Manufacturer: {recommended_part['Manufacturer']}")
                print(f"Manufacturer Part Number: {recommended_part['ManufacturerPartNumber']}")
                if recommended_part.get('PriceBreaks'):
                    print(f"Price: {recommended_part['PriceBreaks'][0]['Price']}")
            else:
                print(recommended_part['MouserPartNumber'])
        else:
            if args.verbose:
                print(f"\nCould not find recommended part number: {recommended_part_number}")
                print("\nAvailable part numbers:")
                for part in parts:
                    print(f"- {part['ManufacturerPartNumber']}")
            else:
                print(f"Error: Could not find recommended part", file=sys.stderr)

    except Exception as e:
        print(f"Error occurred: {str(e)}", file=sys.stderr)

if __name__ == '__main__':
    main() 