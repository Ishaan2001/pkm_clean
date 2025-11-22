TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpc2hhYW4yMDAxYXJvcmFAZ21haWwuY29tIiwiZXhwIjoxNzYzOTI2NTEzfQ.5xpxTG11iQwSkKBFtUJ5mhk3eT1ZG--A4xqOKqone7U"
curl -X GET http://localhost:8000/api/push/subscriptions -H "Authorization: Bearer $TOKEN"

 echo -e "\n\n=== Testing scheduler status ==="
 curl -X GET http://localhost:8000/api/push/scheduler/status -H "Authorization: Bearer $TOKEN"