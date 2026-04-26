from ast import List
import json
import os
from typing import Any
from urllib import request
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.fbpLog import fbpLog


'''
This function will return all email addresses and displayname for the users in the FBP-Users DynamoDB table.
That data will be used by admin to view/modify profiles for users in the system.
This is GET with no parameters, it will return all users in the system with their email and display name.
'''

logger = logging.getLogger("SendEmail")
logger.info("Initializing SendEmail Lambda function")  # Log initialization message
logger.setLevel(logging.INFO)
logger.info("SendEmail Lambda function initialized successfully")  # Log successful initialization
logger.info("JUNK!!! Lambda function initialized successfully")  # Log successful initialization
logger.info("JUNK!!! Lambda function initialized successfully")  # Log successful initialization


# USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
# logger.info(f"Using DynamoDB table: {USERS_TABLE_NAME}")  # Log the table name being used
fbpLog("fbpadmin@my-fbp.com", "SendEmail", "Lambda function initialized", "INFO")

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
@app.post("/sendEmail")   # This is the endpoint for OPTIONS
def sendTemplatedEmail():
    logger.info("Handling sendTemplatedEmail request")  # Log entry into the function
    try:
        logger.info(f"Raw event data: {json.dumps(app.current_event.raw_event, default=str)}")  # Log the raw event data

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'exception occurred: {e}',
                'message': 'An unexpected error occurred while processing the request'
            })
        }
    # Get the request body and see what the request is for.
    body=app.current_event.json_body
    email=body.get('email')
    logger.info(f"the email is: {email}")
    if not email:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request type',
                'message': 'email address not present:  Please provide a valid request type (email, firstName, messageType)'
            })
        } 
    firstName=body.get('firstName')
    logger.info(f"the firstName is: {firstName}")
    if not firstName:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request type',
                'message': 'firstName not present:  Please provide a valid request type (email, firstName, messageType)'
            })
        }
    templateName=body.get('templateName')
    logger.info(f"the templateName is: {templateName}")
    if not templateName:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request type',
                'message': 'templateName not present:  Please provide a valid request type (email, firstName, messageType)'
            })
        }
    
    items= []
    match templateName:
        case "WelcomeEmailTemplate":
            logger.info("Processing request for grid sheet")
            fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Processing request for Welcome Email", "INFO")
            # Pass the dynamoDB attribute name you want to work with.
            items= sendEmailWithTemplate(email, firstName,templateName)
        case "picks":
            logger.info("Processing request for picks sheet")
            fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Processing request for picks sheet", "INFO")
            # Pass the dynamoDB attribute name you want to work with.
        case "gridSheet":
            logger.info("Processing request for reminders")
            fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Processing request for reminders", "INFO")
            # Pass the dynamoDB attribute name you want to work with.
        case "reminders":
            logger.info("Processing request for reminders")
            fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Processing request for reminders", "INFO")
            # Pass the dynamoDB attribute name you want to work with.
        case _:
            logger.error("Invalid request type")
            fbpLog("fbpadmin@my-fbp.com", "GetFBPUser", "Invalid request type", "ERROR")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid request type',
                    'message': 'Please provide a valid template name.'
                })
            }

    # If items is empty return it anyway    
    if items:
        logger.info(f"MessageIDs returned: {items}")  # Log the items being returned
        return {
            'statusCode': 200,
            'body': json.dumps({
                'items': items
                })
            }

        

def sendEmailWithTemplate(email, firstName, templateName):
    ses = boto3.client('ses', region_name='us-east-1')
    try:
        response = ses.send_templated_email(
            Source=email,
            Destination={
                'ToAddresses': [
                    email,
                ],
            },
            Template=templateName,
            TemplateData=json.dumps({'firstName': firstName})
        )
        return response
    except ClientError as e:
        logger.error(f"Simple Mail Service Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "sendEmail", f"Simple Mail Service Error: {e}", "ERROR")
        return None
    except Exception as e:
        fbpLog("fbpadmin@my-fbp.com", "sendEmail", f"Unexpected Simple Mail Service error: {e}", "ERROR")
        logger.error(f"Unexpected error: {e}")
        return None

def lambda_handler(event, context):
    return app.resolve(event, context)