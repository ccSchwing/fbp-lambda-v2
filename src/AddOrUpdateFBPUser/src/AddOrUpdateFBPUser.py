import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from FBPLib.fbpLog import fbpLog


'''
This function will update the user information for the given email address in the event.
'''

logger = logging.getLogger()
logger.info("Initializing AddOrUpdateFBPUser Lambda function")  # Log initialization message
logger.setLevel(logging.INFO)

USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
logger.info(f"Using DynamoDB table: {USERS_TABLE_NAME}")  # Log the table name being used
fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", "Lambda function initialized", "INFO")

cors_config = CORSConfig(
    allow_origin="*",  # Or specify your domain like "https://yourdomain.com"
    allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
    max_age=86400,  # Cache preflight for 24 hours
    allow_credentials=False
)

app=APIGatewayHttpResolver(cors=cors_config)

#  THe function below is the main logic for the lambda function.
#  It will parse the email address from the event and then call
#  the updateFBPUserData function to update the user information in DynamoDB.
#  Finally, it will return the updated user information in the response.
@app.post("/updateFBPUser")
def updateFBPUser():
    logger.info("Handling updateFBPUser request")  # Log entry into the function
    try:
        logger.info(f"Raw event data: {json.dumps(app.current_event.raw_event, default=str)}")  # Log the raw event data
        request_body = app.current_event.json_body
        email = request_body.get('email') if request_body else None
        if not email:
            logger.warning("Email field is missing in the request body")
            fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", "Email field is missing in the request body", "ERROR")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Email address is required',
                    'message': 'Please provide email address in the event'
                })
            }
        logger.info(f"Extracted email from API Gateway event: {email}")
        logger.info(f"Request body: {request_body}")
        if not request_body:
            logger.error("No JSON body found in the request")
            fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", "No JSON body found in the request", "ERROR")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid request body',
                    'message': 'Request body seems to be empty or not valid JSON'
                })
            }

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"Unexpected error: {e}", "ERROR")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON with an email field'
            })
        }

    item = updateFBPUserData(request_body)
    
    if item:
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"Updated user data for email: {email}: request_body: {json.dumps(request_body, default=str)}", "INFO")
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
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"User not found: {email}", "ERROR")
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': f'User with email {email} not found',
                'email': email,
                })
            } 



@app.post("/addFBPUser")
def addFBPUser():
    logger.info("Handling addFFBPUser request")  # Log entry into the function
    try:
        logger.info(f"Raw event data: {json.dumps(app.current_event.raw_event, default=str)}")  # Log the raw event data
        request_body = app.current_event.json_body
        email = request_body.get('email') if request_body else None
        if not email:
            logger.warning("Email field is missing in the request body")
            fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", "Email field is missing in the request body", "ERROR")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Email address is required',
                    'message': 'Please provide email address in the event'
                })
            }
        logger.info(f"Extracted email from API Gateway event: {email}")
        logger.info(f"Request body: {request_body}")
        if not request_body:
            logger.error("No JSON body found in the request")
            fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", "No JSON body found in the request", "ERROR")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid request body',
                    'message': 'Request body seems to be empty or not valid JSON'
                })
            }

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"Unexpected error: {e}", "ERROR")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request body',
                'message': 'Request body must be valid JSON with an email field'
            })
        }

    item = addFBPUserData(request_body)
    
    if item:
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"Updated user data for email: {email}: request_body: {json.dumps(request_body, default=str)}", "INFO")
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
        fbpLog("fbpadmin@my-fbp.com", "AddOrUpdateFBPUser", f"User not found: {email}", "ERROR")
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': f'User with email {email} not found',
                'email': email,
                })
            } 



        

def updateFBPUserData(request_body):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(USERS_TABLE_NAME)
    try:
        response = table.update_item(
            Key={
                'email': request_body.get('email')
            },
            UpdateExpression=
                "SET defaultAlgorithm = :defaultAlgorithm, "
                "displayName = :displayName, "
                "emailGridSheet = :emailGridSheet, "
                "emailPickSheet = :emailPickSheet, "
                "emailReminders = :emailReminders, "
                "firstName = :firstName, "
                "lastName = :lastName, "
                "isAccountLocked = :isAccountLocked, "
                "isAdmin = :isAdmin, "
                "isPaidUser = :isPaidUser",
            ExpressionAttributeValues={
                ':defaultAlgorithm': request_body.get('defaultAlgorithm'),
                ':displayName': request_body.get('displayName'),
                ':emailGridSheet': bool(request_body.get('emailGridSheet')),
                ':emailPickSheet': bool(request_body.get('emailPickSheet')),
                ':emailReminders': bool(request_body.get('emailReminders')),
                ':firstName': request_body.get('firstName'),
                ':lastName': request_body.get('lastName'),
                ':isAccountLocked': bool(request_body.get('isAccountLocked')),
                ':isAdmin': bool(request_body.get('isAdmin')),
                ':isPaidUser': bool(request_body.get('isPaidUser'))
            },
        )
        return response
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "UpdateFBPUser", f"DynamoDB Error: {e}", "ERROR")
        return None
    except Exception as e:
        fbpLog("fbpadmin@my-fbp.com", "UpdateFBPUser", f"Unexpected error: {e}", "ERROR")
        logger.error(f"Unexpected error: {e}")
        return None


def addFBPUserData(request_body):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(USERS_TABLE_NAME)
    try:
        response = table.put_item(
            Item={
                'email': request_body.get('email'),
                'defaultAlgorithm': request_body.get('defaultAlgorithm'),
                'displayName': request_body.get('displayName'),
                'emailGridSheet': bool(request_body.get('emailGridSheet')),
                'emailPickSheet': bool(request_body.get('emailPickSheet')),
                'emailReminders': bool(request_body.get('emailReminders')),
                'firstName': request_body.get('firstName'),
                'lastName': request_body.get('lastName'),
                'isAccountLocked': bool(request_body.get('isAccountLocked')),
                'isAdmin': bool(request_body.get('isAdmin')),
                'isPaidUser': bool(request_body.get('isPaidUser'))
            }
        )
        return response
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "AddFBPUser", f"DynamoDB Error: {e}", "ERROR")
        return None
    except Exception as e:
        fbpLog("fbpadmin@my-fbp.com", "AddFBPUser", f"Unexpected error: {e}", "ERROR")
        logger.error(f"Unexpected error: {e}")
        return None


def lambda_handler(event, context):
    return app.resolve(event, context)