#!/bin/bash

# Try forcing an update with rollback enabled
aws cloudformation update-stack \
  --stack-name fbp-lambda-v2 \
  --template-body file://min.yaml \
  --capabilities CAPABILITY_IAM \

