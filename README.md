# PCB Part Selection Streamlining Tool

## Overview

This tool automates and streamlines the part selection process for Printed Circuit Board (PCB) design. It takes an input CSV file containing approximate part descriptions, matches them to real parts using the Mouser Electronics API, and uses a Large Language Model (LLM) like Anthropic's Claude to evaluate the relevance and suitability of the potential matches.

## How it Works

The tool employs a queue-based system and a two-pass LLM approach:

1.  **Input:** A project is defined by an `initial_bom.csv` file (listing desired parts) and a `project_details.txt` file (containing project requirements and constraints) placed in a specific directory structure.
2.  **Queue Processing:** A dedicated script monitors a `queue` directory for new projects.
3.  **LLM Pass 1 (Search Term Generation):** For each part in the input CSV, the LLM generates optimal search terms based on the description and project context.
4.  **Mouser API Search:** The generated terms are used to query the Mouser API for potential matching parts.
5.  **LLM Pass 2 (Evaluation & Selection):** The LLM evaluates the Mouser search results against the original part description, project requirements, availability, pricing, package compatibility, and previously selected parts, selecting the best match.
6.  **Output:** A detailed `bom_matched.csv` file is generated with comprehensive information about the selected Mouser parts, along with a `results.json` file indicating the processing status.

## Features

-   Automated part matching using Mouser's API.
-   Intelligent search term generation via LLM.
-   Context-aware part evaluation considering:
    -   Project requirements and constraints.
    -   Previously selected parts within the same project.
    -   Part availability and pricing.
    -   Package compatibility.
    -   Manufacturer preferences.
-   Queue-based processing system handles multiple projects sequentially.
-   Detailed output CSV with matched part information.
-   Robust error handling and logging.

## Prerequisites

Before you begin, ensure you have the following:

-   **Python:** Version 3.8 or higher installed.
-   **API Keys:**
    -   Mouser API Key (obtainable from Mouser Electronics)
    -   Anthropic Claude API Key (obtainable from Anthropic)
-   **Required Python Packages:** Listed in `requirements.txt`.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd part_finder
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a file named `.env` in the project's root directory (`part_finder/`). Add your API keys to this file:
    ```dotenv
    MOUSER_API_KEY="your_mouser_api_key"
    ANTHROPIC_API_KEY="your_anthropic_api_key"
    ```

## Running Tests

The project includes a comprehensive test suite that can be run using Docker Compose. To run the tests:

1.  **Run all tests:**
    ```bash
    docker compose run --rm -v $(pwd)/tests:/app/tests api python -m pytest tests/ -v
    ```

Or a single test:

`docker compose run --rm -v $(pwd)/tests:/app/tests api python -m pytest tests/test_main.py::test_main_success -v`

Remove all docker images:

`docker system prune -a --volumes`

docker image prune -a
docker image prune -a -f

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker image prune -a -f
docker volume prune -f
docker volume rm part_finder_postgres_data

The test suite includes:
- Data loader tests (`test_data_loader.py`)
- Mouser API tests (`test_mouser_api.py`)
- Output writer tests (`test_output_writer.py`)
- Main application tests (`test_main.py`)

Note: The Docker Compose setup automatically handles the environment variables and dependencies, so you don't need to set up the `.env` file separately for testing.

## Running the Tool

The system consists of three main services that need to be run concurrently, typically each in its own terminal window.

1.  **Start the Queue Processor:**
    Monitors the `projects/queue/` directory and processes new projects.
    ```bash
    python -m pcb_part_finder queue
    ```

2.  **Start the API Server:**
    Handles project creation (though typically handled by file placement) and status queries. Runs on `http://localhost:8000`.
    ```bash
    python -m pcb_part_finder api
    ```

3.  **Start the Web Server (Optional UI):**
    Provides a user interface for interaction. Runs on `http://localhost:8000`.
    ```bash
    python -m pcb_part_finder web
    ```

You can also specify custom host and port for the API and web servers:
```bash
python -m pcb_part_finder api --host 0.0.0.0 --port 8080
python -m pcb_part_finder web --host 0.0.0.0 --port 8080
```

## Basic Workflow

1.  **Create Project Files:**
    * Prepare your Bill of Materials (BOM) as `initial_bom.csv`.
    * Write down project requirements in `project_details.txt`.
    * *(See File Formats section below for details)*.
