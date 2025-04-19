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
# Delay between initial API requests in seconds
API_REQUEST_DELAY = 0.5
# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10
REQUEST_TIMEOUT = 15

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

def _make_mouser_request(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    search_term: str, # For logging purposes
    search_type: str  # For logging purposes
) -> Dict[str, Any]:
    """Makes a request to the Mouser API with retry logic."""
    last_exception = None
    for attempt in range(MAX_RETRIES + 1): # Initial attempt + retries
        try:
            # Add delay before making the request (except first attempt)
            if attempt > 0:
                logging.warning(f"Retrying Mouser API request for {search_type} '{search_term}'. Attempt {attempt}/{MAX_RETRIES}. Waiting {RETRY_DELAY_SECONDS}s.")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                # Initial request delay
                time.sleep(API_REQUEST_DELAY)

            logging.debug(f"Making Mouser API {search_type} search request for '{search_term}' (Attempt {attempt+1})")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            logging.debug(f"Mouser API response status code: {response.status_code} for {search_type} '{search_term}'")

            if response.status_code == 200:
                try:
                    raw_response_data = response.json()
                    logging.debug(f"Successfully received JSON response for {search_type} '{search_term}'")
                    # Check for API-level errors before returning
                    api_errors = raw_response_data.get('Errors', [])
                    if api_errors:
                        logging.error(f"Mouser API returned errors for {search_type} '{search_term}': {api_errors}")
                        # Decide whether to retry based on error type, for now, raise immediately
                        raise MouserApiError(f"Mouser API error for {search_type} '{search_term}': {api_errors}")
                    return raw_response_data # Success
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON response for {search_type} '{search_term}': {e}")
                    raise MouserApiError(f"Invalid JSON response from Mouser API: {e}")

            elif response.status_code == 429:
                logging.warning(f"Mouser API rate limit exceeded for {search_type} '{search_term}'.")
                last_exception = MouserApiError("Mouser API rate limit exceeded")
                # Continue to retry loop for rate limit errors

            else:
                logging.error(f"Mouser API request failed for {search_type} '{search_term}': {response.status_code} - {response.text}")
                last_exception = MouserApiError(f"Mouser API request failed: {response.status_code} - {response.text}")
                # Break retry loop for non-recoverable HTTP errors (like 400, 401, 404, 500 etc.)
                break # Don't retry on definitive failures

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during Mouser API request for {search_type} '{search_term}': {e}")
            last_exception = MouserApiError(f"Network error during Mouser API request: {e}")
            # Continue to retry loop for network errors

    # If all retries failed
    logging.error(f"Mouser API request failed after {MAX_RETRIES} retries for {search_type} '{search_term}'.")
    raise last_exception if last_exception else MouserApiError(f"Mouser API request failed after multiple retries for {search_type} '{search_term}'.")

def search_mouser_by_keyword(
    keyword: str,
    cache_manager: MouserApiCacheManager,
    db: Session,
    records: int = 10
) -> List[Dict[str, Any]]:
    """Search for parts using a keyword, using cache and retry logic."""
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
        logging.warning(f"Cache read error for keyword '{keyword}': {e}. Proceeding with API call.")

    logging.info(f"Cache miss for keyword: {keyword}. Calling Mouser API.")
    # --- API Call ---
    api_key = get_api_key() # Raises MouserApiError if not found

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
        # Use the new helper function for the request
        raw_response_data = _make_mouser_request(
            url=url,
            headers=headers,
            payload=payload,
            search_term=keyword,
            search_type='keyword'
        )

        # --- Cache Write (only if successful API call without API errors) ---
        try:
            cache_manager.cache_response(
                search_term=keyword,
                search_type='keyword',
                response_data=raw_response_data,
                db=db
            )
        except (SQLAlchemyError, Exception) as cache_e:
            logging.warning(f"Failed to cache response for keyword '{keyword}': {cache_e}")

        # --- Parse Response ---
        parts = raw_response_data.get('SearchResults', {}).get('Parts', [])
        logging.debug(f"Returning {len(parts)} parts from API for keyword '{keyword}'")
        return parts if parts else []

    except MouserApiError as e:
        # Log the final error after retries and re-raise or handle as needed
        logging.error(f"Final error after retries for keyword '{keyword}': {e}")
        raise # Re-raise the MouserApiError to be handled by the caller

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
    """Search for a specific part by Manufacturer Part Number (MPN), using cache and retry logic."""
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
                # Cache hit with no results means the MPN likely doesn't exist on Mouser
                # We might cache this "not found" state explicitly later if needed
                return None
    except Exception as e:
        logging.warning(f"Cache read error for MPN {mpn}: {e}. Proceeding with API call.")

    logging.info(f"Cache miss for MPN: {mpn}. Calling Mouser API.")
    # --- API Call ---
    api_key = get_api_key() # Raises MouserApiError if not found

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
        # Use the new helper function for the request
        raw_response_data = _make_mouser_request(
            url=url,
            headers=headers,
            payload=payload,
            search_term=mpn,
            search_type='mpn'
        )

        # --- Cache Write (only if successful API call without API errors) ---
        try:
            cache_manager.cache_response(
                search_term=mpn,
                search_type='mpn',
                response_data=raw_response_data,
                db=db
            )
        except (SQLAlchemyError, Exception) as cache_e:
            logging.warning(f"Failed to cache response for MPN {mpn}: {cache_e}")


        # --- Parse Response ---
        parts = raw_response_data.get('SearchResults', {}).get('Parts', [])
        if not parts:
            logging.debug(f"No parts found in API response for MPN '{mpn}' after API call")
            # Consider caching the "not found" result here if needed
            return None # MPN not found

        parsed_data = _parse_mouser_part_data(parts[0])
        logging.debug(f"Returning parsed data from API for MPN '{mpn}'")
        return parsed_data

    except MouserApiError as e:
        # Log the final error after retries and re-raise or handle as needed
        logging.error(f"Final error after retries for MPN '{mpn}': {e}")
        raise # Re-raise the MouserApiError to be handled by the caller 