"""Module for interacting with the Mouser API."""

import os
import json
import time
import logging
import requests
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session  # Added
from sqlalchemy.exc import SQLAlchemyError # Added for cache exception handling
from pcb_part_finder.core.cache_manager import MouserApiCacheManager  # Added

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

def search_mouser_by_keyword(
    keyword: str,
    cache_manager: MouserApiCacheManager,
    db: Session,
    records: int = 10
) -> List[Dict[str, Any]]:
    """Search for parts using a keyword, using cache."""
    logging.debug(f"Initiating keyword search for: '{keyword}'")
    # --- Cache Check ---
    try:
        cached_response = cache_manager.get_cached_response(
            search_term=keyword, search_type='keyword', db=db
        )
        if cached_response:
            logging.info(f"Cache hit for keyword: {keyword}")
            parts = cached_response.get('SearchResults', {}).get('Parts', [])
            logging.debug(f"Returning {len(parts[:records])} parts from cache for keyword '{keyword}'")
            return parts[:records] if parts else []
    except Exception as e:
        # Log cache read errors but continue to API call
        logging.warning(f"Cache read error for keyword '{keyword}': {e}. Proceeding with API call.")

    logging.info(f"Cache miss for keyword: {keyword}. Calling Mouser API.")
    # --- API Call ---
    api_key = get_api_key()
    if not api_key:
        raise MouserApiError("Mouser API key not found")

    # Add delay before making the request
    time.sleep(API_REQUEST_DELAY)

    logging.debug(f"Making Mouser API keyword search request for '{keyword}'")
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
        logging.debug(f"Mouser API response status code: {response.status_code} for keyword '{keyword}'")

        if response.status_code == 200:
            try:
                raw_response_data = response.json()
                logging.debug(f"Successfully received JSON response for keyword '{keyword}'")

                # Check for API-level errors before caching
                api_errors = raw_response_data.get('Errors', [])
                if api_errors:
                    logging.error(f"Mouser API returned errors for keyword '{keyword}': {api_errors}")
                    # Raise error if API explicitly failed
                    raise MouserApiError(f"Mouser API error for keyword '{keyword}': {api_errors}")

                # --- Cache Write (only if no API errors) ---
                try:
                    cache_manager.cache_response(
                        search_term=keyword,
                        search_type='keyword',
                        response_data=raw_response_data,
                        db=db
                    )
                except (SQLAlchemyError, Exception) as cache_e:
                    # Log cache write errors but don't fail the main operation
                    logging.warning(f"Failed to cache response for keyword '{keyword}': {cache_e}")

                # --- Parse Response --- 
                parts = raw_response_data.get('SearchResults', {}).get('Parts', [])
                logging.debug(f"Returning {len(parts)} parts from API for keyword '{keyword}'")
                return parts if parts else [] 

            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON response for keyword '{keyword}': {e}")
                raise MouserApiError(f"Invalid JSON response from Mouser API: {e}")
        elif response.status_code == 429:
            logging.warning(f"Mouser API rate limit exceeded for keyword '{keyword}'")
            raise MouserApiError("Mouser API rate limit exceeded")
        else:
            logging.error(f"Mouser API request failed for keyword '{keyword}': {response.status_code} - {response.text}")
            raise MouserApiError(f"Mouser API request failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error during Mouser API request for keyword '{keyword}': {e}")
        raise MouserApiError(f"Network error during Mouser API request: {e}")

