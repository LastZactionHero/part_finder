"""Module for interacting with the Mouser API."""

import os
import json
import time
import requests
from typing import List, Dict, Optional, Any

# API base URL
MOUSER_API_BASE_URL = "https://api.mouser.com/api/v1.0"
# Delay between API requests in seconds
API_REQUEST_DELAY = 0.5

class MouserApiError(Exception):
    """Custom exception for Mouser API errors."""
    pass

def get_api_key() -> Optional[str]:
    """Get the Mouser API key from environment variables.
    
    Returns:
        The API key string.
        
    Raises:
        MouserApiError: If the API key is not found.
    """
    api_key = os.getenv('MOUSER_API_KEY')
    if not api_key:
        raise MouserApiError("Mouser API key not found")
    return api_key

def search_mouser_by_keyword(keyword: str, records: int = 5) -> List[Dict[str, Any]]:
    """Search for parts using a keyword.
    
    Args:
        keyword: The search term.
        records: Maximum number of records to return (default: 5).
        
    Returns:
        A list of dictionaries containing part information.
        
    Raises:
        MouserApiError: If the API request fails or returns an error.
    """
    api_key = get_api_key()
    if not api_key:
        raise MouserApiError("Mouser API key not found")
    
    # Add delay before making the request
    time.sleep(API_REQUEST_DELAY)
    
    url = f"{MOUSER_API_BASE_URL}/search/keyword?apiKey={api_key}"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {
        'SearchByKeywordRequest': {
            'keyword': keyword,
            'records': records,
            'startingRecord': 0,
            'searchOptions': None,
            'searchWithYourSignUpLanguage': None
        }
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            try:
                data = response.json()
                if 'Errors' in data and len(data['Errors']) > 0:
                    raise MouserApiError(f"Mouser API error: {data['Errors']}")
                parts = data.get('SearchResults', {}).get('Parts', [])
                return parts if parts else []
            except json.JSONDecodeError as e:
                raise MouserApiError(f"Invalid JSON response: {e}")
        elif response.status_code == 429:
            raise MouserApiError("Mouser API rate limit exceeded")
        else:
            raise MouserApiError(f"Mouser API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise MouserApiError(f"Network error: {e}")

def search_mouser_by_mpn(mpn: str) -> Optional[Dict[str, Any]]:
    """Search for a specific part by Manufacturer Part Number (MPN).
    
    Args:
        mpn: The manufacturer part number to search for.
        
    Returns:
        A dictionary containing detailed part information, or None if not found.
        
    Raises:
        MouserApiError: If the API request fails or returns an error.
    """
    api_key = get_api_key()
    if not api_key:
        raise MouserApiError("Mouser API key not found")
    
    # Add delay before making the request
    time.sleep(API_REQUEST_DELAY)
    
    url = f"{MOUSER_API_BASE_URL}/search/keyword?apiKey={api_key}"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {
        'SearchByKeywordRequest': {
            'keyword': mpn,
            'records': 1,
            'startingRecord': 0,
            'searchOptions': None,
            'searchWithYourSignUpLanguage': None
        }
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'Errors' in data and len(data['Errors']) > 0:
                    print(data)
                    raise MouserApiError(f"Mouser API error: {data['Errors']}")
                parts = data.get('SearchResults', {}).get('Parts', [])
                if not parts:
                    return None
                    
                # Take the first part from the results
                part = parts[0]
                
                # Extract price (find qty 1 or lowest break)
                price = None
                price_breaks = part.get('PriceBreaks', [])
                if price_breaks:
                    # Sort by quantity and take the lowest
                    price_breaks.sort(key=lambda x: x.get('Quantity', float('inf')))
                    price_str = price_breaks[0].get('Price', 'N/A')
                    # Remove any existing $ symbol as we'll add our own
                    price_str = price_str.replace('$', '')
                    price = f"${price_str}" if price_str != 'N/A' else 'N/A'
                
                # Extract availability
                availability = "Unknown"
                stock = part.get('AvailabilityInStock', '0')
                try:
                    if int(stock) > 0:
                        availability = "In Stock"
                    elif part.get('LeadTime'):
                        availability = f"Lead Time: {part.get('LeadTime')}"
                except (ValueError, TypeError):
                    pass
                
                return {
                    'Mouser Part Number': part.get('MouserPartNumber', ''),
                    'Manufacturer Part Number': part.get('ManufacturerPartNumber', ''),
                    'Manufacturer Name': part.get('Manufacturer', ''),
                    'Mouser Description': part.get('Description', ''),
                    'Datasheet URL': part.get('DataSheetUrl', ''),
                    'Price': price or 'N/A',
                    'Availability': availability
                }
            except json.JSONDecodeError as e:
                raise MouserApiError(f"Invalid JSON response: {e}")
        elif response.status_code == 429:
            raise MouserApiError("Mouser API rate limit exceeded")
        else:
            raise MouserApiError(f"Mouser API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise MouserApiError(f"Network error: {e}") 