# Drift Agent Deployer - OpenAI Plugin

## Overview
The **Drift Agent Deployer** OpenAI plugin enables ChatGPT users to deploy autonomous trading agents directly from conversation. Users can describe their trading strategy, and the plugin handles deployment to the Drift platform.

## Installation

### For OpenAI Plugin Store (Future)
1. Visit OpenAI Plugin Store
2. Search for "Drift Agent Deployer"
3. Click "Install"
4. Authorize access to your Drift account

### Manual Installation (For Testing/Development)

#### Step 1: Prepare Your Drift Server
Ensure your Drift server is running and accessible at a public URL or localhost:5000 for development.

#### Step 2: Add Plugin to ChatGPT
1. Open ChatGPT (requires ChatGPT Plus or API access to plugins)
2. Go to **Plugins → Plugin Store**
3. Click **"Develop your own plugin"**
4. Enter your plugin manifest URL: `http://localhost:5000/ai-plugin.json` (or your server's URL)
5. Click **Install**

#### Step 3: Start Using
Begin a new conversation and mention "Drift" or ask to deploy agents.

## Usage

### Basic Example
**You:** "Deploy a trading agent that buys when the price drops below 150. Run it every 60 minutes for user ID 'trader_001'."

**ChatGPT:** *Uses the plugin to deploy your agent and returns the agent ID.*

### Advanced Example
**You:** 
```
Here's my trading strategy:
- If price > 155, execute sell
- If price < 145, execute buy
- Check market every 30 minutes

Deploy this for user: alice@example.com
```

**ChatGPT:** *Deploys the agent and provides monitoring instructions.*

## API Specification

### Endpoint
```
POST /api/openai-plugin
```

### Request Format
```json
{
  "action": "deploy_agent",
  "user_id": "string",
  "agent_code": "python_code_as_string",
  "execution_frequency": 60
}
```

### Response Format

**Success (201 Created):**
```json
{
  "success": true,
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "message": "Agent deployed to Drift"
}
```

**Error (400/500):**
```json
{
  "success": false,
  "error": "error description"
}
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be `"deploy_agent"` |
| `user_id` | string | Yes | User's unique identifier |
| `agent_code` | string | Yes | Python code for agent logic (cannot be empty) |
| `execution_frequency` | integer | Yes | Minutes between executions (1-1440) |

## Agent Code Examples

### Simple Price Alert
```python
if market_data['current_price'] > 150:
    print('Price above threshold - sell signal')
```

### Volume-Based Strategy
```python
if market_data['volume'] > 500000:
    print('High volume detected - buy signal')
```

### Time-Based Logic
```python
import datetime
hour = datetime.datetime.now().hour
if 14 <= hour <= 15:
    print('Market close approaching - exit positions')
```

## Agent Code Sandbox

Your code runs in a restricted environment with:
- **Available:** `market_data` dictionary with current price, volume, and timestamp
- **Unavailable:** File system, network, imports (except basic Python operations)
- **Execution:** Only during market hours (9:30 AM - 4:00 PM Eastern Time)

## Authentication

For the MVP version, no authentication is required. In production:
- API key authentication will be added
- Users will authorize plugin access through OpenAI's OAuth flow
- API keys should be generated in the Drift dashboard

## Monitoring & Management

After deployment, monitor your agents:
1. Visit your Drift dashboard
2. View agent execution history
3. Check results and error logs
4. Pause/resume agents as needed

## Troubleshooting

### "Agent deployment failed"
- Check that `agent_code` is valid Python
- Ensure `user_id` is not empty
- Verify `execution_frequency` is a positive number

### "Invalid action"
- Only `deploy_agent` action is supported
- Ensure your request includes the correct action field

### "Agent code error during execution"
- Your code ran into a runtime error
- Check the execution history for error details
- Agents run in a sandbox with limited capabilities

## Rate Limiting

- 100 agent deployments per hour per user
- 1000 total agent executions per day
- Contact support for higher limits

## Support

- **Documentation:** https://drift.example.com/docs
- **Support Email:** support@drift.example.com
- **Status Page:** https://status.drift.example.com
