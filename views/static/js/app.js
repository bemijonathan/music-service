// Tab switching functionality
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));

    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Show selected tab content
    document.getElementById(tabName).classList.add('active');

    // Add active class to clicked tab
    event.target.classList.add('active');
}

// API testing functions
async function makeRequest(method, url, data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();
        return { status: response.status, data: result };
    } catch (error) {
        return { status: 0, data: { error: error.message } };
    }
}

function displayResponse(elementId, response) {
    const element = document.getElementById(elementId);
    element.classList.add('show');

    let statusClass = 'info';
    if (response.status >= 200 && response.status < 300) {
        statusClass = 'success';
    } else if (response.status >= 400) {
        statusClass = 'error';
    }

    element.innerHTML = `
        <div class="status ${statusClass}">Status: ${response.status}</div>
        <pre>${JSON.stringify(response.data, null, 2)}</pre>
    `;
}

// Form handlers
document.addEventListener('DOMContentLoaded', () => {
    // Create Song Form
    const createSongForm = document.getElementById('createSongForm');
    if (createSongForm) {
        createSongForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = {
                title: formData.get('title'),
                genre: formData.get('genre'),
                mood: formData.get('mood'),
                theme: formData.get('theme'),
                style: formData.get('style')
            };

            const response = await makeRequest('POST', '/create_song', data);
            displayResponse('createSongResponse', response);
        });
    }

    // Check Status Form
    const checkStatusForm = document.getElementById('checkStatusForm');
    if (checkStatusForm) {
        checkStatusForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const taskId = document.getElementById('taskId').value;
            const response = await makeRequest('GET', `/check_status/${taskId}`);
            displayResponse('checkStatusResponse', response);
        });
    }

    // Download Form
    const downloadForm = document.getElementById('downloadForm');
    if (downloadForm) {
        downloadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = {
                audio_url: formData.get('audioUrl')
            };

            const response = await makeRequest('POST', '/download', data);
            displayResponse('downloadResponse', response);
        });
    }
});

// Health check function
async function checkHealth() {
    const response = await makeRequest('GET', '/health');
    displayResponse('healthResponse', response);
}

// Auto-refresh status check if we have a task ID
let statusCheckInterval;

function startStatusChecking(taskId) {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    statusCheckInterval = setInterval(async () => {
        const response = await makeRequest('GET', `/check_status/${taskId}`);
        displayResponse('checkStatusResponse', response);

        // Stop checking if song is completed or failed
        if (response.data.status === 'completed' || response.data.status === 'failed') {
            clearInterval(statusCheckInterval);
        }
    }, 5000); // Check every 5 seconds
}

// Listen for successful song creation to start status checking
document.addEventListener('DOMContentLoaded', () => {
    const createSongForm = document.getElementById('createSongForm');
    if (createSongForm) {
        createSongForm.addEventListener('submit', () => {
            // After form submission, we'll check the response
            setTimeout(() => {
                const response = document.getElementById('createSongResponse');
                if (response?.classList.contains('show')) {
                    try {
                        const responseData = JSON.parse(response.querySelector('pre').textContent);
                        if (responseData.task_id) {
                            document.getElementById('taskId').value = responseData.task_id;
                            startStatusChecking(responseData.task_id);
                        }
                    } catch {
                        // Ignore parsing errors
                    }
                }
            }, 1000);
        });
    }
});
