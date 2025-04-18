document.addEventListener('DOMContentLoaded', function() {
    const componentInput = document.getElementById('componentInput');
    const submitButton = document.getElementById('submitButton');
    const projectNameInput = document.getElementById('projectNameInput');
    const projectDescriptionInput = document.getElementById('projectDescriptionInput');
    const processingResultsSection = document.getElementById('processing-results-section');
    const statusMessageContainer = document.getElementById('statusMessageContainer');
    const statusMessage = document.getElementById('statusMessage');
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsTableContainer = document.getElementById('resultsTableContainer');
    const resultsTable = document.getElementById('resultsTable');
    const queueInfoContainer = document.getElementById('queueInfoContainer');
    const queueLength = document.getElementById('queueLength');

    let currentJobId = null;
    let pollingInterval = null;

    // Enable submit button when there's input
    function checkInput() {
        submitButton.disabled = !componentInput.value.trim() || !projectNameInput.value.trim();
    }

    componentInput.addEventListener('input', checkInput);
    projectNameInput.addEventListener('input', checkInput);

    // Function to update queue length
    async function updateQueueLength() {
        try {
            const response = await fetch(`${window.API_BASE_URL}/queue_length`);
            const data = await response.json();
            queueLength.textContent = `${data.queue_length} jobs in queue`;
        } catch (error) {
            console.error('Error fetching queue length:', error);
            queueLength.textContent = 'Queue status unavailable';
        }
    }

    // Initial queue length update and start polling
    updateQueueLength();
    setInterval(updateQueueLength, 5000); // Update every 5 seconds

    // Submit components
    submitButton.addEventListener('click', async function() {
        try {
            submitButton.disabled = true;
            const response = await fetch(`${window.API_BASE_URL}/submit_job`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    components: componentInput.value,
                    project_name: projectNameInput.value,
                    project_description: projectDescriptionInput.value
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            currentJobId = data.job_id;

            // Show processing section and start polling
            processingResultsSection.classList.remove('hidden');
            statusMessage.textContent = 'Processing your request...';
            startPolling();

        } catch (error) {
            console.error('Error:', error);
            statusMessage.textContent = 'Error submitting components. Please try again.';
            submitButton.disabled = false;
        }
    });

    // Poll for results
    function startPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        pollingInterval = setInterval(async function() {
            try {
                const response = await fetch(`${window.API_BASE_URL}/job_status/${currentJobId}`);
                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(pollingInterval);
                    displayResults(data.results);
                    submitButton.disabled = false;
                } else if (data.status === 'failed') {
                    clearInterval(pollingInterval);
                    statusMessage.textContent = 'Job failed. Please try again.';
                    submitButton.disabled = false;
                } else {
                    statusMessage.textContent = `Processing... ${data.progress || ''}`;
                }
            } catch (error) {
                console.error('Error polling for results:', error);
                clearInterval(pollingInterval);
                statusMessage.textContent = 'Error checking job status. Please try again.';
                submitButton.disabled = false;
            }
        }, 1000);
    }

    // Display results in the table
    function displayResults(results) {
        statusMessage.textContent = 'Processing complete!';
        resultsHeader.classList.remove('hidden');
        resultsTableContainer.classList.remove('hidden');

        const tbody = resultsTable.querySelector('tbody');
        tbody.innerHTML = '';

        results.forEach(result => {
            const row = document.createElement('tr');
            
            // Add quantity cell
            const qtyCell = document.createElement('td');
            qtyCell.textContent = result.quantity || '-';
            row.appendChild(qtyCell);

            // Add description cell
            const descCell = document.createElement('td');
            descCell.textContent = result.description || '-';
            row.appendChild(descCell);

            // Add part number cell
            const partCell = document.createElement('td');
            partCell.textContent = result.mouser_part || '-';
            row.appendChild(partCell);

            // Add manufacturer cell
            const mfgCell = document.createElement('td');
            mfgCell.textContent = result.manufacturer || '-';
            row.appendChild(mfgCell);

            // Add status cell
            const statusCell = document.createElement('td');
            statusCell.textContent = result.status || '-';
            row.appendChild(statusCell);

            // Add price cell
            const priceCell = document.createElement('td');
            priceCell.textContent = result.price ? `$${result.price}` : '-';
            row.appendChild(priceCell);

            // Add availability cell
            const availCell = document.createElement('td');
            availCell.textContent = result.availability || '-';
            row.appendChild(availCell);

            // Add URL cell
            const urlCell = document.createElement('td');
            if (result.url) {
                const link = document.createElement('a');
                link.href = result.url;
                link.textContent = 'View';
                link.target = '_blank';
                urlCell.appendChild(link);
            } else {
                urlCell.textContent = '-';
            }
            row.appendChild(urlCell);

            tbody.appendChild(row);
        });
    }
}); 