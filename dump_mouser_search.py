#!/usr/bin/env python3

import argparse
import json
import os
import requests
from dotenv import load_dotenv
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
            'records': 1,
            'startingRecord': 0,
            'searchOptions': 'string',
            'searchWithYourSignUpLanguage': 'string'
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def main():
    parser = argparse.ArgumentParser(description='Dump raw Mouser API search results')
    parser.add_argument('-q', '--query', required=True, help='Search query (e.g., "10k resistor")')
    args = parser.parse_args()

    # Load API key from .env file
    load_dotenv()
    mouser_api_key = os.getenv('MOUSER_API_KEY')

    if not mouser_api_key:
        print("Error: MOUSER_API_KEY not found in .env file", file=sys.stderr)
        return

    try:
        # Get parts from Mouser
        result = search_mouser_parts(args.query, mouser_api_key)
        
        # Pretty print the JSON response
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error occurred: {str(e)}", file=sys.stderr)

if __name__ == '__main__':
    main() 