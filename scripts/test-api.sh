#!/bin/sh
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${TEST_USER_EMAIL:-apitest@inventory.com}"
PASSWORD="${TEST_USER_PASSWORD:-password123}"
NAME="${TEST_USER_NAME:-API Test User}"

echo "==> Health"
curl -sf "$BASE_URL/health" | grep -q ok

echo "==> Sign in (user must exist — create with: docker compose exec backend python /app/scripts/create_user.py ...)"
LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
STATUS=$(echo "$LOGIN" | tail -n1)
BODY=$(echo "$LOGIN" | sed '$d')
if [ "$STATUS" != "200" ]; then
  echo "Login failed ($STATUS). Create a user first:"
  echo "  docker compose exec backend python /app/scripts/create_user.py --name \"$NAME\" --email \"$EMAIL\" --password \"$PASSWORD\""
  exit 1
fi
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH_HEADER="Authorization: Bearer $TOKEN"

echo "==> Create product"
PRODUCT=$(curl -sf -X POST "$BASE_URL/products" \
  -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d '{"name":"Test Widget","sku":"TEST-SKU-'"$$"'","price":10.50,"quantity_in_stock":5}')
PRODUCT_ID=$(echo "$PRODUCT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "==> Create customer"
CUSTOMER=$(curl -sf -X POST "$BASE_URL/customers" \
  -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d '{"full_name":"Test Buyer","email":"buyer-'"$$"'@test.com","phone_number":"555-0001"}')
CUSTOMER_ID=$(echo "$CUSTOMER" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "==> Create order"
ORDER=$(curl -sf -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d "{\"customer_id\":$CUSTOMER_ID,\"items\":[{\"product_id\":$PRODUCT_ID,\"quantity\":2}]}")
echo "$ORDER" | python3 -c "import sys,json; assert json.load(sys.stdin)['total_amount']=='21.00'"

echo "==> Dashboard"
curl -sf "$BASE_URL/dashboard" -H "$AUTH_HEADER" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['total_products']>=1"

echo "==> Cleanup"
curl -sf -X DELETE "$BASE_URL/orders/$(echo "$ORDER" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")" -H "$AUTH_HEADER" -o /dev/null
curl -sf -X DELETE "$BASE_URL/products/$PRODUCT_ID" -H "$AUTH_HEADER" -o /dev/null
curl -sf -X DELETE "$BASE_URL/customers/$CUSTOMER_ID" -H "$AUTH_HEADER" -o /dev/null

echo "All API checks passed."
