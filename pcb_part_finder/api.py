import os
import shutil
import string
import random
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .schemas import InputBOM, MatchedBOM

app = FastAPI(title="PCB Part Finder API")

# Ensure projects directories exist
PROJECTS_DIR = Path("projects")
QUEUE_DIR = PROJECTS_DIR / "queue"
FINISHED_DIR = PROJECTS_DIR / "finished"

for dir_path in [PROJECTS_DIR, QUEUE_DIR, FINISHED_DIR]:
    dir_path.mkdir(exist_ok=True)

def generate_project_id() -> str:
    """Generate a unique project ID with timestamp and random chars."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{timestamp}_{random_chars}"

def bom_to_dataframe(bom: InputBOM) -> pd.DataFrame:
    """Convert InputBOM to pandas DataFrame for CSV storage."""
    data = []
    for comp in bom.components:
        data.append({
            'Qty': comp.qty,
            'Description': comp.description,
            'Possible MPN': comp.possible_mpn,
            'Package': str(comp.package),
            'Notes/Source': comp.notes
        })
    return pd.DataFrame(data)

def dataframe_to_bom(df: pd.DataFrame, project_description: str) -> InputBOM:
    """Convert pandas DataFrame to InputBOM."""
    components = []
    for _, row in df.iterrows():
        components.append({
            'qty': int(row['Qty']),
            'description': str(row['Description']),
            'possible_mpn': str(row['Possible MPN']) if pd.notna(row['Possible MPN']) else None,
            'package': str(row['Package']),
            'notes': str(row['Notes/Source']) if pd.notna(row['Notes/Source']) else None
        })
    return InputBOM(components=components, project_description=project_description)

def read_project_details(project_dir: Path) -> tuple[str, dict]:
    """Read project details and results from a project directory."""
    project_description = ""
    results = {}
    
    # Read project description
    if (project_dir / "project_details.txt").exists():
        with open(project_dir / "project_details.txt", "r") as f:
            project_description = f.read()
    
    # Read results.json if it exists
    if (project_dir / "results.json").exists():
        with open(project_dir / "results.json", "r") as f:
            results = json.load(f)
    
    return project_description, results

@app.post("/project")
async def create_project(bom: InputBOM):
    """Create a new project with BOM data."""
    try:
        # Truncate to 20 components if needed
        truncation_info = None
        if len(bom.components) > 20:
            truncation_info = f"BOM truncated from {len(bom.components)} to 20 components"
            bom.components = bom.components[:20]
        
        # Generate project ID and create directory
        project_id = generate_project_id()
        project_dir = QUEUE_DIR / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Convert to DataFrame and save as CSV
        df = bom_to_dataframe(bom)
        df.to_csv(project_dir / "initial_bom.csv", index=False)
        
        # Save project description
        if bom.project_description:
            with open(project_dir / "project_details.txt", "w") as f:
                f.write(bom.project_description)
        
        return {
            "project_id": project_id,
            "truncation_info": truncation_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/project/{project_id}")
async def get_project(project_id: str):
    """Get project status and details."""
    # Check if project exists in queue
    queue_path = QUEUE_DIR / project_id
    if queue_path.exists():
        # Get queue position
        queue_items = sorted([d for d in QUEUE_DIR.iterdir() if d.is_dir()])
        position = queue_items.index(queue_path) + 1 if queue_path in queue_items else None
        
        # Read the input BOM
        df = pd.read_csv(queue_path / "initial_bom.csv")
        project_description, _ = read_project_details(queue_path)
        
        bom = dataframe_to_bom(df, project_description)
        
        return {
            "status": "queued",
            "position": position,
            "total_in_queue": len(queue_items),
            "bom": bom.model_dump()
        }
    
    # Check if project exists in finished
    finished_path = FINISHED_DIR / project_id
    if finished_path.exists():
        try:
            # Read the matched BOM
            df = pd.read_csv(finished_path / "bom_matched.csv")
            project_description, results = read_project_details(finished_path)
            
            # Convert to MatchedBOM format
            components = []
            for _, row in df.iterrows():
                component = {
                    'qty': int(row['Qty']),
                    'description': str(row['Description']),
                    'possible_mpn': str(row['Possible MPN']) if pd.notna(row['Possible MPN']) else None,
                    'package': str(row['Package']),
                    'notes': str(row['Notes/Source']) if pd.notna(row['Notes/Source']) else None,
                    'mouser_part_number': str(row.get('Mouser Part Number')) if pd.notna(row.get('Mouser Part Number')) else None,
                    'manufacturer_part_number': str(row.get('Manufacturer Part Number')) if pd.notna(row.get('Manufacturer Part Number')) else None,
                    'manufacturer_name': str(row.get('Manufacturer Name')) if pd.notna(row.get('Manufacturer Name')) else None,
                    'mouser_description': str(row.get('Mouser Description')) if pd.notna(row.get('Mouser Description')) else None,
                    'datasheet_url': str(row.get('Datasheet URL')) if pd.notna(row.get('Datasheet URL')) else None,
                    'price': float(row.get('Price').replace('$', '')) if pd.notna(row.get('Price')) else None,
                    'availability': str(row.get('Availability')) if pd.notna(row.get('Availability')) else None,
                    'match_status': str(row.get('Match Status')) if pd.notna(row.get('Match Status')) else None
                }
                components.append(component)
            
            matched_bom = MatchedBOM(
                components=components,
                project_description=project_description,
                match_date=results.get('end_time', datetime.now().isoformat()),
                match_status=results.get('status', 'complete')
            )
            
            return {
                "status": "finished",
                "bom": matched_bom.model_dump(),
                "results": results
            }
        except FileNotFoundError:
            return {
                "status": "finished",
                "bom": None,
                "results": None
            }
    
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/project/{project_id}")
async def delete_project(project_id: str):
    """Delete a project from the queue."""
    queue_path = QUEUE_DIR / project_id
    if not queue_path.exists():
        raise HTTPException(status_code=404, detail="Project not found in queue")
    
    try:
        shutil.rmtree(queue_path)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue_length")
async def get_queue_length():
    """Get the current length of the processing queue."""
    queue_items = [d for d in QUEUE_DIR.iterdir() if d.is_dir()]
    return {"queue_length": len(queue_items)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 