def _parse_mouser_part_data(part_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helper function to parse raw part data from Mouser API response."""
    if not part_data:
        return None

    # Extract price (find qty 1 or lowest break)
    price = None
    price_breaks = part_data.get('PriceBreaks', [])
    if price_breaks:
        # Sort by quantity and take the lowest
        price_breaks.sort(key=lambda x: x.get('Quantity', float('inf')))
        price_str = price_breaks[0].get('Price', 'N/A')
        # Remove any existing $ symbol
        price_str = price_str.replace('$', '')
        # Store the numeric string or 'N/A', without adding '$'
        price = price_str if price_str != 'N/A' else 'N/A'

    # Extract availability
    availability = "Unknown"
    stock = part_data.get('AvailabilityInStock', '0')
    try:
        if int(stock) > 0:
            availability = "In Stock"
        elif part_data.get('LeadTime'):
            availability = f"Lead Time: {part_data.get('LeadTime')}"
    except (ValueError, TypeError):
        pass # Keep availability as "Unknown"

    return {
        'Mouser Part Number': part_data.get('MouserPartNumber', ''),
        'Manufacturer Part Number': part_data.get('ManufacturerPartNumber', ''),
        'Manufacturer Name': part_data.get('Manufacturer', ''),
        'Mouser Description': part_data.get('Description', ''),
        'Datasheet URL': part_data.get('DataSheetUrl', ''),
        'Price': price or 'N/A',
        'Availability': availability
    }

def search_mouser_by_mpn(
    mpn: str,
    cache_manager: MouserApiCacheManager,
    db: Session
) -> Optional[Dict[str, Any]]:
    """Search for a specific part by Manufacturer Part Number (MPN), using cache."""
    logging.debug(f"Initiating MPN search for: '{mpn}'")
    # --- Cache Check ---
    try:
        cached_response = cache_manager.get_cached_response(
            search_term=mpn, search_type='mpn', db=db
        )
        if cached_response:
            logging.info(f"Cache hit for MPN: {mpn}")
            parts = cached_response.get('SearchResults', {}).get('Parts', [])
            if parts:
                parsed_data = _parse_mouser_part_data(parts[0])
                logging.debug(f"Returning parsed data from cache for MPN '{mpn}'")
                return parsed_data
            else:
                logging.debug(f"Cache hit for MPN '{mpn}', but no parts found in cached data.")
                return None
    except Exception as e:
        # Log cache read errors but continue to API call
        logging.warning(f"Cache read error for MPN {mpn}: {e}. Proceeding with API call.")

    logging.info(f"Cache miss for MPN: {mpn}. Calling Mouser API.")
    # --- API Call ---
    api_key = get_api_key()
    if not api_key:
        raise MouserApiError("Mouser API key not found")

    # Add delay before making the request
    time.sleep(API_REQUEST_DELAY)

    logging.debug(f"Making Mouser API MPN search request for '{mpn}'")
    url = f"{MOUSER_API_BASE_URL}/search/keyword?apiKey={api_key}"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {
        'SearchByKeywordRequest': {
            'keyword': mpn,
            'records': 1, # MPN search expects one primary result
            'startingRecord': 0,
            'searchOptions': None, #'ExactMPN', # Consider using ExactMPN if appropriate
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
        logging.debug(f"Mouser API response status code: {response.status_code} for MPN '{mpn}'")

        if response.status_code == 200:
            try:
                raw_response_data = response.json()
                logging.debug(f"Successfully received JSON response for MPN '{mpn}'")

                # Check for API-level errors before caching
                api_errors = raw_response_data.get('Errors', [])
                if api_errors:
                    # Log the error but might still contain partial data, decide if needed
                    logging.error(f"Mouser API returned errors for MPN {mpn}: {api_errors}")
                    # Depending on requirements, you might still parse or return None/raise
                    # For now, let's treat API errors as non-cacheable failure for this specific MPN search
                    # If the API error structure indicates "not found", we might cache that fact later.
                    # Raise error if API explicitly failed
                    raise MouserApiError(f"Mouser API error for MPN {mpn}: {api_errors}")


                # --- Cache Write (only if no API errors) ---
                try:
                    cache_manager.cache_response(
                        search_term=mpn,
                        search_type='mpn',
                        response_data=raw_response_data,
                        db=db
                    )
                except (SQLAlchemyError, Exception) as cache_e:
                    # Log cache write errors but don't fail the main operation
                    logging.warning(f"Failed to cache response for MPN {mpn}: {cache_e}")


                # --- Parse Response (using the same helper) ---
                parts = raw_response_data.get('SearchResults', {}).get('Parts', [])
                if not parts:
                    logging.debug(f"No parts found in API response for MPN '{mpn}'")
                    return None # MPN not found

                parsed_data = _parse_mouser_part_data(parts[0])
                logging.debug(f"Returning parsed data from API for MPN '{mpn}'")
                return parsed_data

            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON response for MPN '{mpn}': {e}")
                raise MouserApiError(f"Invalid JSON response from Mouser API: {e}")
        elif response.status_code == 429:
            logging.warning(f"Mouser API rate limit exceeded for MPN '{mpn}'")
            raise MouserApiError("Mouser API rate limit exceeded")
        else:
            logging.error(f"Mouser API request failed for MPN '{mpn}': {response.status_code} - {response.text}")
            raise MouserApiError(f"Mouser API request failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error during Mouser API request for MPN '{mpn}': {e}")
        raise MouserApiError(f"Network error during Mouser API request: {e}") 