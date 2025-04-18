// API base URL - use the exposed port on localhost
const API_BASE_URL = 'http://localhost:8000';

// DOM elements
const componentInput = document.getElementById('componentInput');
const submitButton = document.getElementById('submitButton');
const statusSection = document.getElementById('statusSection');
const statusMessage = document.getElementById('statusMessage');
const resultsSection = document.getElementById('resultsSection');
const resultsTable = document.getElementById('resultsTable').getElementsByTagName('tbody')[0];
const queueLength = document.getElementById('queueLength');

// Update queue length
async function updateQueueLength() {
    try {
        const response = await fetch(`${API_BASE_URL}/queue_length`);
        const data = await response.json();
        queueLength.textContent = `${data.queue_length} projects in queue`;
    } catch (error) {
        console.error('Error fetching queue length:', error);
        queueLength.textContent = 'Error loading queue status';
    }
}

// Parse CSV input using a regex approach to handle quoted fields
function parseCSV(csv) {
    const lines = csv.trim().split('\n');
    const headersLine = lines.shift(); // Remove header line
    if (!headersLine) return [];

    const headers = headersLine.split(',').map(h => h.trim());
    const components = [];

    // Regex to handle CSV fields, including quoted ones with commas
    const csvRegex = /(\s*"(?:[^"]*""|[^\\"]*)*"|[^,]+|,)(?:,|$)/g;

    // Map of CSV headers to API field names
    const fieldMap = {
        'Qty': 'qty',
        'Description': 'description',
        'Possible MPN': 'possible_mpn',
        'Package': 'package',
        'Notes/Source': 'notes'
    };

    lines.forEach(line => {
        if (!line.trim()) return; // Skip empty lines

        const values = [];
        let match;
        // Reset lastIndex since we're reusing the regex
        csvRegex.lastIndex = 0;
        // Use regex to extract fields
        while ((match = csvRegex.exec(line)) !== null) {
            let value = match[1];
            // If the value ends with a comma, it means the field was empty
            if (value === ',') {
                value = '';
            } else if (value.endsWith(',')) {
                value = value.slice(0, -1); // Remove trailing comma
            } 

            // Remove surrounding quotes and unescape double quotes
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1).replace(/""/g, '"');
            }
            values.push(value.trim());
            // Stop if the regex consumed the whole line
            if (match[0].endsWith(',')){
                csvRegex.lastIndex = match.index + match[0].length;
            } else {
                break; // End of line
            }
        }
        // Handle case where last field might be empty
        if (line.endsWith(',')) values.push('');


        const component = {};
        if (values.length === headers.length) {
            headers.forEach((header, index) => {
                const apiField = fieldMap[header] || header.toLowerCase();
                component[apiField] = values[index];
            });
        } else {
            // Handle invalid row format - less likely now but good fallback
            console.warn(`Skipping invalid CSV row: ${line} (Parsed ${values.length} fields, expected ${headers.length})`);
            component.description = `${line}`;
            component.qty = '1';
            component.possible_mpn = '';
            component.package = '';
            component.notes = 'Invalid row format';
        }
        components.push(component);
    });

    return components;
}

// Create a new project
async function createProject(components) {
    try {
        const response = await fetch(`${API_BASE_URL}/project`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                components: components,
                project_description: "Web UI Project"
            })
        });

        if (!response.ok) {
            throw new Error('Failed to create project');
        }

        const data = await response.json();
        return data.project_id;
    } catch (error) {
        console.error('Error creating project:', error);
        throw error;
    }
}

// Get project status
async function getProjectStatus(projectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/project/${projectId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch project status');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching project status:', error);
        throw error;
    }
}