2.  **Submit Project:**
    * Create a new directory for your project inside the `part_finder/projects/queue/` directory (e.g., `part_finder/projects/queue/my_sensor_board/`).
    * Place your `initial_bom.csv` and `project_details.txt` files inside this new project directory.
3.  **Processing:**
    * The **Queue Processor** (if running) will detect the new project directory and begin processing the `initial_bom.csv`.
4.  **Completion:**
    * Once finished, the project directory will be moved from `projects/queue/` to `projects/finished/`.
    * Inside the finished project directory (e.g., `part_finder/projects/finished/my_sensor_board/`), you will find the original input files along with the generated `bom_matched.csv` and `results.json`.

## Project Structure

### Directory Layout

```
part_finder/
├── src/                    # Source code directory
│   ├── process_queue.py    # Queue processing script
│   └── web/               # Web interface files
├── pcb_part_finder/        # Main package directory
│   ├── api.py             # API Server logic
│   ├── main.py            # Main processing logic
│   ├── data_loader.py     # Input file handling
│   ├── output_writer.py   # Output file handling
│   ├── mouser_api.py      # Mouser API integration
│   └── llm_handler.py     # LLM integration
├── projects/              # Project directories root
│   ├── queue/            # Projects waiting to be processed
│   └── finished/         # Completed projects
├── tests/                # Test suite
├── data/                 # Sample data and test files
├── .env                  # Environment variables (API Keys)
└── requirements.txt      # Python dependencies
```

### `projects` Directory

This directory manages the state of processing jobs:

-   `projects/queue/`: Place new project folders here to initiate processing. Each subfolder represents one project.
-   `projects/finished/`: Completed projects (both successful and failed) are moved here by the queue processor.

**Example Project Structure:**

```
projects/
├── queue/
│   └── project_name_A/        # Project waiting to be processed
│       ├── initial_bom.csv
│       └── project_details.txt
└── finished/
    └── project_name_B/        # Project already processed
        ├── initial_bom.csv        # Original input BOM
        ├── project_details.txt    # Original project notes
        ├── bom_matched.csv        # Generated output
        └── results.json           # Processing results metadata
```

## File Formats

### `initial_bom.csv`

The input CSV file containing the parts you need to find.

**Required Columns:**

-   `Qty`: Quantity needed for each part.
-   `Description`: A textual description of the part (e.g., "10k 1% 0805 resistor").
-   `Possible MPN`: Manufacturer Part Number, if known (can be approximate or empty).
-   `Package`: Desired component package type (e.g., "0805", "SOIC-8").
-   `Notes/Source`: Any additional notes, constraints, or source information relevant to this specific part.

**Example:**

```csv
Qty,Description,Possible MPN,Package,Notes/Source
1,10k 1% 0805 resistor,RC0805FR-0710KL,0805,Precision voltage divider component
2,100nF 16V X7R capacitor,CL21B104KBCNNNC,0805,"Power supply decoupling, must be X7R or better"
1,Microcontroller with USB,STM32F401,LQFP64,Main processor, needs at least 64KB RAM
```

### `project_details.txt`

A plain text file detailing the overall project requirements and constraints. This provides context for the LLM during part evaluation.

**Content Suggestions:**

-   Overall project goal or description.
-   Key performance requirements (e.g., temperature range, power limits, accuracy).
-   Compliance requirements (e.g., RoHS, automotive grade).
-   Preferred or excluded manufacturers.
-   Budget considerations.
-   Any other relevant constraints or preferences.

**Example:**

```
Project: Industrial Temperature Sensor Board

Requirements:
- Operating Temperature Range: -40°C to +85°C (Industrial)
- Low power consumption is critical.
- Target temperature accuracy: ±0.5°C after calibration.
- All components must be RoHS compliant.

Special Considerations:
- Prefer Texas Instruments or Analog Devices for analog ICs.
- Avoid parts with known long lead times if possible.
- Target BOM cost under $15 per unit in low volume.
```

### `results.json`

Generated in the `finished/project_name/` directory after processing is complete. Contains metadata about the processing run.

**Example:**

```json
{
    "status": "complete",
    "start_time": "2025-04-15T20:00:00.123456Z",
    "end_time": "2025-04-15T20:05:30.987654Z"
}
```

Possible `"status"` values include `"complete"` or `"failed"`.