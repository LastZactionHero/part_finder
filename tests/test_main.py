import pytest
import os
import sys
from unittest.mock import patch, mock_open, MagicMock
from pcb_part_finder.main import parse_args, validate_file_paths, main
from pcb_part_finder.core.data_loader import DataLoaderError, load_input_csv
from pcb_part_finder.output_writer import OutputWriterError

def test_parse_args_valid():
    """Test parsing valid command line arguments."""
    test_args = ['--input', 'test.csv', '--notes', 'notes.txt']
    with patch.object(sys, 'argv', ['script.py'] + test_args):
        args = parse_args()
        assert args.input == 'test.csv'
        assert args.notes == 'notes.txt'

def test_parse_args_missing():
    """Test handling missing required arguments."""
    with patch.object(sys, 'argv', ['script.py']):
        with pytest.raises(SystemExit):
            parse_args()

def test_validate_file_paths_valid(tmp_path):
    """Test validation of existing file paths."""
    # Create temporary files
    input_file = tmp_path / "test.csv"
    notes_file = tmp_path / "notes.txt"
    input_file.write_text("test")
    notes_file.write_text("test")
    
    class Args:
        def __init__(self, input_path, notes_path):
            self.input = input_path
            self.notes = notes_path
    
    args = Args(str(input_file), str(notes_file))
    # Should not raise any exceptions
    validate_file_paths(args)

def test_validate_file_paths_missing_input(tmp_path):
    """Test validation when input file is missing."""
    notes_file = tmp_path / "notes.txt"
    notes_file.write_text("test")
    
    class Args:
        def __init__(self, input_path, notes_path):
            self.input = input_path
            self.notes = notes_path
    
    args = Args("nonexistent.csv", str(notes_file))
    with pytest.raises(SystemExit):
        validate_file_paths(args)

def test_validate_file_paths_missing_notes(tmp_path):
    """Test validation when notes file is missing."""
    input_file = tmp_path / "test.csv"
    input_file.write_text("test")
    
    class Args:
        def __init__(self, input_path, notes_path):
            self.input = input_path
            self.notes = notes_path
    
    args = Args(str(input_file), "nonexistent.txt")
    with pytest.raises(SystemExit):
        validate_file_paths(args)

# @patch('pcb_part_finder.core.data_loader.load_input_csv')
# @patch('pcb_part_finder.llm_handler.get_llm_response')
# def test_main_success(mock_llm_response, mock_load_input, tmp_path, capsys):
#     """Test successful execution of main function."""
#     # Create test files
#     input_file = tmp_path / "test.csv"
#     notes_file = tmp_path / "notes.txt"
#     input_file.write_text("Qty,Description,Possible MPN,Package,Notes/Source\n1,Test Part,ABC123,SMD,Test Note")
#     notes_file.write_text("Test project notes")

#     # Mock command line arguments
#     test_args = ['--input', str(input_file), '--notes', str(notes_file)]
    
#     # Mock API responses
#     mock_llm_response.return_value = "term1, term2"
#     mock_load_input.return_value = [{
#         'Qty': '1',
#         'Description': 'Test Part',
#         'Possible MPN': 'ABC123',
#         'Package': 'SMD',
#         'Notes/Source': 'Test Note'
#     }]
    
#     mock_mouser_response = {
#         'SearchResults': {
#             'Parts': [
#                 {
#                     'MouserPartNumber': 'MOUSER123',
#                     'ManufacturerPartNumber': 'ABC123',
#                     'Manufacturer': 'Test Mfr',
#                     'Description': 'Test Part',
#                     'DataSheetUrl': 'http://example.com',
#                     'PriceBreaks': [{'Price': '1.23'}],
#                     'AvailabilityInStock': '100'
#                 }
#             ]
#         }
#     }
    
#     with patch.object(sys, 'argv', ['script.py'] + test_args):
#         with patch.dict('os.environ', {'MOUSER_API_KEY': 'test_key', 'ANTHROPIC_API_KEY': 'test_key'}):
#             with patch('pcb_part_finder.mouser_api.search_mouser_by_keyword', return_value=mock_mouser_response['SearchResults']['Parts']):
#                 with patch('pcb_part_finder.mouser_api.search_mouser_by_mpn', return_value=mock_mouser_response['SearchResults']['Parts'][0]):
#                     with patch('builtins.open', mock_open(read_data="Test project notes")):
#                         with patch('pcb_part_finder.data_loader.reformat_csv_with_llm', return_value=str(input_file)):
#                             # Run main function
#                             main()

#                             # Check output
#                             captured = capsys.readouterr()
#                             assert "Loaded project notes" in captured.out

@patch('pcb_part_finder.core.data_loader.load_input_csv')
def test_main_data_loader_error(mock_load_input, tmp_path, capsys):
    """Test main function handling DataLoaderError."""
    # Create test files
    input_file = tmp_path / "test.csv"
    notes_file = tmp_path / "notes.txt"
    input_file.write_text("invalid csv content")
    notes_file.write_text("Test project notes")

    # Mock command line arguments
    test_args = ['--input', str(input_file), '--notes', str(notes_file)]
    
    # Mock load_input_csv to raise DataLoaderError
    mock_load_input.side_effect = DataLoaderError("Test error")
    
    with patch.object(sys, 'argv', ['script.py'] + test_args):
        with patch.dict('os.environ', {'MOUSER_API_KEY': 'test_key', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('builtins.open', mock_open(read_data="Test project notes")):
                with pytest.raises(SystemExit):
                    main()

                # Check error output
                captured = capsys.readouterr()
                assert "Error loading input data" in captured.err

# @patch('pcb_part_finder.core.data_loader.load_input_csv')
# def test_main_output_writer_error(mock_load_input, tmp_path, capsys):
#     """Test main function handling OutputWriterError."""
#     # Create test files
#     input_file = tmp_path / "test.csv"
#     notes_file = tmp_path / "notes.txt"
#     input_file.write_text("Qty,Description,Possible MPN,Package,Notes/Source\n1,Test Part,ABC123,SMD,Test Note")
#     notes_file.write_text("Test project notes")

#     # Mock command line arguments
#     test_args = ['--input', str(input_file), '--notes', str(notes_file)]
    
#     # Mock load_input_csv to return valid data
#     mock_load_input.return_value = [{
#         'Qty': '1',
#         'Description': 'Test Part',
#         'Possible MPN': 'ABC123',
#         'Package': 'SMD',
#         'Notes/Source': 'Test Note'
#     }]
    
#     # Mock initialize_output_csv to raise OutputWriterError
#     with patch('pcb_part_finder.main.initialize_output_csv', side_effect=OutputWriterError("Test error")):
#         with patch.object(sys, 'argv', ['script.py'] + test_args):
#             with patch.dict('os.environ', {'MOUSER_API_KEY': 'test_key', 'ANTHROPIC_API_KEY': 'test_key'}):
#                 with patch('builtins.open', mock_open(read_data="Test project notes")):
#                     with patch('pcb_part_finder.data_loader.reformat_csv_with_llm', return_value=str(input_file)):
#                         with pytest.raises(SystemExit):
#                             main()

#                         # Check error output
#                         captured = capsys.readouterr()
#                         assert "Error writing output" in captured.err or "Test error" in captured.err 