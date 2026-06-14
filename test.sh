#!/bin/bash

BASE_URL="http://localhost:5000"

echo "Testing POST /agents..."
RESPONSE=$(curl -s -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "agent_code": "print(\"Hello Agent\")",
    "execution_frequency": 60
  }')

echo "Response: $RESPONSE"
AGENT_ID=$(echo "$RESPONSE" | grep -o '"agent_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$AGENT_ID" ]; then
  echo "Failed to create agent"
  exit 1
fi

echo "Created agent with ID: $AGENT_ID"
echo ""

echo "Testing GET /agents/<agent_id>..."
curl -s -X GET "$BASE_URL/agents/$AGENT_ID" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "Testing missing required fields..."
curl -s -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user456"
  }' | python3 -m json.tool

echo ""
echo "Testing 404 for non-existent agent..."
curl -s -X GET "$BASE_URL/agents/nonexistent" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "Testing POST /api/claude-skill with valid deploy_agent action..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/claude-skill" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deploy_agent",
    "user_id": "claude_user_123",
    "agent_code": "if market_data[\"current_price\"] > 150:\n    print(\"Price above target\")",
    "execution_frequency": 30
  }')

echo "Response: $RESPONSE"
CLAUDE_AGENT_ID=$(echo "$RESPONSE" | grep -o '"agent_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$CLAUDE_AGENT_ID" ]; then
  echo "Failed to deploy agent via Claude skill"
  exit 1
fi

echo "Deployed agent via Claude skill with ID: $CLAUDE_AGENT_ID"
echo ""

echo "Testing Claude skill with empty agent_code..."
curl -s -X POST "$BASE_URL/api/claude-skill" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deploy_agent",
    "user_id": "claude_user_456",
    "agent_code": "",
    "execution_frequency": 60
  }' | python3 -m json.tool

echo ""
echo "Testing Claude skill with missing required fields..."
curl -s -X POST "$BASE_URL/api/claude-skill" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deploy_agent",
    "user_id": "claude_user_789"
  }' | python3 -m json.tool

echo ""
echo "Testing Claude skill with invalid action..."
curl -s -X POST "$BASE_URL/api/claude-skill" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "invalid_action",
    "user_id": "claude_user_999",
    "agent_code": "print(\"test\")",
    "execution_frequency": 60
  }' | python3 -m json.tool
