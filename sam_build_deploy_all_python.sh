#!/bin/bash

set -e

# Clean FBPLibLayer build output
rm -rf .aws-sam/build/FBPLibLayer

# Build FBPLibLayer first
sam build -t min.yaml --use-container --no-cached FBPLibLayer

# List of all Python Lambda resources
PY_LAMBDAS=(
  CalcWeeklyResultsPython
  GetWeeklyResultsPython
  SaveFBPPicksPython
  GetPickSheetPython
  GetPoolOpenEvent
  GetPoolConfig
  SetPoolStatusOpen
  SetPoolStatusClosed
  GetFBPUserPython
  UpdateFBPUserPython
  AddFBPUserPython
  GetFBPPicksPython
  GetAllFBPPicksPython
)

# Build each Lambda individually
for LAMBDA in "${PY_LAMBDAS[@]}"; do
  echo "Building $LAMBDA..."
  sam build -t min.yaml --no-cached "$LAMBDA"
done
echo "Deploying stack..."
sam deploy -t .aws-sam/build/template.yaml --stack-name fbp-lambda-v2 --region us-east-1 --capabilities CAPABILITY_IAM --resolve-s3 --s3-prefix fbp-lambda-v2 --force-upload
