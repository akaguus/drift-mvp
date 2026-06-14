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
