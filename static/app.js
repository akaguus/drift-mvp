// API Base URL
const API_BASE = window.location.origin;

// State
let agents = [];
let selectedAgentId = null;
let autoRefreshIntervals = {};
let currentUser = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Get authenticated user from Flask session
    await loadUserProfile();

    // Load initial data
    await loadAgents();
    await refreshSchedulerStatus();
    await loadApiKeys();

    // Set up form submission
    document.getElementById('deployForm').addEventListener('submit', handleDeployAgent);

    // Start auto-refresh for agents (every 30 seconds)
    setInterval(() => loadAgents(), 30000);
    autoRefreshIntervals.agents = setInterval(() => loadAgents(), 30000);

    // Start auto-refresh for execution history (every 10 seconds if viewing an agent)
    autoRefreshIntervals.history = setInterval(() => {
        if (selectedAgentId) {
            loadExecutionHistory();
        }
    }, 10000);

    // Auto-refresh scheduler status every 60 seconds
    autoRefreshIntervals.scheduler = setInterval(() => refreshSchedulerStatus(), 60000);
}

// Load user profile from Flask session
async function loadUserProfile() {
    try {
        const response = await fetch(`${API_BASE}/api/me`);
        if (response.status === 401) {
            // Not authenticated - redirect to login
            window.location.href = `${API_BASE}/login`;
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load user profile');
        }

        currentUser = await response.json();
        document.getElementById('userId').textContent = currentUser.email;
        console.log('✓ User authenticated:', currentUser.email);
    } catch (error) {
        console.error('Error loading user profile:', error);
        // In development without Auth0, allow anonymous access
        if (window.location.hostname === 'localhost') {
            currentUser = { email: 'dev-user@example.com', name: 'Dev User' };
            document.getElementById('userId').textContent = 'Development Mode';
        }
    }
}

// Load all agents
async function loadAgents() {
    try {
        showLoading('agentsList', true);

        const response = await fetch(`${API_BASE}/agents`);
        if (!response.ok) {
            throw new Error('Failed to load agents');
        }

        const agentsList = await response.json();
        displayAgents(agentsList);
    } catch (error) {
        console.error('Error loading agents:', error);
        document.getElementById('agentsList').innerHTML = `
            <tr>
                <td colspan="6" class="loading">
                    <span>⚠️ Error loading agents</span>
                </td>
            </tr>
        `;
    }
}

