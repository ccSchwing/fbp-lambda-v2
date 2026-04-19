#!/bin/bash

# rm -rf .aws-sam/build/FBPLibLayer
echo sam build -t min.yaml --use-container --no-cached FBPLibLayer

lambdas="CalcWeeklyResultsPython GetWeeklyResultsPython SaveFBPPicksPython GetPickSheetPython GetPoolOpenEvent GetPoolConfig SetPoolStatusOpen SetPoolStatusClosed GetFBPUserPython UpdateFBPUserPython AddFBPUserPython GetFBPPicksPython GetAllFBPPicksPython"

IFS=' ' read -ra lambda <<< "$lambdas"
for i in "${lambda[@]}"; do
  echo "$i"
  sam build -t min.yaml --use-container --no-cached $i
done
sam deploy -t .aws-sam/build/template.yaml --stack-name fbp-lambda-v1-python --region us-east-1 --capabilities CAPABILITY_IAM  --s3-bucket=my-fbp.com-v2 --force-upload
exit $?
sam deploy -t .aws-sam/build/template.yaml --stack-name fbp-lambda-v2 --region us-east-1 --capabilities CAPABILITY_IAM --resolve-s3 --s3-prefix fbp-lambda-v2 --force-upload