// Update results table
function updateResultsTable(components) {
    resultsTable.innerHTML = ''; // Clear existing rows

    const statusDisplayMap = {
        'matched': 'Matched',
        'search_term_failed': 'No Match Found',
        'no_keyword_results': 'No Match Found',
        'evaluation_failed': 'LLM Evaluation Failed',
        'mpn_lookup_failed': 'Mouser Lookup Failed',
        'llm_error': 'LLM Evaluation Failed',
        'mouser_error': 'Mouser Lookup Failed',
        'component_db_error': 'System Error',
        'db_save_error': 'System Error',
        'processing_error': 'System Error',
        'worker_uncaught_exception': 'System Error',
        'error': 'System Error', // Generic internal error
        'pending': 'Processing...', // For items still in progress
        'no_match_record': 'No Match', // If backend uses this for finished items without a match record
    };
    const defaultStatusText = 'Unknown Status';

    components.forEach(component => {
        const row = resultsTable.insertRow();
        const qtyCell = row.insertCell();
        const descCell = row.insertCell();
        const mpnCell = row.insertCell(); // Manufacturer Part Number
        const manufCell = row.insertCell(); // Manufacturer Name
        const statusCell = row.insertCell();
        const priceCell = row.insertCell();
        const availCell = row.insertCell();
        const datasheetCell = row.insertCell();

        qtyCell.textContent = component.qty;
        descCell.textContent = component.description;
        mpnCell.textContent = component.manufacturer_part_number || 'N/A';
        manufCell.textContent = component.manufacturer_name || 'N/A';
        priceCell.textContent = component.price ? `$${component.price.toFixed(2)}` : 'N/A';
        availCell.textContent = component.availability || 'N/A';

        // Set status text using the map
        statusCell.textContent = statusDisplayMap[component.match_status] || defaultStatusText;

        // --- New CSS Class Logic ---
        // Helper function or logic to get the CSS class based on status
        const getStatusClass = (status) => {
            switch (status) {
                case 'matched':
                    return 'status-matched';
                case 'search_term_failed':
                case 'no_keyword_results':
                case 'no_match_record':
                    return 'status-no-match';
                case 'evaluation_failed':
                    return 'status-evaluation-needed';
                case 'mpn_lookup_failed':
                    return 'status-lookup-failed';
                case 'llm_error':
                case 'mouser_error':
                    return 'status-api-error';
                case 'component_db_error':
                case 'db_save_error':
                case 'processing_error':
                case 'worker_uncaught_exception':
                case 'error':
                    return 'status-system-error';
                case 'pending':
                    return 'status-pending';
                default:
                    return 'status-unknown';
            }
        };

        // Remove all potential status classes before adding the new one
        statusCell.classList.remove(
            'status-matched', 'status-no-match', 'status-evaluation-needed',
            'status-lookup-failed', 'status-api-error', 'status-system-error',
            'status-pending', 'status-unknown'
        );

        // Add the specific CSS class based on the status
        const statusClass = getStatusClass(component.match_status);
        statusCell.classList.add(statusClass);
        // --- End New CSS Class Logic ---

        // Add datasheet link if available
        if (component.datasheet_url) {
            const link = document.createElement('a');
            link.href = component.datasheet_url;
            link.textContent = 'Link';
            link.target = '_blank'; // Open in new tab
            datasheetCell.appendChild(link);
        } else {
            datasheetCell.textContent = 'N/A';
        }
    });
}

// Poll project status
async function pollProjectStatus(projectId) {
    try {
        const status = await getProjectStatus(projectId);
        
        if (status.status === 'queued') {
            statusMessage.innerHTML = `
                <div class="status-message">
                    <p>Your project is in queue</p>
                    <p>Position: ${status.position} of ${status.total_in_queue}</p>
                </div>
            `;
            setTimeout(() => pollProjectStatus(projectId), 10000); // Poll every 10 seconds
        } else if (status.status === 'processing') {
            statusMessage.innerHTML = `
                <div class="status-message">
                    <p>Your project is processing...</p>
                </div>
            `;
            // Update the table with partial results if available
            if (status.bom && status.bom.components) {
                updateResultsTable(status.bom.components);
                resultsSection.classList.remove('hidden');
            }
            setTimeout(() => pollProjectStatus(projectId), 5000); // Poll faster (every 5 seconds)
        } else if (status.status === 'error') {
            statusMessage.innerHTML = '<div class="error">Processing failed.</div>';
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
        } else if (status.status === 'finished') {
            statusMessage.innerHTML = '<div class="success">Processing complete!</div>';
            updateResultsTable(status.bom.components);
            resultsSection.classList.remove('hidden');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
        } else {
            statusMessage.innerHTML = `<div class="error">Unknown project status: ${status.status}</div>`;
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
        }
    } catch (error) {
        statusMessage.innerHTML = `<div class="error">Error fetching status: ${error.message}</div>`;
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
    }
}

// Handle form submission
submitButton.addEventListener('click', async () => {
    try {
        const csv = componentInput.value.trim();
        if (!csv) {
            throw new Error('Please enter component data');
        }

        const components = parseCSV(csv);
        if (components.length === 0) {
            throw new Error('No valid components found in the input');
        }

        // Clear previous results
        resultsTable.innerHTML = '';
        resultsSection.classList.add('hidden');

        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        statusSection.classList.remove('hidden');
        statusMessage.innerHTML = '<div class="status-message">Creating project...</div>';

        const projectId = await createProject(components);
        window.history.pushState({}, '', `?project=${projectId}`);
        await pollProjectStatus(projectId);
    } catch (error) {
        statusMessage.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
    }
});

// Check for project ID in URL on page load
window.addEventListener('load', () => {
    updateQueueLength();
    setInterval(updateQueueLength, 30000); // Update queue length every 30 seconds

    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('project');
    if (projectId) {
        statusSection.classList.remove('hidden');
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        pollProjectStatus(projectId);
    } else {
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
    }
}); 