// Display agents in table
function displayAgents(agentList) {
    const tbody = document.getElementById('agentsList');

    if (!agentList || agentList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="loading">No agents deployed yet. Create one to get started!</td>
            </tr>
        `;
        document.getElementById('selectedAgent').innerHTML = '<option value="">-- Choose an agent --</option>';
        return;
    }

    agents = agentList;

    // Build table rows
    const rows = agentList.map(agent => `
        <tr>
            <td class="agent-id" title="${agent.agent_id}">${truncateId(agent.agent_id)}</td>
            <td>${agent.user_id}</td>
            <td>
                <span class="status-badge status-${agent.status}">
                    ${agent.status.toUpperCase()}
                </span>
            </td>
            <td>${agent.execution_frequency}</td>
            <td>${agent.last_executed ? formatDate(agent.last_executed) : 'Never'}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn" onclick="viewAgent('${agent.agent_id}')">View</button>
                    <button class="action-btn" onclick="toggleAgentStatus('${agent.agent_id}', '${agent.status}')">
                        ${agent.status === 'active' ? 'Pause' : 'Resume'}
                    </button>
                    <button class="action-btn btn-danger" onclick="deleteAgent('${agent.agent_id}')">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');

    tbody.innerHTML = rows;

    // Update agent selector
    const agentSelect = document.getElementById('selectedAgent');
    agentSelect.innerHTML = '<option value="">-- Choose an agent --</option>' +
        agentList.map(agent => `<option value="${agent.agent_id}">${truncateId(agent.agent_id)} (${agent.user_id})</option>`).join('');
}

// Deploy new agent
async function handleDeployAgent(e) {
    e.preventDefault();

    const deployBtn = e.target.querySelector('button[type="submit"]');
    const agentCode = document.getElementById('agentCode').value.trim();
    const executionFrequency = parseInt(document.getElementById('executionFrequency').value);

    if (!agentCode || !executionFrequency) {
        showStatus('All fields are required', 'error');
        return;
    }

    try {
        // Show loading state
        deployBtn.disabled = true;
        const originalText = deployBtn.textContent;
        deployBtn.textContent = 'Deploying...';

        const response = await fetch(`${API_BASE}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_code: agentCode,
                execution_frequency: executionFrequency
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to deploy agent');
        }

        // Success
        showStatus(`✅ Agent deployed successfully! ID: ${truncateId(data.agent_id)}`, 'success');
        document.getElementById('deployForm').reset();

        // Reload agents after a short delay
        setTimeout(() => loadAgents(), 500);
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    } finally {
        // Restore button state
        deployBtn.disabled = false;
        deployBtn.textContent = originalText;
    }
}

// Load execution history
async function loadExecutionHistory() {
    const agentId = selectedAgentId || document.getElementById('selectedAgent').value;

    if (!agentId) {
        document.getElementById('historyList').innerHTML = `
            <tr>
                <td colspan="4" class="empty">Select an agent to view execution history</td>
            </tr>
        `;
        return;
    }

    selectedAgentId = agentId;

    try {
        showLoading('historyList', true);

        const response = await fetch(`${API_BASE}/agents/${agentId}`);
        if (!response.ok) {
            throw new Error('Failed to load execution history');
        }

        const data = await response.json();
        const executions = data.execution_history || [];

        if (executions.length === 0) {
            document.getElementById('historyList').innerHTML = `
                <tr>
                    <td colspan="4" class="empty">No executions yet</td>
                </tr>
            `;
            return;
        }

        const rows = executions.map(execution => {
            const isError = execution.error_message && execution.error_message.length > 0;
            return `
                <tr class="${isError ? 'error-row' : ''}">
                    <td>${formatDate(execution.executed_at)}</td>
                    <td>
                        <code>${truncateText(execution.result || 'N/A', 50)}</code>
                    </td>
                    <td>${execution.trade_executed ? '✅ Yes' : '❌ No'}</td>
                    <td ${isError ? 'title="' + (execution.error_message || '') + '"' : ''}>
                        ${execution.error_message ? '⚠️ ' + truncateText(execution.error_message, 40) : '--'}
                    </td>
                </tr>
            `;
        }).join('');

        document.getElementById('historyList').innerHTML = rows;
    } catch (error) {
        console.error('Error loading execution history:', error);
        document.getElementById('historyList').innerHTML = `
            <tr>
                <td colspan="4" class="loading">⚠️ Error loading execution history</td>
            </tr>
        `;
    }
}

// View agent details
function viewAgent(agentId) {
    document.getElementById('selectedAgent').value = agentId;
    loadExecutionHistory();
    document.querySelector('.history-section').scrollIntoView({ behavior: 'smooth' });
}

// Toggle agent status (Pause/Resume)
async function toggleAgentStatus(agentId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';

    if (!confirm(`${newStatus === 'paused' ? 'Pause' : 'Resume'} this agent?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/agents/${agentId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to update agent');
        }

        showStatus(`✅ Agent ${newStatus === 'paused' ? 'paused' : 'resumed'} successfully`, 'success');
        await loadAgents();
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Delete agent
async function deleteAgent(agentId) {
    if (!confirm('Are you sure you want to delete this agent? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/agents/${agentId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete agent');
        }

        showStatus('✅ Agent deleted successfully', 'success');

        // Clear selection if it was the deleted agent
        if (selectedAgentId === agentId) {
            selectedAgentId = null;
            document.getElementById('selectedAgent').value = '';
            document.getElementById('historyList').innerHTML = `
                <tr>
                    <td colspan="4" class="empty">Select an agent to view execution history</td>
                </tr>
            `;
        }

        await loadAgents();
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Refresh scheduler status
async function refreshSchedulerStatus() {
    try {
        const response = await fetch(`${API_BASE}/scheduler/status`);
        if (!response.ok) {
            throw new Error('Failed to load scheduler status');
        }

        const data = await response.json();

        document.getElementById('schedulerRunning').textContent = data.running ? '✅ Running' : '⛔ Stopped';
        document.getElementById('schedulerLastCheck').textContent = data.last_check
            ? formatDate(data.last_check)
            : 'Never';
        document.getElementById('schedulerExecuted').textContent = data.agents_executed_today || 0;
    } catch (error) {
        console.error('Error loading scheduler status:', error);
        document.getElementById('schedulerRunning').textContent = '⚠️ Error';
    }
}

// Show status message
function showStatus(message, type) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = `status-message show ${type}`;

    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusEl.classList.remove('show');
    }, 5000);
}

// Show loading indicator
function showLoading(elementId, show) {
    const element = document.getElementById(elementId);
    if (show && element.innerHTML.indexOf('Loading') === -1) {
        element.innerHTML = `
            <tr>
                <td colspan="100" class="loading">
                    <span class="spinner"></span> Loading...
                </td>
            </tr>
        `;
    }
}

// Handle logout
function handleLogout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('userId');
        window.location.reload();
    }
}

