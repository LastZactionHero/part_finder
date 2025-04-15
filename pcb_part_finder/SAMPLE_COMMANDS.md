curl -X DELETE "http://localhost:8000/project/20250415_143902_fqrm"

curl "http://localhost:8000/project/20250415_143902_fqrm"


curl -X POST "http://localhost:8000/project" \
     -H "Content-Type: application/json" \
     -d '{
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
     }'

# Get project status
curl "http://localhost:8000/project/{project_id}"

# Get queue length
curl "http://localhost:8000/queue_length"

# Delete a project
curl -X DELETE "http://localhost:8000/project/{project_id}"

curl "http://localhost:8000/project/20250415_154254_z6tb"
