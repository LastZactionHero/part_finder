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

# PCB Part Finder API Documentation

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Create a New Project
```
POST /project
```

Creates a new project with a BOM (Bill of Materials) for processing.

**Request Body:**
```json
{
  "components": [
    {
      "qty": 1,
      "description": "10k 1% 0805 resistor",
      "possible_mpn": "RC0805FR-0710KL",
      "package": "0805",
      "notes": "Precision voltage divider"
    }
  ],
  "project_description": "My Project"
}
```

**Response:**
```json
{
  "project_id": "20250415_154254_z6tb",
  "truncation_info": null
}
```

**Notes:**
- Maximum of 20 components per BOM (will be truncated if exceeded)
- `truncation_info` will contain a message if truncation occurred
- Project ID format: `YYYYMMDD_HHMMSS_XXXX` where XXXX is a random 4-character string

### 2. Get Project Status
```
GET /project/{project_id}
```

Retrieves the current status and details of a project.

**Response (Queued Status):**
```json
{
  "status": "queued",
  "position": 1,
  "total_in_queue": 1,
  "bom": {
    "components": [
      {
        "qty": 1,
        "description": "10k 1% 0805 resistor",
        "possible_mpn": "RC0805FR-0710KL",
        "package": "805",
        "notes": "Precision voltage divider"
      }
    ],
    "project_description": "My Project"
  }
}
```

**Response (Finished Status):**
```json
{
  "status": "finished",
  "bom": {
    "components": [
      {
        "qty": 1,
        "description": "10k 1% 0805 resistor",
        "possible_mpn": "RC0805FR-0710KL",
        "package": "805",
        "notes": "Precision voltage divider",
        "mouser_part_number": "603-RC0805FR-0710KL",
        "manufacturer_part_number": "RC0805FR-0710KL",
        "manufacturer_name": "YAGEO",
        "mouser_description": "Thick Film Resistors - SMD 10 kOhms 125 mW 0805 1%",
        "datasheet_url": "https://www.mouser.com/datasheet/2/447/YAGEO_PYu_RC_Group_51_RoHS_L_12-3313492.pdf",
        "price": 0.14,
        "availability": "In Stock",
        "match_status": "Matched"
      }
    ],
    "project_description": "My Project",
    "match_date": "2025-04-15T15:43:06.907602",
    "match_status": "complete"
  },
  "results": {
    "status": "complete",
    "start_time": "2025-04-15T15:42:55.110870",
    "end_time": "2025-04-15T15:43:06.907602"
  }
}
```

**Notes:**
- Status can be either "queued" or "finished"
- For queued projects, includes position in queue and total queue length
- For finished projects, includes complete matching results and processing timestamps
- Returns 404 if project not found

### 3. Delete Project
```
DELETE /project/{project_id}
```

Deletes a project from the queue (only works for queued projects).

**Response:**
```json
{
  "status": "deleted"
}
```

**Notes:**
- Returns 404 if project not found in queue
- Cannot delete finished projects

### 4. Get Queue Length
```
GET /queue_length
```

Returns the current number of projects in the processing queue.

**Response:**
```json
{
  "queue_length": 1
}
```

## Error Responses

All endpoints may return the following error responses:

- `404 Not Found`: Project does not exist
- `500 Internal Server Error`: Server-side processing error

## Processing Details

1. Projects are processed in the order they are received
2. Each project goes through the following stages:
   - Queued: Project is waiting to be processed
   - Processing: Project is being matched with Mouser parts
   - Finished: Project has completed processing (success or failure)

3. Processing includes:
   - Part matching with Mouser's catalog
   - Price and availability checking
   - Datasheet URL retrieval
   - Manufacturer information lookup

4. Results are stored in the following format:
   - Original BOM information
   - Matched Mouser part numbers
   - Manufacturer details
   - Pricing information
   - Availability status
   - Processing timestamps

## Rate Limits

- No explicit rate limits on the API
- However, the underlying Mouser API has rate limits that may affect processing speed
- Projects are processed sequentially to avoid overwhelming external APIs

## Environment Requirements

The API requires the following environment variables:
- `MOUSER_API_KEY`: API key for Mouser's catalog
- `ANTHROPIC_API_KEY`: API key for the LLM service 