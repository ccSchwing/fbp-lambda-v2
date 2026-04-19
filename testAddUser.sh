#!/bin/bash

echo '{
  "body": "{\"email\":\"test@example.com\",\"firstName\":\"TestUser\",\"lastName\":\"User\",\"displayName\":\"Test User\"}"
}' > test-payload.json

aws lambda invoke \
  --function-name new-fbp-AddFBPUser-r5Na8nWRUN4a \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-payload.json \
  response.json

