"""Tests for the data loader module."""

import os
import csv
import pytest
from unittest.mock import patch, mock_open
from pcb_part_finder.core.data_loader import (
    load_input_csv,
    DataLoaderError,
    get_ideal_csv_path
)

@pytest.fixture
def mock_get_llm_response():
    """Fixture to mock the get_llm_response function."""
    with patch('pcb_part_finder.llm_handler.get_llm_response') as mock:
        yield mock

@pytest.fixture
def mock_get_ideal_csv():
    """Fixture to mock the get_ideal_csv_path function."""
    with patch('pcb_part_finder.data_loader.get_ideal_csv_path') as mock:
        yield mock

def test_get_ideal_csv_path_default():
    """Test getting the default ideal CSV path."""
    with patch("os.path.exists", return_value=True):
        path = get_ideal_csv_path()
        assert path.endswith("ideal_initial_bom.csv")

def test_get_ideal_csv_path_override():
    """Test overriding the ideal CSV path."""
    test_path = "/test/path/ideal.csv"
    with patch("os.path.exists", return_value=True):
        path = get_ideal_csv_path()
        assert path.endswith("ideal_initial_bom.csv")

def test_get_ideal_csv_path_not_found():
    """Test handling of missing ideal CSV file."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(DataLoaderError) as exc_info:
            get_ideal_csv_path()
        assert "Ideal CSV format file not found" in str(exc_info.value)

def test_load_input_csv_success(mock_get_llm_response, mock_get_ideal_csv):
    """Test successful loading of input CSV file."""
    # Mock the reformatted CSV content
    reformatted_content = """Qty,Description,Possible MPN,Package,Notes/Source
1,Resistor 10k,RES-123,SMD-0805,DigiKey
2,Capacitor 100uF,CAP-456,SMD-1206,Mouser"""
    
    # Mock the LLM response
    mock_get_llm_response.return_value = reformatted_content
    
    # Mock the ideal CSV path
    mock_get_ideal_csv.return_value = "/test/path/ideal.csv"
    
    # Mock file operations
    with patch("builtins.open", mock_open(read_data=reformatted_content)):
        result = load_input_csv("test.csv", ideal_csv_path="/test/path/ideal.csv")
        assert len(result) == 2
        assert result[0]["Qty"] == "1"
        assert result[0]["Description"] == "Resistor 10k"
        assert result[1]["Qty"] == "2"
        assert result[1]["Description"] == "Capacitor 100uF"

def test_load_input_csv_file_not_found(mock_get_llm_response, mock_get_ideal_csv):
    """Test handling of missing input CSV file."""
    mock_get_ideal_csv.return_value = "/test/path/ideal.csv"
    with pytest.raises(DataLoaderError) as exc_info:
        load_input_csv("nonexistent.csv", ideal_csv_path="/test/path/ideal.csv")
    assert "Error loading input CSV" in str(exc_info.value)

def test_load_input_csv_invalid_format(mock_get_llm_response, mock_get_ideal_csv):
    """Test handling of invalid CSV format."""
    # Mock invalid CSV content
    invalid_content = "This is not a valid CSV"
    mock_get_llm_response.return_value = invalid_content
    mock_get_ideal_csv.return_value = "/test/path/ideal.csv"
    
    with patch("builtins.open", mock_open(read_data=invalid_content)):
        with pytest.raises(DataLoaderError) as exc_info:
            load_input_csv("test.csv", ideal_csv_path="/test/path/ideal.csv")
        assert "Error parsing CSV" in str(exc_info.value)

def test_load_input_csv_missing_headers(mock_get_llm_response, mock_get_ideal_csv):
    """Test handling of CSV with missing required headers."""
    # Mock CSV content with missing headers
    missing_headers_content = """Qty,Description,Package
1,Resistor 10k,SMD-0805"""
    mock_get_llm_response.return_value = missing_headers_content
    mock_get_ideal_csv.return_value = "/test/path/ideal.csv"
    
    with patch("builtins.open", mock_open(read_data=missing_headers_content)):
        with pytest.raises(DataLoaderError) as exc_info:
            load_input_csv("test.csv", ideal_csv_path="/test/path/ideal.csv")
        assert "CSV is missing required headers" in str(exc_info.value)

def test_load_input_csv_empty_file(mock_get_llm_response, mock_get_ideal_csv):
    """Test handling of empty CSV file."""
    # Mock empty CSV content
    empty_content = ""
    mock_get_llm_response.return_value = empty_content
    mock_get_ideal_csv.return_value = "/test/path/ideal.csv"
    
    with patch("builtins.open", mock_open(read_data=empty_content)):
        with pytest.raises(DataLoaderError) as exc_info:
            load_input_csv("test.csv", ideal_csv_path="/test/path/ideal.csv")
        assert "CSV file is empty" in str(exc_info.value) 