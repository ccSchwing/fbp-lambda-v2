#!/bin/bash
echo "You need your config-id before you can run this."

exit 0

aws sms-voice describe-notify-templates \
    --notify-configuration-id your-config-id \
    --region us-east-1

