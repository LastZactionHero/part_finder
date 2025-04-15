"""Tests for the data loader module."""

import pytest
from pcb_part_finder.data_loader import load_notes, load_input_csv, DataLoaderError

def test_load_notes_success(tmp_path):
    """Test successful loading of notes file."""
    notes_file = tmp_path / "notes.txt"
    notes_file.write_text("Test project notes")
    
    result = load_notes(str(notes_file))
    assert result == "Test project notes"

def test_load_notes_file_not_found():
    """Test loading non-existent notes file."""
    with pytest.raises(DataLoaderError):
        load_notes("nonexistent.txt")

def test_load_input_csv_success(tmp_path):
    """Test successful loading of input CSV."""
    csv_file = tmp_path / "test.csv"
    csv_content = """Qty,Description,Possible MPN,Package,Notes/Source
1,Test Part,ABC123,SMD,Test Note"""
    csv_file.write_text(csv_content)
    
    result = load_input_csv(str(csv_file))
    assert len(result) == 1
    assert result[0]["Qty"] == "1"
    assert result[0]["Description"] == "Test Part"
    assert result[0]["Possible MPN"] == "ABC123"
    assert result[0]["Package"] == "SMD"
    assert result[0]["Notes/Source"] == "Test Note"

def test_load_input_csv_file_not_found():
    """Test loading non-existent CSV file."""
    with pytest.raises(DataLoaderError):
        load_input_csv("nonexistent.csv")

def test_load_input_csv_invalid_format(tmp_path):
    """Test loading invalid CSV format."""
    csv_file = tmp_path / "invalid.csv"
    csv_content = "Invalid CSV content"
    csv_file.write_text(csv_content)
    
    with pytest.raises(DataLoaderError):
        load_input_csv(str(csv_file))

def test_load_input_csv_missing_headers(tmp_path):
    """Test loading CSV with missing required headers."""
    csv_file = tmp_path / "missing_headers.csv"
    csv_content = """Description,Package
Test Part,SMD"""
    csv_file.write_text(csv_content)
    
    with pytest.raises(DataLoaderError) as exc_info:
        load_input_csv(str(csv_file))
    assert "missing required headers" in str(exc_info.value)

def test_load_input_csv_empty_file(tmp_path):
    """Test loading empty CSV file."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")
    
    with pytest.raises(DataLoaderError) as exc_info:
        load_input_csv(str(csv_file))
    assert "CSV file is empty" in str(exc_info.value) 