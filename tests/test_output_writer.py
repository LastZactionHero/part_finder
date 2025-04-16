"""Tests for the output writer module."""

import csv
import pytest
import os
from pcb_part_finder.output_writer import (
    initialize_output_csv,
    append_row_to_csv,
    OUTPUT_HEADER,
    OutputWriterError
)
from unittest.mock import patch

def test_initialize_output_csv_success(tmp_path):
    """Test successful initialization of output CSV."""
    output_file = tmp_path / "output.csv"
    initialize_output_csv(str(output_file), OUTPUT_HEADER)
    
    # Verify the file was created with the correct header
    with open(output_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == OUTPUT_HEADER

def test_initialize_output_csv_permission_error(tmp_path):
    """Test initialization with permission error."""
    output_file = tmp_path / "output.csv"
    
    with patch('builtins.open', side_effect=PermissionError("Permission denied")):
        with pytest.raises(OutputWriterError) as exc_info:
            initialize_output_csv(str(output_file), OUTPUT_HEADER)
        assert "Error initializing output CSV" in str(exc_info.value)

def test_append_row_to_csv_success(tmp_path):
    """Test successful appending of a row to output CSV."""
    output_file = tmp_path / "output.csv"
    initialize_output_csv(str(output_file), OUTPUT_HEADER)
    
    test_data = {
        'Qty': '1',
        'Description': 'Test Part',
        'Possible MPN': 'ABC123',
        'Package': 'SMD',
        'Notes/Source': 'Test Note',
        'Mouser Part Number': 'MOUSER123',
        'Manufacturer Part Number': 'MFR123',
        'Manufacturer Name': 'Test Mfr',
        'Mouser Description': 'Test Description',
        'Datasheet URL': 'http://example.com',
        'Price': '$1.23',
        'Availability': 'In Stock',
        'Match Status': 'Success'
    }
    
    append_row_to_csv(str(output_file), test_data, OUTPUT_HEADER)
    
    # Verify the row was appended correctly
    with open(output_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert row == test_data

def test_append_row_to_csv_missing_fields(tmp_path):
    """Test appending a row with missing required fields."""
    output_file = tmp_path / "output.csv"
    initialize_output_csv(str(output_file), OUTPUT_HEADER)
    
    test_data = {
        'Qty': '1',
        'Description': 'Test Part'
        # Missing other required fields
    }
    
    with pytest.raises(OutputWriterError) as exc_info:
        append_row_to_csv(str(output_file), test_data, OUTPUT_HEADER)
    assert "missing required fields" in str(exc_info.value)

def test_append_row_to_csv_multiple_rows(tmp_path):
    """Test appending multiple rows to output CSV."""
    output_file = tmp_path / "output.csv"
    initialize_output_csv(str(output_file), OUTPUT_HEADER)
    
    test_data_1 = {field: f'Test1_{field}' for field in OUTPUT_HEADER}
    test_data_2 = {field: f'Test2_{field}' for field in OUTPUT_HEADER}
    
    append_row_to_csv(str(output_file), test_data_1, OUTPUT_HEADER)
    append_row_to_csv(str(output_file), test_data_2, OUTPUT_HEADER)
    
    # Verify both rows were appended correctly
    with open(output_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0] == test_data_1
        assert rows[1] == test_data_2 