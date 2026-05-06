#!/bin/bash
aws lambda invoke \
    --function-name SMSSend \
    --payload '{"alert_type":"FBP-Test-Alert","phone_numbers":["+7325007427"]}' \
    response.json

