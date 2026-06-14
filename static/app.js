// API Base URL
const API_BASE = window.location.origin;

// State
let agents = [];
let selectedAgentId = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Set user ID from localStorage or generate a temporary one
    const userId = localStorage.getItem('userId') || 'user_' + Date.now();
    localStorage.setItem('userId', userId);
    document.getElementById('userId').textContent = userId;
    document.getElementById('deployUserId').value = userId;

    // Load initial data
    await loadAgents();
    await refreshSchedulerStatus();

    // Set up form submission
    document.getElementById('deployForm').addEventListener('submit', handleDeployAgent);

    // Auto-refresh every 30 seconds
    setInterval(async () => {
        await loadAgents();
        if (selectedAgentId) {
            await loadExecutionHistory();
        }
    }, 30000);
}

// Load all agents
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/agents`);
        if (!response.ok) {
            throw new Error('Failed to load agents');
        }

        // For now, we'll simulate getting all agents
        // In a real app, we'd have a GET /agents endpoint that returns all agents
        // For MVP, we'll just show the deployed agents from the form
        displayAgents([]);
    } catch (error) {
        console.error('Error loading agents:', error);
        document.getElementById('agentsList').innerHTML = `
            <tr>
                <td colspan="6" class="loading">Error loading agents. Try refreshing the page.</td>
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
            <td class="agent-id">${truncateId(agent.agent_id)}</td>
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
        agentList.map(agent => `<option value="${agent.agent_id}">${truncateId(agent.agent_id)}</option>`).join('');
}

// Deploy new agent
async function handleDeployAgent(e) {
    e.preventDefault();

    const userId = document.getElementById('deployUserId').value.trim();
    const agentCode = document.getElementById('agentCode').value.trim();
    const executionFrequency = parseInt(document.getElementById('executionFrequency').value);

    if (!userId || !agentCode || !executionFrequency) {
        showStatus('All fields are required', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                agent_code: agentCode,
                execution_frequency: executionFrequency
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to deploy agent');
        }

        // Success
        showStatus(`Agent deployed successfully! ID: ${truncateId(data.agent_id)}`, 'success');
        document.getElementById('deployForm').reset();
        document.getElementById('deployUserId').value = userId;

        // Reload agents after a short delay
        setTimeout(() => loadAgents(), 500);
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
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

        const rows = executions.map(execution => `
            <tr>
                <td>${formatDate(execution.executed_at)}</td>
                <td>${truncateText(execution.result || 'N/A', 50)}</td>
                <td>${execution.trade_executed ? '✓ Yes' : '✗ No'}</td>
                <td>${execution.error_message ? '⚠️ ' + truncateText(execution.error_message, 50) : '--'}</td>
            </tr>
        `).join('');

        document.getElementById('historyList').innerHTML = rows;
    } catch (error) {
        console.error('Error loading execution history:', error);
        document.getElementById('historyList').innerHTML = `
            <tr>
                <td colspan="4" class="loading">Error loading execution history</td>
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

// Toggle agent status
async function toggleAgentStatus(agentId, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    alert(`Toggle agent status to ${newStatus} - Coming soon!`);
    // TODO: Implement agent status toggle endpoint
}

// Delete agent
async function deleteAgent(agentId) {
    if (!confirm('Are you sure you want to delete this agent? This cannot be undone.')) {
        return;
    }

    alert('Delete agent - Coming soon!');
    // TODO: Implement agent deletion endpoint
}

// Refresh scheduler status
async function refreshSchedulerStatus() {
    try {
        const response = await fetch(`${API_BASE}/scheduler/status`);
        if (!response.ok) {
            throw new Error('Failed to load scheduler status');
        }

        const data = await response.json();

        document.getElementById('schedulerRunning').textContent = data.running ? '✓ Running' : '✗ Stopped';
        document.getElementById('schedulerLastCheck').textContent = data.last_check
            ? formatDate(data.last_check)
            : 'Never';
        document.getElementById('schedulerExecuted').textContent = data.agents_executed_today;
    } catch (error) {
        console.error('Error loading scheduler status:', error);
        document.getElementById('schedulerRunning').textContent = 'Error';
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
