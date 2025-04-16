"""FastAPI application for the PCB Part Finder API."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .projects import router as projects_router

app = FastAPI(
    title="PCB Part Finder API",
    description="API for finding electronic components on Mouser",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(projects_router)

@app.get("/")
async def root():
    """Root endpoint that returns a simple message."""
    return {"message": "Welcome to the PCB Part Finder API"}

@app.get("/queue_length")
async def queue_length_redirect():
    """Redirect from old queue_length endpoint to new one."""
    return RedirectResponse(url="/project/queue/length") 