# Drift Agent Deployer Skill

## Overview
The **Drift Agent Deployer** is a Claude skill that enables users to deploy autonomous trading agents to the Drift cloud platform. Users can write agent code and configure execution frequency directly from Claude, and the skill handles deployment and scheduling.

## Skill Details
- **Name:** Drift Agent Deployer
- **Purpose:** Deploy agents to Drift cloud platform
- **Endpoint:** `POST /api/claude-skill`
- **Base URL:** `http://localhost:5000` (or your Drift instance URL)

## API Specification

### Request Format
```json
{
  "action": "deploy_agent",
  "user_id": "string (required) - User's unique identifier",
  "agent_code": "string (required) - Python code for the agent logic",
  "execution_frequency": "integer (required) - Minutes between executions"
}
```

### Example Request
```json
{
  "action": "deploy_agent",
  "user_id": "user123",
  "agent_code": "if market_data['current_price'] > 150:\n    print('Price above target')",
  "execution_frequency": 60
}
```

### Success Response (201 Created)
```json
{
  "success": true,
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "message": "Agent deployed successfully"
}
```

### Error Response (400/500)
```json
{
  "success": false,
  "error": "error message describing what went wrong"
}
```

## Validation Rules
- `user_id` must not be empty
- `agent_code` must not be empty
- `execution_frequency` must be a positive integer (minutes)
- Agent code is executed in a sandboxed environment with access to `market_data` only

## Usage in Claude

Users can deploy agents directly through Claude:

1. Write your agent code in Python
2. Specify the user ID and execution frequency
3. Ask Claude to deploy the agent using this skill
4. Claude will submit the deployment request and return the agent ID

### Example User Prompt
```
Deploy my trading agent to Drift. Here's the code:

if market_data['current_price'] < 150:
    print('Buy signal detected')

Schedule it to run every 60 minutes for user_id: myuser123
```

## Agent Code Sandbox

Agent code runs in a restricted environment with access to:
- `market_data`: Dictionary containing:
  - `current_price`: float - Current market price
  - `volume`: integer - Current volume
  - `timestamp`: string - ISO timestamp

Agent code cannot:
- Import modules
- Access the file system
- Access the network
- Access any other Python builtins besides basic operations

## Agent Lifecycle

1. **Deployment:** Agent created and stored in database with status='active'
2. **Scheduling:** Agent automatically added to scheduler queue
3. **Execution:** Agent code runs within market hours (9:30 AM - 4:00 PM Eastern)
4. **Monitoring:** Execution history and results tracked in Drift dashboard

## Error Handling

- Missing required fields → 400 Bad Request
- Database errors → 500 Internal Server Error
- Invalid action → 400 Bad Request
- Empty agent_code → 400 Bad Request

All errors include a descriptive message in the `error` field.
