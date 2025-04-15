# PCB Part Finder Web Application

This is the web frontend and API for the PCB Part Finder tool. It provides a user-friendly interface for submitting component lists and viewing matched Mouser parts.

## Prerequisites

- Python 3.8 or higher
- All dependencies listed in the root `requirements.txt` file

## Installation

1. Install the required dependencies:
```bash
pip install -r ../requirements.txt
```

## Running the Application

### Development Mode

1. Start the Flask server:
```bash
cd web
python server.py
```

The application will be available at:
- Web interface: http://localhost:8000
- API endpoints: http://localhost:8001/api/*

### Production Mode

For production use, it's recommended to use a production-grade WSGI server like Gunicorn:

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Start the server:
```bash
cd web
gunicorn server:app -b 0.0.0.0:8000
```

## API Documentation

### Base URL
```
http://localhost:8001
```

### Endpoints

#### 1. Create a New Project
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

#### 2. Get Project Status
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
    "components": [...],
    "project_description": "My Project"
  }
}
```

**Response (Finished Status):**
```json
{
  "status": "finished",
  "bom": {
    "components": [...],
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

#### 3. Get Queue Length
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

## Development Notes

- The server uses in-memory storage for projects and queue. In a production environment, this should be replaced with a proper database.
- The API is designed to work with the existing PCB Part Finder backend. Make sure the backend service is running and properly configured.
- CORS is not currently configured. If you need to access the API from a different domain, you'll need to add CORS headers.

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON body with an error message:
```json
{
  "error": "Error message description"
}
```

## Environment Variables

The following environment variables are required:
- `MOUSER_API_KEY`: API key for Mouser's catalog
- `ANTHROPIC_API_KEY`: API key for the LLM service

These should be set in your environment or in a `.env` file in the project root. 