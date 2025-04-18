"""Tests for the Mouser API module."""

import pytest
import requests
from unittest.mock import patch, MagicMock
from pcb_part_finder.mouser_api import (
    get_api_key,
    search_mouser_by_keyword,
    search_mouser_by_mpn,
    MouserApiError
)

def test_get_api_key_success():
    """Test successful API key retrieval."""
    with patch.dict('os.environ', {'MOUSER_API_KEY': 'test_key'}):
        assert get_api_key() == 'test_key'

# def test_get_api_key_missing():
#     """Test missing API key."""
#     with patch.dict('os.environ', {}, clear=True):
#         with pytest.raises(MouserApiError) as exc_info:
#             get_api_key()
#         assert "Mouser API key not found" in str(exc_info.value)

# def test_search_mouser_by_keyword_success(mocker):
#     """Test successful keyword search."""
#     mock_response = MagicMock()
#     mock_response.status_code = 200
#     mock_response.json.return_value = {
#         'SearchResults': {
#             'Parts': [
#                 {
#                     'MouserPartNumber': 'MOUSER123',
#                     'ManufacturerPartNumber': 'MFR123',
#                     'Manufacturer': 'Test Mfr',
#                     'Description': 'Test Part'
#                 }
#             ]
#         }
#     }
    
#     mocker.patch('requests.post', return_value=mock_response)
#     mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
#     result = search_mouser_by_keyword('test')
#     assert len(result) == 1
#     assert result[0]['MouserPartNumber'] == 'MOUSER123'

def test_search_mouser_by_keyword_rate_limit(mocker):
    """Test keyword search with rate limit response."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    with pytest.raises(MouserApiError) as exc_info:
        search_mouser_by_keyword('test')
    assert "rate limit" in str(exc_info.value)

def test_search_mouser_by_keyword_api_error(mocker):
    """Test keyword search with API error response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'Errors': ['Test error']
    }
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    with pytest.raises(MouserApiError) as exc_info:
        search_mouser_by_keyword('test')
    assert "Mouser API error" in str(exc_info.value)

def test_search_mouser_by_keyword_network_error(mocker):
    """Test keyword search with network error."""
    mocker.patch('requests.post', side_effect=requests.exceptions.RequestException('Network error'))
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    with pytest.raises(MouserApiError) as exc_info:
        search_mouser_by_keyword('test')
    assert "Network error" in str(exc_info.value)

def test_search_mouser_by_mpn_success(mocker):
    """Test successful MPN search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'SearchResults': {
            'Parts': [
                {
                    'MouserPartNumber': 'MOUSER123',
                    'ManufacturerPartNumber': 'MFR123',
                    'Manufacturer': 'Test Mfr',
                    'Description': 'Test Part',
                    'DataSheetUrl': 'http://example.com',
                    'PriceBreaks': [{'Price': '$1.23'}],
                    'AvailabilityInStock': '100'
                }
            ]
        }
    }
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    result = search_mouser_by_mpn('MFR123')
    assert result is not None
    assert result['Mouser Part Number'] == 'MOUSER123'
    assert result['Price'] == '$1.23'
    assert 'In Stock' in result['Availability']

def test_search_mouser_by_mpn_not_found(mocker):
    """Test MPN search with no results."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'SearchResults': {
            'Parts': []
        }
    }
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    result = search_mouser_by_mpn('NONEXISTENT')
    assert result is None

def test_search_mouser_by_mpn_lead_time(mocker):
    """Test MPN search with lead time availability."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'SearchResults': {
            'Parts': [
                {
                    'MouserPartNumber': 'MOUSER123',
                    'ManufacturerPartNumber': 'MFR123',
                    'Manufacturer': 'Test Mfr',
                    'Description': 'Test Part',
                    'DataSheetUrl': 'http://example.com',
                    'PriceBreaks': [{'Price': '$1.23'}],
                    'AvailabilityInStock': '0',
                    'LeadTime': '10 weeks'
                }
            ]
        }
    }
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    result = search_mouser_by_mpn('MFR123')
    assert result is not None
    assert 'Lead Time' in result['Availability']
    assert '10 weeks' in result['Availability']

def test_search_mouser_by_mpn_missing_price(mocker):
    """Test MPN search with missing price information."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'SearchResults': {
            'Parts': [
                {
                    'MouserPartNumber': 'MOUSER123',
                    'ManufacturerPartNumber': 'MFR123',
                    'Manufacturer': 'Test Mfr',
                    'Description': 'Test Part',
                    'DataSheetUrl': 'http://example.com',
                    'AvailabilityInStock': '0'
                }
            ]
        }
    }
    
    mocker.patch('requests.post', return_value=mock_response)
    mocker.patch('pcb_part_finder.mouser_api.get_api_key', return_value='test_key')
    
    result = search_mouser_by_mpn('MFR123')
    assert result is not None
    assert result['Price'] == 'N/A' 