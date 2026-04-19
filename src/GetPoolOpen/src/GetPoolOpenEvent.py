import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """
    Lambda function to retrieve poolOpen Boolean value from FBP-Config table
    Week number is passed via the event
    """
    
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('FBP-Config')
    try:
        if(event.get('queryStringParameters') and event['queryStringParameters'].get('week')):
            week_number = event['queryStringParameters'].get('week')
        elif event.get('week'):
            week_number = event.get('week')
        
        if week_number is None:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Week number is required',
                    'message': 'Please provide week number in the event'
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
                    'message': 'Week must be a valid number'
                })
            }
        
        # Query DynamoDB table
        response = table.get_item(
            Key={
                'Week': week_number
            }
        )
        
        # Check if item exists and return poolOpen value
        if 'Item' in response:
            pool_open = response['Item'].get('poolOpen', False)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'week': week_number,
                    'poolOpen': pool_open
                })
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'Configuration for week {week_number} not found',
                    'week': week_number,
                    'poolOpen': False
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
