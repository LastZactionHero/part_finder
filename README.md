# PCB Part Selection Streamlining Tool

## Overview

This tool automates and streamlines the part selection process for PCB design by matching approximate parts listed in a CSV file to real Mouser parts using the Mouser API, with the aid of an LLM for evaluating relevance.

The tool takes an input CSV file containing part descriptions and uses a two-pass LLM approach to:
1. Generate optimal search terms for the Mouser API
2. Evaluate and select the best matching part from Mouser's search results

## Features

- Automated part matching using Mouser's API
- Intelligent search term generation using LLM
- Context-aware part evaluation considering:
  - Project requirements and constraints
  - Previously selected parts
  - Availability and pricing
  - Package compatibility
  - Manufacturer preferences
- Detailed output CSV with comprehensive part information
- Robust error handling and logging

## Prerequisites

- Python 3.8 or higher
- Mouser API key
- Anthropic Claude API key
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd part_finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export MOUSER_API_KEY="your_mouser_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

## Usage

The tool is run from the command line with the following arguments:

```bash
python part_finder.py --input <input_csv_path> --notes <project_notes_path>
```

### Arguments

- `--input`: Path to the input CSV file containing part descriptions
- `--notes`: Path to the project notes file containing requirements and constraints

### Input CSV Format

The input CSV should have the following columns:
- `Qty`: Quantity needed
- `Description`: Part description
- `Possible MPN`: Manufacturer part number (if known)
- `Package`: Package type
- `Notes/Source`: Additional notes or source information

### Output

The tool generates a `bom_matched.csv` file containing:
- Original input data
- Matched Mouser part information
- Match status
- Detailed part specifications
- Pricing and availability information

## Testing

### Running Tests

The project includes both unit tests and integration tests. To run all tests:

```bash
python -m pytest tests/
```

### Test Categories

1. **Unit Tests**
   - Search term generation
   - Mouser API interaction
   - LLM evaluation logic
   - CSV handling
   - Data extraction

2. **Integration Tests**
   - End-to-end workflow
   - API interaction
   - Error handling

3. **Error Handling Tests**
   - Invalid file paths
   - API errors
   - Data format issues

### Running Specific Tests

To run specific test categories:

```bash
# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run tests with coverage report
python -m pytest --cov=part_finder tests/
```

## Error Handling

The tool includes comprehensive error handling for:
- Mouser API errors
- LLM API errors
- Data parsing errors
- File handling errors
- No matches/LLM selection failures

Errors are logged and appropriate status messages are written to the output CSV.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Specify your license here]

## Acknowledgments

- Mouser Electronics for their API
- Anthropic for Claude LLM 