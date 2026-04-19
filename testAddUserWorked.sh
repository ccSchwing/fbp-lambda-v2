#!/bin/bash

aws dynamodb get-item \
  --table-name FBPUsers \
  --key '{"email":{"S":"test@example.com"}}' \
  --region us-east-1

