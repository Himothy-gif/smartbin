# SMART BIN LTD - API TEST COMMANDS
# Run these after starting the server

# 1. Health Check
curl http://localhost:3000/health

# 2. Login (get token)
TOKEN=$(curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartbin.co.ke","password":"admin123"}' | jq -r '.token')

echo "Token: $TOKEN"

# 3. Get Dashboard Stats
curl http://localhost:3000/api/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"

# 4. List Estates
curl http://localhost:3000/api/estates \
  -H "Authorization: Bearer $TOKEN"

# 5. Get Estate Detail (replace ID)
curl http://localhost:3000/api/estates/YOUR_ESTATE_ID \
  -H "Authorization: Bearer $TOKEN"

# 6. Create Estate
curl -X POST http://localhost:3000/api/estates \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"New Estate","location":"Nairobi","total_phases":2}'

# 7. List Houses in Phase
curl http://localhost:3000/api/houses/phase/YOUR_PHASE_ID \
  -H "Authorization: Bearer $TOKEN"

# 8. Lookup House by Account Number
curl http://localhost:3000/api/houses/account/348/4 \
  -H "Authorization: Bearer $TOKEN"

# 9. Create Bill
curl -X POST http://localhost:3000/api/bills \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"house_id":"YOUR_HOUSE_ID","amount":400,"bill_period":"Jan 2025","due_date":"2025-01-15","description":"Monthly fee"}'

# 10. Bulk Create Bills
curl -X POST http://localhost:3000/api/bills/bulk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"estate_id":"YOUR_ESTATE_ID","amount":400,"bill_period":"Jan 2025","due_date":"2025-01-15","description":"Monthly fee"}'

# 11. List Bills
curl http://localhost:3000/api/bills \
  -H "Authorization: Bearer $TOKEN"

# 12. Overdue Summary
curl http://localhost:3000/api/bills/summary/overdue \
  -H "Authorization: Bearer $TOKEN"

# 13. M-PESA Validation (simulated)
curl -X POST http://localhost:3000/api/payments/validate \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType":"Pay Bill",
    "TransID":"ABC123XYZ",
    "TransTime":"20240101120000",
    "TransAmount":"400",
    "BusinessShortCode":"4060083",
    "BillRefNumber":"348/4",
    "MSISDN":"254712345678",
    "FirstName":"Faith"
  }'

# 14. M-PESA Confirmation (simulated)
curl -X POST http://localhost:3000/api/payments/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType":"Pay Bill",
    "TransID":"ABC123XYZ",
    "TransTime":"20240101120000",
    "TransAmount":"400",
    "BusinessShortCode":"4060083",
    "BillRefNumber":"348/4",
    "MSISDN":"254712345678",
    "FirstName":"Faith"
  }'

# 15. Public Portal - Resident Statement (NO AUTH REQUIRED)
curl http://localhost:3000/api/portal/statement/348/4

# 16. Public Portal - Payment History
curl http://localhost:3000/api/portal/payments/348/4

# 17. List Drivers
curl http://localhost:3000/api/drivers \
  -H "Authorization: Bearer $TOKEN"

# 18. Revenue by Estate
curl http://localhost:3000/api/dashboard/revenue-by-estate \
  -H "Authorization: Bearer $TOKEN"

# 19. Collection Performance
curl http://localhost:3000/api/dashboard/collection-performance?days=30 \
  -H "Authorization: Bearer $TOKEN"

# 20. Overdue Aging Report
curl http://localhost:3000/api/dashboard/overdue-aging \
  -H "Authorization: Bearer $TOKEN"
