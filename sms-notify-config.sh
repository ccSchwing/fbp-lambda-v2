#!/bin/bash
aws sms-voice create-notify-configuration \
    --display-name "YourApp Alerts" \
    --use-case CODE_VERIFICATION \
    --enabled-channels SMS \
    --region us-east-1
