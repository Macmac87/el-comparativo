#!/bin/bash

# El Comparativo - Post-Deploy Test Script
# Verifica que todo esté funcionando en producción

# Configuración
API_URL="${1:-https://el-comparativo-api.onrender.com}"

echo "🧪 El Comparativo - Post-Deploy Tests"
echo "======================================"
echo "API URL: $API_URL"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check..."
HEALTH=$(curl -s "$API_URL/health")
if echo "$HEALTH" | grep -q "ok"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "Response: $HEALTH"
fi
echo ""

# Test 2: API Docs
echo "Test 2: API Documentation..."
DOCS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
if [ "$DOCS" = "200" ]; then
    echo "✅ API docs accessible"
else
    echo "❌ API docs not accessible (HTTP $DOCS)"
fi
echo ""

# Test 3: Register User
echo "Test 3: User Registration..."
REGISTER=$(curl -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@elcomparativo.ve",
    "password": "TestPassword123",
    "full_name": "Test User"
  }')

if echo "$REGISTER" | grep -q "access_token"; then
    echo "✅ User registration successful"
    ACCESS_TOKEN=$(echo "$REGISTER" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "   Access token obtained: ${ACCESS_TOKEN:0:20}..."
else
    echo "⚠️  User registration failed (might already exist)"
    echo ""
    echo "Test 3b: Login with existing user..."
    LOGIN=$(curl -s -X POST "$API_URL/api/auth/login" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "test@elcomparativo.ve",
        "password": "TestPassword123"
      }')
    
    if echo "$LOGIN" | grep -q "access_token"; then
        echo "✅ Login successful"
        ACCESS_TOKEN=$(echo "$LOGIN" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        echo "   Access token obtained: ${ACCESS_TOKEN:0:20}..."
    else
        echo "❌ Login failed"
        echo "Response: $LOGIN"
    fi
fi
echo ""

# Test 4: Get Current User
if [ ! -z "$ACCESS_TOKEN" ]; then
    echo "Test 4: Get Current User..."
    USER=$(curl -s "$API_URL/api/auth/me" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    if echo "$USER" | grep -q "email"; then
        echo "✅ User profile accessible"
    else
        echo "❌ User profile not accessible"
        echo "Response: $USER"
    fi
    echo ""
    
    # Test 5: Search (Conversational)
    echo "Test 5: RAG Search..."
    SEARCH=$(curl -s -X POST "$API_URL/api/search/conversational" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "Toyota 4Runner",
        "limit": 5
      }')
    
    if echo "$SEARCH" | grep -q "vehicles"; then
        VEHICLE_COUNT=$(echo "$SEARCH" | grep -o '"total_results":[0-9]*' | cut -d':' -f2)
        echo "✅ Search successful"
        echo "   Found $VEHICLE_COUNT vehicles"
    else
        echo "❌ Search failed"
        echo "Response: $SEARCH"
    fi
else
    echo "⚠️  Skipping authenticated tests (no access token)"
fi
echo ""

# Test 6: Brands Endpoint
echo "Test 6: Get Brands..."
BRANDS=$(curl -s "$API_URL/api/brands")
if echo "$BRANDS" | grep -q "brand"; then
    BRAND_COUNT=$(echo "$BRANDS" | grep -o '"brand"' | wc -l)
    echo "✅ Brands endpoint working"
    echo "   Total brands: $BRAND_COUNT"
else
    echo "❌ Brands endpoint failed"
    echo "Response: $BRANDS"
fi
echo ""

# Test 7: Stats
echo "Test 7: Platform Stats..."
STATS=$(curl -s "$API_URL/api/stats")
if echo "$STATS" | grep -q "total_vehicles"; then
    TOTAL=$(echo "$STATS" | grep -o '"total_vehicles":[0-9]*' | cut -d':' -f2)
    echo "✅ Stats endpoint working"
    echo "   Total vehicles in database: $TOTAL"
else
    echo "❌ Stats endpoint failed"
    echo "Response: $STATS"
fi
echo ""

# Summary
echo "======================================"
echo "✅ Test Suite Complete"
echo ""
echo "Next steps:"
echo "1. Check Render dashboard for logs"
echo "2. Verify scrapers completed successfully"
echo "3. Test API at: $API_URL/docs"
echo ""
echo "API is live at: $API_URL"
echo "======================================"
