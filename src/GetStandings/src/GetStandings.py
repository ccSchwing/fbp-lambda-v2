import os
import json
from decimal import Decimal
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.getCurrentWeek import getCurrentWeek
from fbplib.fbpLog import fbpLog


logger = logging.getLogger()
logger.info("Initializing GetStandings Lambda function")  # Log initialization message
logger.setLevel(level=logging.INFO)
logger.info("CORS configuration applied")

cors_config = CORSConfig(
    allow_origin="*",  # Or specify your domain like "https://yourdomain.com"
    allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
    max_age=86400,  # Cache preflight for 24 hours
    allow_credentials=False
)

app=APIGatewayHttpResolver(cors=cors_config)
@app.get("/getStandings")
def getStandings():
    """
    Lambda function to scan FBP-Users table and return year to date wins, losses and DisplayName
    """
    
    # Initialize DynamoDB resource
    logger.info("Connecting to DynamoDB table FBP-Config")
    dynamodb = boto3.resource('dynamodb')
    USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
    table = dynamodb.Table(USERS_TABLE_NAME)
    try:
        week_number = getCurrentWeek()
        if week_number is None:
            fbpLog("fbpadmin@my-fbp.com", "GetStandings", "Cannot determine week.", "ERROR")
            logger.error("Cannot determine week.")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Cannot determine current week.',
                    'message': 'Check logs for errors.',
                    'pool_open': False
                })
            }
        
        # Convert to integer if it's a string
        try:
            week_number = int(week_number)
        except (ValueError, TypeError):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid week number',
                    'message': 'Week must be a valid number',
                    'pool_open': False
                })
            }
        
        try:
            logger.info(f"Scanning DynamoDB table {USERS_TABLE_NAME} for current week {week_number}")# Query DynamoDB table
            response = table.scan(
                ProjectionExpression="displayName, totalCorrectPicks, totalIncorrectPicks"
            )
            logger.info(f"Retrieved data from DynamoDB: {response}")
            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('totalCorrectPicks', Decimal(0)), reverse=True)

            fbpLog("fbpadmin@my-fbp.com", "GetStandings", "Retrieved Standings","INFO")
            return {
                'statusCode': 200,
                'body': json.dumps({
                'week': week_number,
                'items': items
            })
            }
        except ClientError as e:
            fbpLog("fbpadmin@my-fbp.com", "GetStandings", f"Exception: {e}","ERROR")
            logger.error(f"DynamoDB Error: {e}")
            return {
               'statusCode': 500,
                'body': json.dumps({
                    'error': 'DynamoDB error',
                    'details': str(e)
                })
            } 
        except Exception as e:
            fbpLog("fbpadmin@my-fbp.com", "GetStandings", f"Exception: {e}","ERROR")
            logger.error(f"Unexpected error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': str(e)
                })
            }
        
    except ClientError as e:
        print(f"DynamoDB Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Database error',
                'details': str(e)
            })
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }

def lambda_handler(event, context):
    return app.resolve(event, context)