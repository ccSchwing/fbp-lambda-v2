from calendar import c
import json
from math import log
import os
from typing import Any
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.fbpLog import fbpLog
from fbplib import getCurrentWeek


'''
This function will update user picks to the FBP-Picks DynamoDB table 
for the given email address in the event.
'''

logger = logging.getLogger()
logger.info("Initializing SaveFBPPicksPython Lambda function")  # Log initialization message
logger.setLevel(logging.INFO)


cors_config = CORSConfig(
    allow_origin="*",  # Or specify your domain like "https://yourdomain.com"
    allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
    max_age=86400,  # Cache preflight for 24 hours
    allow_credentials=False
)

app=APIGatewayHttpResolver(cors=cors_config)

@app.post("/saveFBPPicks")
def saveFBPPicks():
    fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", "Saving FBP picks", "INFO")
   
    FBP_PICKS_TABLE_NAME = os.environ.get('FBPPicksTableName', 'FBP-Picks')
    logger.info(f"Using FBP Picks DynamoDB table: {FBP_PICKS_TABLE_NAME}")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(FBP_PICKS_TABLE_NAME)

    week=getCurrentWeek.getCurrentWeek()
    if week is None:
        fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", "Could not determine current week", "ERROR")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Could not determine current week'}),
        }
    logger.info(f"Saving picks for week: {week}")
    try:
        body = app.current_event.json_body
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        logger.info(f"Parsed JSON body: {body}")
        email = body.get('email')
        picks = body.get('picks')
        tieBreaker = body.get('tieBreaker')

        logger.info(f"Extracted email from API Gateway event: {email}")
        logger.info(f"Extracted picks from API Gateway event: {picks}")
        table.update_item(
            Key={'email': email}, 
            UpdateExpression="SET #picks = :p, #tieBreaker = :t",
            ExpressionAttributeNames={'#picks': 'picks', '#tieBreaker': 'tieBreaker'},
            ExpressionAttributeValues={':p': picks, ':t': tieBreaker}
        )

        logger.info(f"Successfully saved picks: {picks} and tieBreaker: {tieBreaker} for email: {email} and week: {week}")
        fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", f"Successfully saved picks: {picks} and tieBreaker: {tieBreaker} for email: {email} and week: {week}", "INFO")
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", f"DynamoDB Error: {e}", "ERROR")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'DynamoDB Error'}),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", f"Unexpected error: {e}", "ERROR")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Unexpected error'}),
        }
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Successfully saved picks: {picks} and tieBreaker: {tieBreaker} for week {week}'}),
    }



def lambda_handler(event, context):
    return app.resolve(event, context)  