# PCB Part Finder Queue Processing System

This system processes a queue of PCB part finding projects automatically. Each project in the queue is processed sequentially, and the results are moved to a finished directory when complete.

## Directory Structure

The system uses two main directories:

- `projects/queue/`: Contains projects waiting to be processed
- `projects/finished/`: Contains completed projects

## Project Structure

Each project should be a directory containing:

- `initial_bom.csv`: The input BOM file
- `project_details.txt`: Project notes and requirements

Example structure:
```
projects/
├── queue/
│   └── project1/
│       ├── initial_bom.csv
│       └── project_details.txt
└── finished/
    └── project1/
        ├── initial_bom.csv
        ├── project_details.txt
        ├── bom_matched.csv
        └── results.json
```

## Processing Flow

1. The system checks the queue directory for projects
2. Projects are processed in alphabetical order
3. Each project is validated to ensure required files exist
4. The project is processed using the PCB Part Finder tool
5. Results are saved in the project directory
6. The project is moved to the finished directory
7. A results.json file is created with processing status and timestamps

## Results File

The `results.json` file contains:
- `status`: "complete" or "failed"
- `start_time`: ISO format timestamp of when processing started
- `end_time`: ISO format timestamp of when processing ended

## Running the Queue Processor

To start processing the queue:

```bash
python process_queue.py
```

The processor will:
- Run continuously, checking for new projects every minute
- Process projects in alphabetical order
- Log all activities to the console
- Handle errors gracefully and continue processing

## Error Handling

If a project fails processing:
- It will be moved to the finished directory
- A results.json file will be created with status "failed"
- The error will be logged
- The processor will continue with the next project 