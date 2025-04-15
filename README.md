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
- Queue-based processing system for multiple projects
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
Create a `.env` file in the project root with:
```
MOUSER_API_KEY="your_mouser_api_key"
CLAUDE_API_KEY="your_anthropic_api_key"
```

## Project Structure

### Directory Layout
```
part_finder/
├── pcb_part_finder/          # Main package directory
│   ├── main.py              # Main processing logic
│   ├── data_loader.py       # Input file handling
│   ├── output_writer.py     # Output file handling
│   ├── mouser_api.py        # Mouser API integration
│   └── llm_handler.py       # LLM integration
├── projects/                # Project directories
│   ├── queue/              # Projects waiting to be processed
│   └── finished/           # Completed projects
├── tests/                  # Test suite
├── data/                   # Sample data and test files
├── .env                    # Environment variables
└── requirements.txt        # Python dependencies
```

### Projects Directory Structure

The `projects` directory contains two main subdirectories:

1. `queue/`: Contains projects waiting to be processed
2. `finished/`: Contains completed projects

Each project is a directory with the following structure:
```
projects/
├── queue/
│   └── project_name/
│       ├── initial_bom.csv        # Input BOM file
│       └── project_details.txt    # Project notes and requirements
└── finished/
    └── project_name/
        ├── initial_bom.csv        # Original input BOM
        ├── project_details.txt    # Original project notes
        ├── bom_matched.csv        # Generated output
        └── results.json           # Processing results
```

### File Formats

#### initial_bom.csv
Required columns:
- `Qty`: Quantity needed
- `Description`: Part description
- `Possible MPN`: Manufacturer part number (if known)
- `Package`: Package type
- `Notes/Source`: Additional notes or source information

Example:
```csv
Qty,Description,Possible MPN,Package,Notes/Source
1,10k 1% 0805 resistor,RC0805FR-0710KL,0805,Precision voltage divider
2,100nF 16V X7R capacitor,CL21B104KBCNNNC,0805,Power supply decoupling
```

#### project_details.txt
Plain text file containing project requirements and constraints. Should include:
- Project description
- Key requirements
- Special considerations
- Manufacturer preferences
- Any other relevant information

Example:
```
Project: Temperature Sensor Board
Requirements:
- Industrial temperature range (-40°C to +85°C)
- Low power consumption
- High accuracy (±0.5°C)
- RoHS compliant

Special Considerations:
- Prefer Texas Instruments for analog components
- Need long lead time parts ordered first
- Budget conscious design
```

#### results.json
Generated after processing, contains:
```json
{
    "status": "complete" | "failed",
    "start_time": "ISO-8601 timestamp",
    "end_time": "ISO-8601 timestamp"
}
```

#### bom_matched.csv
Output file with matched parts. Columns:
- Original input columns
- `Mouser Part Number`
- `Manufacturer Part Number`
- `Manufacturer Name`
- `Mouser Description`
- `Datasheet URL`
- `Price`
- `Availability`
- `Match Status`

## Queue Processing System

### Processing Order
1. Projects are processed in alphabetical order by directory name
2. Each project is processed completely before moving to the next
3. Failed projects are moved to finished directory with error status
4. System checks for new projects every 60 seconds

### Running the Queue Processor
```bash
python process_queue.py
```

The processor will:
- Run continuously
- Process projects in alphabetical order
- Log all activities to the console
- Handle errors gracefully
- Create results.json for each project
- Move completed projects to finished directory

### Error Handling
- Missing required files: Project moved to finished with "failed" status
- API errors: Logged and project marked as failed
- Processing errors: Logged and project marked as failed
- System continues processing next project after any error

## Testing

### Running Tests
```bash
python -m pytest tests/
```

### Test Categories
- Unit tests for each module
- Integration tests for the complete pipeline
- API interaction tests (mocked)
- File handling tests
- Error handling tests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

[Your chosen license] 