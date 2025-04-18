// API base URL - use the exposed port on localhost
const API_BASE_URL = 'http://localhost:8000';

// DOM elements
const componentInput = document.getElementById('componentInput');
const projectNameInput = document.getElementById('projectNameInput');
const projectDescriptionInput = document.getElementById('projectDescriptionInput');
const submitButton = document.getElementById('submitButton');
const processingResultsSection = document.getElementById('processing-results-section'); // Updated: Combined section
const queueInfoContainer = document.getElementById('queueInfoContainer'); // Container for queue info
const statusMessageContainer = document.getElementById('statusMessageContainer'); // Container for status messages
const statusMessage = document.getElementById('statusMessage');
const resultsHeader = document.getElementById('resultsHeader'); // Header for results table
const resultsTableContainer = document.getElementById('resultsTableContainer'); // Container for results table
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
        // Check if the number of values matches the number of headers OR if it's a single value line
        if (values.length === headers.length) {
            headers.forEach((header, index) => {
                const apiField = fieldMap[header] || header.toLowerCase(); // Map or use lowercased header
                component[apiField] = values[index];
            });
        } else if (values.length === 1 && values[0]) { // Handle single description per line
            component.description = values[0];
            component.qty = '1'; // Default Qty
            component.possible_mpn = '';
            component.package = '';
            component.notes = 'Single column input';
        } else if (line.trim()) { // Catch other invalid lines
            console.warn(`Skipping invalid CSV row: ${line} (Parsed ${values.length} fields, expected ${headers.length} or 1)`);
            component.description = `${line}`; // Treat the whole line as description
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
async function createProject(projectName, projectDescription, components) {
    try {
        const response = await fetch(`${API_BASE_URL}/project`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project_name: projectName,
                project_description: projectDescription,
                components: components
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
        const mouserCell = row.insertCell();

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

        // Add Mouser link if available
        if (component.mouser_part_number) {
            const link = document.createElement('a');
            link.href = `https://www.mouser.com/ProductDetail/${component.mouser_part_number}`;
            link.textContent = component.mouser_part_number;
            link.target = '_blank';
            mouserCell.appendChild(link);
        } else {
            mouserCell.textContent = 'Not matched';
        }
    });
}

// Poll project status
async function pollProjectStatus(projectId) {
    try {
        const status = await getProjectStatus(projectId);
        
        // Always show the main processing section once polling starts
        processingResultsSection.classList.remove('hidden');

        if (status.status === 'queued') {
            statusMessage.innerHTML = `
                <div class="status-message">
                    <p>Your project is in queue</p>
                    <p>Position: ${status.position} of ${status.total_in_queue}</p>
                </div>
            `;
            // Hide results table while queued
            resultsHeader.classList.add('hidden');
            resultsTableContainer.classList.add('hidden');
            queueInfoContainer.classList.remove('hidden'); // Show queue info
            setTimeout(() => pollProjectStatus(projectId), 10000); // Poll every 10 seconds
        } else if (status.status === 'processing') {
            statusMessage.innerHTML = `
                <div class="status-message">
                    <p>Your project is processing...</p>
                </div>
            `;
            // Update the table with partial results if available
            if (status.bom && status.bom.components && status.bom.components.length > 0) {
                updateResultsTable(status.bom.components);
                resultsHeader.classList.remove('hidden'); // Show results header
                resultsTableContainer.classList.remove('hidden'); // Show results table
            } else {
                // Hide results table if no components yet
                resultsHeader.classList.add('hidden');
                resultsTableContainer.classList.add('hidden');
            }
            queueInfoContainer.classList.add('hidden'); // Hide queue info while processing
            setTimeout(() => pollProjectStatus(projectId), 5000); // Poll faster (every 5 seconds)
        } else if (status.status === 'error') {
            statusMessage.innerHTML = '<div class="error">Processing failed.</div>';
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
            // Hide results table on error
            resultsHeader.classList.add('hidden');
            resultsTableContainer.classList.add('hidden');
            queueInfoContainer.classList.remove('hidden'); // Show queue info
        } else if (status.status === 'finished') {
            statusMessage.innerHTML = '<div class="success">Processing complete!</div>';
            updateResultsTable(status.bom.components);
            resultsHeader.classList.remove('hidden'); // Ensure results header is visible
            resultsTableContainer.classList.remove('hidden'); // Ensure results table is visible
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
            queueInfoContainer.classList.remove('hidden'); // Show queue info
        } else {
            statusMessage.innerHTML = `<div class="error">Unknown project status: ${status.status}</div>`;
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
            // Hide results table on unknown status
            resultsHeader.classList.add('hidden');
            resultsTableContainer.classList.add('hidden');
            queueInfoContainer.classList.remove('hidden'); // Show queue info
        }
    } catch (error) {
        statusMessage.innerHTML = `<div class="error">Error fetching status: ${error.message}</div>`;
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
        queueInfoContainer.classList.remove('hidden'); // Show queue info on error
    }
}

// Handle form submission
submitButton.addEventListener('click', async () => {
    try {
        const csv = componentInput.value.trim();
        if (!csv) {
            throw new Error('Please enter component data');
        }

        const projectName = projectNameInput.value.trim();
        const projectDescription = projectDescriptionInput.value.trim();

        /* Remove requirement for project name and description
        if (!projectName || !projectDescription) {
            throw new Error('Please enter both Project Name and Description');
        }
        */

        const components = parseCSV(csv);
        if (components.length === 0) {
            throw new Error('No valid components found in the input');
        }

        // Clear previous results and hide specific parts of the processing section
        resultsTable.innerHTML = '';
        resultsHeader.classList.add('hidden');
        resultsTableContainer.classList.add('hidden');

        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        processingResultsSection.classList.remove('hidden'); // Show the main container
        statusMessage.innerHTML = '<div class="status-message">Creating project...</div>';

        const projectId = await createProject(projectName, projectDescription, components);
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
        processingResultsSection.classList.remove('hidden'); // Show the container if project ID exists
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        pollProjectStatus(projectId);
    } else {
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
        // Ensure the processing section is hidden on initial load without a project ID
        processingResultsSection.classList.add('hidden');
    }
}); 