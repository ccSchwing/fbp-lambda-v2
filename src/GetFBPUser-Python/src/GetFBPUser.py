import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.fbpLog import fbpLog


'''
This function will return the user information for the given email address in the event.
'''

logger = logging.getLogger("GetFBPUser")
logger.info("Initializing GetFBPUser Lambda function")  # Log initialization message
logger.setLevel(logging.INFO)

USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
logger.info(f"Using DynamoDB table: {USERS_TABLE_NAME}")  # Log the table name being used
fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Lambda function initialized", "INFO")

cors_config = CORSConfig(
    allow_origin="*",  # Or specify your domain like "https://yourdomain.com"
    allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
    max_age=86400,  # Cache preflight for 24 hours
    allow_credentials=False
)

app=APIGatewayHttpResolver(cors=cors_config)

#  THe function below is the main logic for the lambda function.
#  It will parse the email address from the event and then call
#  the getFBPUserData function to get the user information from DynamoDB.
#  Finally, it will return the user information in the response.
@app.post("/getFBPUserPython")
def getFBPUser():
    logger.info("Handling getFBPUser request")  # Log entry into the function
    try:
        logger.info(f"Raw event data: {json.dumps(app.current_event.raw_event, default=str)}")  # Log the raw event data
        request_body = app.current_event.json_body
        logger.info(f"Request body: {request_body}")
        if not request_body:
            logger.error("No JSON body found in the request")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid request body',
                    'message': 'Request body seems to be empty or not valid JSON'
                })
            }
        email = request_body.get('email')
        logger.info(f"Extracted email from API Gateway event: {email}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON with an email field'
            })
        }

    if not email:   
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Email address is required',
                'message': 'Please provide email address in the event'
            })
        }
    item = getFBPUserData(email)
    
    if item:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'email': item.get('email'),
                'defaultAlgorithm': item.get('defaultAlgorithm'),
                'displayName': item.get('displayName'),
                'emailGridSheet': item.get('emailGridSheet'),
                'emailPickSheet': item.get('emailPickSheet'),
                'emailReminders': item.get('emailReminders'),
                'firstName': item.get('firstName'),
                'lastName': item.get('lastName'),
                'isAccountLocked': item.get('isAccountLocked'),
                'isAdmin': item.get('isAdmin'),
                'isPaidUser': item.get('isPaidUser'),
                })
            }
    else:
        logger.info(f"User not found: {email}")
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': f'User with email {email} not found',
                'email': email,
                'name': None,
                'team': None
                })
            } 

        

def getFBPUserData(emailAddress):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(USERS_TABLE_NAME)
    try:
        response = table.get_item(
            Key={'email': emailAddress}
        )
        item = response['Item'] if 'Item' in response else None
        logger.info(f"Fetched user from DynamoDB: {json.dumps(item, default=str) if item else 'None'}")
        return item
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", f"DynamoDB Error: {e}", "ERROR")
        return None
    except Exception as e:
        fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", f"Unexpected error: {e}", "ERROR")
        logger.error(f"Unexpected error: {e}")
        return None

def lambda_handler(event, context):
    return app.resolve(event, context)