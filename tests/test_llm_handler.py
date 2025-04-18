"""Tests for the LLM handler module."""

import pytest
from unittest.mock import MagicMock, patch
import anthropic
from pcb_part_finder.core.llm_handler import (
    get_anthropic_client,
    get_llm_response,
    format_search_term_prompt,
    parse_search_terms,
    LlmApiError
)

def test_get_anthropic_client_success():
    """Test successful Anthropic client creation."""
    with patch('anthropic.Anthropic') as mock_anthropic:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv('ANTHROPIC_API_KEY', 'test_key')
            client = get_anthropic_client()
            mock_anthropic.assert_called_once_with(api_key='test_key')

def test_get_anthropic_client_missing_key():
    """Test Anthropic client creation with missing API key."""
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv('ANTHROPIC_API_KEY', raising=False)
        with pytest.raises(LlmApiError) as exc_info:
            get_anthropic_client()
        assert "not found" in str(exc_info.value)

def test_get_llm_response_success(mocker):
    """Test successful LLM response."""
    mock_response = MagicMock()
    mock_response.text = "test response"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    
    mocker.patch('pcb_part_finder.core.llm_handler.get_gemini_client', return_value=mock_client)
    
    result = get_llm_response("test prompt")
    assert result == "test response"
    
    # Verify the correct parameters were used
    mock_client.models.generate_content.assert_called_once()
    call_args = mock_client.models.generate_content.call_args[1]
    assert call_args['model'] == "gemini-2.5-pro-preview-03-25"
    assert call_args['contents'][0].role == "user"
    assert call_args['contents'][0].parts[0].text == "test prompt"

def test_get_llm_response_api_error(mocker):
    """Test LLM response with API error."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API Error")
    
    mocker.patch('pcb_part_finder.core.llm_handler.get_gemini_client', return_value=mock_client)
    
    with pytest.raises(LlmApiError) as exc_info:
        get_llm_response("test prompt")
    assert "API Error" in str(exc_info.value)

def test_format_search_term_prompt():
    """Test search term prompt formatting."""
    part_info = {
        'Description': 'Test IC',
        'Possible MPN': 'TEST123',
        'Package': 'SMD'
    }
    
    prompt = format_search_term_prompt(part_info)
    
    # Check that all input fields are included in the prompt
    assert 'Description: Test IC' in prompt
    assert 'Possible MPN: TEST123' in prompt
    assert 'Package: SMD' in prompt
    
    # Check that the prompt includes the key instructions
    assert 'generate' in prompt.lower()
    assert 'search terms' in prompt.lower()
    assert 'comma-separated list' in prompt.lower()

def test_format_search_term_prompt_missing_fields():
    """Test search term prompt formatting with missing fields."""
    part_info = {
        'Description': 'Test IC'
        # Missing Possible MPN and Package
    }
    
    prompt = format_search_term_prompt(part_info)
    
    # Check that missing fields are handled gracefully
    assert 'Description: Test IC' in prompt
    assert 'Possible MPN: ' in prompt
    assert 'Package: ' in prompt

def test_parse_search_terms_valid():
    """Test parsing valid search terms."""
    llm_response = "term1, term2,   term3  "
    terms = parse_search_terms(llm_response)
    assert terms == ['term1', 'term2', 'term3']

def test_parse_search_terms_empty():
    """Test parsing empty search terms."""
    assert parse_search_terms("") == []
    assert parse_search_terms(None) == []

def test_parse_search_terms_extra_whitespace():
    """Test parsing search terms with extra whitespace."""
    llm_response = "  term1  ,  ,  term2  ,,"
    terms = parse_search_terms(llm_response)
    assert terms == ['term1', 'term2'] 