#!/bin/bash

# Create the bucket
aws s3 mb s3://fbp-sam-deploy-768286545465

# Enable static website hosting
aws s3 website s3://fbp-sam-deploy-768286545465 \
  --index-document signup.html \
  --error-document error.html

# Allow public access (required for static websites)
aws s3api delete-public-access-block \
  --bucket fbp-sam-deploy-768286545465

# Set bucket policy for public read access
aws s3api put-bucket-policy \
  --bucket fbp-sam-deploy-768286545465 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::fbp-sam-deploy-768286545465/*"
      }
    ]
  }'