// Toggle advanced options (placeholder)
function toggleAdvanced() {
    alert('Advanced options coming soon!');
}

// Load API keys
async function loadApiKeys() {
    try {
        const response = await fetch(`${API_BASE}/api/keys`);
        if (!response.ok) {
            throw new Error('Failed to load API keys');
        }

        const keys = await response.json();
        displayApiKeys(keys);
    } catch (error) {
        console.error('Error loading API keys:', error);
        document.getElementById('apiKeysList').innerHTML = `
            <tr>
                <td colspan="5" class="loading">⚠️ Error loading API keys</td>
            </tr>
        `;
    }
}

// Display API keys in table
function displayApiKeys(keys) {
    const tbody = document.getElementById('apiKeysList');

    if (!keys || keys.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="loading">No API keys yet. Generate one to connect Claude or OpenAI.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = keys.map(key => `
        <tr>
            <td><code>${truncateText(key.api_key, 12)}</code></td>
            <td>${key.name || '--'}</td>
            <td>${key.created_at ? formatDate(key.created_at) : '--'}</td>
            <td>${key.last_used_at ? formatDate(key.last_used_at) : 'Never'}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn" onclick="copyApiKey('${key.api_key}')">Copy</button>
                    <button class="action-btn btn-danger" onclick="revokeApiKey('${key.api_key}')">Revoke</button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Generate a new API key
async function handleCreateApiKey() {
    try {
        const response = await fetch(`${API_BASE}/api/keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to create API key');
        }

        const resultEl = document.getElementById('apiKeyResult');
        resultEl.textContent = `✅ New API key created: ${data.api_key} (copy it now, shown only once here)`;
        resultEl.className = 'status-message show success';
        setTimeout(() => resultEl.classList.remove('show'), 15000);

        await loadApiKeys();
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Copy API key to clipboard
function copyApiKey(apiKey) {
    navigator.clipboard.writeText(apiKey).then(() => {
        showStatus('✅ API key copied to clipboard', 'success');
    }).catch(() => {
        showStatus('❌ Could not copy API key', 'error');
    });
}

// Revoke an API key
async function revokeApiKey(apiKey) {
    if (!confirm('Revoke this API key? Any integrations using it will stop working.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/keys/${apiKey}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to revoke API key');
        }

        showStatus('✅ API key revoked', 'success');
        await loadApiKeys();
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Utility functions
function truncateId(id) {
    return id.substring(0, 8) + '...';
}

function truncateText(text, length) {
    return text.length > length ? text.substring(0, length) + '...' : text;
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (error) {
        return dateString;
    }
}
