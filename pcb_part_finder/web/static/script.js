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

// Update the results table
function updateResultsTable(components) {
    resultsTable.innerHTML = '';
    components.forEach(component => {
        const row = resultsTable.insertRow();
        row.insertCell(0).textContent = component.qty;
        row.insertCell(1).textContent = component.description;
        
        const mouserCell = row.insertCell(2);
        const statusCell = row.insertCell(3); // Add a cell for explicit status
        const manufacturerCell = row.insertCell(4);
        const priceCell = row.insertCell(5);
        const availabilityCell = row.insertCell(6);

        // Set default/pending values
        mouserCell.textContent = '-';
        statusCell.textContent = 'Pending...'; 
        statusCell.classList.add('status-pending');
        manufacturerCell.textContent = 'N/A';
        priceCell.textContent = 'N/A';
        availabilityCell.textContent = 'N/A';
        
        if (component.match_status === 'matched' && component.mouser_part_number) {
            const link = document.createElement('a');
            link.href = `https://www.mouser.com/ProductDetail/${component.mouser_part_number}`;
            link.textContent = component.mouser_part_number;
            link.target = '_blank';
            mouserCell.innerHTML = ''; // Clear default '-'
            mouserCell.appendChild(link);
            statusCell.textContent = 'Matched';
            statusCell.classList.remove('status-pending');
            statusCell.classList.add('status-matched');
            manufacturerCell.textContent = component.manufacturer_name || 'N/A';
            priceCell.textContent = component.price ? `$${component.price.toFixed(2)}` : 'N/A'; // Format price
            availabilityCell.textContent = component.availability || 'N/A';
        } else if (component.match_status && component.match_status !== 'pending') {
            // Any status other than pending or matched indicates a finished non-match
            mouserCell.textContent = '-'; // Keep default '-'
            statusCell.textContent = 'No Match'; // Or use component.match_status for detail?
            statusCell.classList.remove('status-pending');
            statusCell.classList.add('status-no-match');
            // Keep N/A for other fields
        }
        // If status is still 'pending', the defaults are already set
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