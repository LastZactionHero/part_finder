from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime
import random
import string

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# Configure CORS to allow requests from all origins in development
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# In-memory storage for projects (replace with database in production)
projects = {}
queue = []

def generate_project_id():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{timestamp}_{random_str}"

@app.route('/')
def index():
    api_url = os.environ.get('API_URL', 'http://localhost:8000')
    return render_template('index.html', api_url=api_url)

@app.route('/project', methods=['POST'])
def create_project():
    data = request.json
    project_id = generate_project_id()
    
    # Create project entry
    projects[project_id] = {
        'status': 'queued',
        'bom': {
            'components': data['components'],
            'project_description': data['project_description'],
            'match_date': None,
            'match_status': 'pending'
        },
        'results': {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'end_time': None
        }
    }
    
    # Add to queue
    queue.append(project_id)
    
    return jsonify({
        'project_id': project_id,
        'truncation_info': None
    })

@app.route('/project/<project_id>')
def get_project(project_id):
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    project = projects[project_id]
    
    if project['status'] == 'queued':
        position = queue.index(project_id) + 1
        return jsonify({
            'status': 'queued',
            'position': position,
            'total_in_queue': len(queue),
            'bom': project['bom']
        })
    else:
        return jsonify({
            'status': 'finished',
            'bom': project['bom'],
            'results': project['results']
        })

@app.route('/queue_length')
def get_queue_length():
    return jsonify({
        'queue_length': len(queue)
    })

if __name__ == '__main__':
    app.run(debug=True, port=8000) 