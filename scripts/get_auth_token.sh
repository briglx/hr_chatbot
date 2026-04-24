#!/bin/bash

# Auth0 token endpoint
TOKEN_URL="https://${AUTH0_DOMAIN}/oauth/token"

echo "Requesting access token from Auth0..."
echo "Token URL: $TOKEN_URL"

# Make the POST request to get the token
response=$(curl --request POST  \
    --url "$TOKEN_URL" \
    --header 'content-type: application/json' \
    --data '{
      "client_id":"'"$AUTH0_CLIENT_ID"'",
      "client_secret":"'"$AUTH0_CLIENT_SECRET"'",
      "audience":"'"$AUTH0_AUDIENCE"'",
      "grant_type":"client_credentials"
    }')

# Extract the access token from the response
access_token=$(echo "$response" | jq -r '.access_token')

# Check if the token was successfully retrieved
if [ "$access_token" != "null" ] && [ -n "$access_token" ]; then
  echo "Access token retrieved successfully:"
  echo "$access_token"
else
  echo "Failed to retrieve access token. Response:"
  echo "$response"
fi