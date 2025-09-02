#!/bin/bash

# Dhive AI Music Generator - Complete API Testing Script
# This script tests all available endpoints with curl commands

BASE_URL="http://127.0.0.1:5000"
echo "🚀 Testing Dhive AI Music Generator API"
echo "📍 Base URL: $BASE_URL"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to make curl request and check response
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    echo -e "\n${BLUE}🧪 Testing: $description${NC}"
    echo "Method: $method"
    echo "Endpoint: $endpoint"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_STATUS:/d')

    echo "Status Code: $http_status"
    echo "Response: $body"

    if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 300 ]; then
        print_status 0 "SUCCESS"
    else
        print_status 1 "FAILED"
    fi
}

echo -e "\n${YELLOW}📋 Testing Basic Endpoints${NC}"
echo "========================================"

# Test 1: Root endpoint
test_endpoint "GET" "/" "" "Root endpoint"

# Test 2: Health check
test_endpoint "GET" "/health" "" "Health check endpoint"

echo -e "\n${YELLOW}🎵 Testing Song Generation Endpoints${NC}"
echo "========================================"

# Test 3: Create song with full parameters
SONG_DATA='{
    "title": "Summer Vibes",
    "genre": "pop",
    "mood": "happy",
    "theme": "beach party",
    "style": "electronic"
}'

test_endpoint "POST" "/create_song" "$SONG_DATA" "Create song with full parameters"

# Test 4: Create instrumental song
INSTRUMENTAL_DATA='{
    "title": "Ambient Dreams",
    "genre": "ambient",
    "mood": "calm",
    "theme": "meditation",
    "style": "instrumental"
}'

test_endpoint "POST" "/create_song" "$INSTRUMENTAL_DATA" "Create instrumental song"

# Test 5: Create song with minimal parameters
MINIMAL_DATA='{
    "title": "Simple Tune",
    "genre": "rock"
}'

test_endpoint "POST" "/create_song" "$MINIMAL_DATA" "Create song with minimal parameters"

# Test 6: Check status (using a dummy task_id - this will likely fail but tests the endpoint)
echo -e "\n${BLUE}🧪 Testing: Check status endpoint${NC}"
echo "Method: GET"
echo "Endpoint: /check_status/dummy_task_id"
echo "Note: This will likely return 404 since we're using a dummy task ID"

response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$BASE_URL/check_status/dummy_task_id")
http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_STATUS:/d')

echo "Status Code: $http_status"
echo "Response: $body"

if [ "$http_status" = "404" ]; then
    print_status 0 "EXPECTED 404 for dummy task ID"
else
    print_status 1 "UNEXPECTED STATUS"
fi

echo -e "\n${YELLOW}📥 Testing Download Endpoint${NC}"
echo "========================================"

# Test 7: Download with invalid URL (should fail gracefully)
DOWNLOAD_DATA='{
    "audio_url": "https://example.com/invalid-audio.mp3"
}'

test_endpoint "POST" "/download" "$DOWNLOAD_DATA" "Download with invalid URL"

# Test 8: Download with missing audio_url (should return error)
MISSING_URL_DATA='{}'

test_endpoint "POST" "/download" "$MISSING_URL_DATA" "Download with missing audio_url"

echo -e "\n${YELLOW}🔧 Testing Error Handling${NC}"
echo "========================================"

# Test 9: Create song with invalid JSON
test_endpoint "POST" "/create_song" '{"invalid": json}' "Create song with invalid JSON"

# Test 10: Create song with empty body
test_endpoint "POST" "/create_song" "" "Create song with empty body"

echo -e "\n${GREEN}🎉 API Testing Complete!${NC}"
echo "========================================"
echo "📝 Summary:"
echo "• Basic endpoints: Root and Health check"
echo "• Song generation: Create song with various parameters"
echo "• Status checking: Check task status"
echo "• Download functionality: Download audio files"
echo "• Error handling: Invalid requests and edge cases"
echo ""
echo "💡 Note: For full testing, you may want to:"
echo "   1. Use a real task_id from a successful song creation"
echo "   2. Test the /receive_song endpoint with actual Suno callback data"
echo "   3. Test with real audio URLs for the download endpoint"
