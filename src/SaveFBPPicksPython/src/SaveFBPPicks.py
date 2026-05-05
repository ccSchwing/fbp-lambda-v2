from calendar import c
import json
from math import log
import os
import re
from typing import Any
import boto3
import logging
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response
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

pattern = re.compile(r'^[HA]*$')
def isValidPickString(s: str) -> bool:
    if s == "" or s is None:
        return False
    return bool(pattern.match(s))

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
            UpdateExpression="SET #picks = :p, #tieBreaker = :t, #week = :w",
            ExpressionAttributeNames={'#picks': 'picks', '#tieBreaker': 'tieBreaker', '#week': 'week'},
            ExpressionAttributeValues={':p': picks, ':t': tieBreaker, ':w': week}
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

@app.post("/validateAndFixFBPPicks")
def validateAndFixFBPPicks():
    fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", "Validating and fixing FBP picks", "INFO")
    FBP_USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
    FBP_PICKS_TABLE_NAME = os.environ.get('FBPPicksTableName', 'FBP-Picks')
    logger.info(f"Using FBP Picks DynamoDB table: {FBP_PICKS_TABLE_NAME}")
    dynamodb = boto3.resource('dynamodb')
    picksTable = dynamodb.Table(FBP_PICKS_TABLE_NAME)
    usersTable = dynamodb.Table(FBP_USERS_TABLE_NAME)

    week=getCurrentWeek.getCurrentWeek()
    if week is None:
        fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", "Could not determine current week", "ERROR")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Could not determine current week'}),
        }
    logger.info(f"Validating and fixing picks for week: {week}")
    try:
        body = app.current_event.json_body
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        logger.info(f"Parsed JSON body: {body}")
        email = body.get('email')
        if email is None:
            logger.error("Email is required in the request body")
            fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", "Email is required in the request body", "ERROR")
            return Response(
                status_code=400,
                body=json.dumps({'error': 'Email is required'})
            )
        okToProceed = True
        picks = body.get('picks')
        noPicks = False
        noTieBreaker = False

        if picks == "" or picks is None:
            noPicks = True
        tieBreaker = body.get('tieBreaker')
        # The tieBreaker is enforced in the UI, so if there is no tieBreaker,
        # the user made no picks.
        if tieBreaker is None:
            noTieBreaker = True
        # Check to see if user had already made picks for the week.  If they had, we will use those picks and only replace the missing picks with the algorithm.  If they had not made any picks, then we will apply the algorithm to all picks.
        existingPicksResponse = picksTable.get_item(Key={'email': email})
        if 'Item' in existingPicksResponse and existingPicksResponse['Item'].get('week') == week:
            existingPicks = existingPicksResponse['Item'].get('picks')
            existingTieBreaker = existingPicksResponse['Item'].get('tieBreaker')
            if existingPicks is not None:
                picks = existingPicks
                noPicks = True if picks == "" else False 
            if existingTieBreaker is not None:
                tieBreaker = existingTieBreaker
                noTieBreaker = False
        if isValidPickString(picks) and tieBreaker is not None:
            return Response(
                status_code=200,
                body=json.dumps({
                    'picks': picks,
                    'tieBreaker': tieBreaker
                })
            )

        # Now we can get the user and find out what algorithm they are using
        # This will capture the case where the user did not make any picks,
        # or the made SOME picks.  In the second case, the missing pick is
        # shown as a ? in the picks string.  We will replace the ? by applyin the alrorigthm
        # for the user.
        # if the user is using the default algorithm, or we will replace all picks with the default pick for that week if they are using the "pick the winner" algorithm
        userResponse = usersTable.get_item(Key={'email': email})
        if 'Item' not in userResponse:
            logger.error(f"User with email {email} not found in FBP-Users table")
            fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"User with email {email} not found in FBP-Users table", "ERROR")
            return Response(
                status_code=404,
                body=json.dumps({'error': 'User not found'})
            )
        user = userResponse['Item']
        algorithm = user.get('defaultAlgorithm')



        FBP_SCHEDULE_TABLE_NAME = os.environ.get('FBPScheduleTableName', '2025-Schedule')
        match algorithm:
            case "home":
                if noPicks:
                    picks = "H" * 17
                else:
                    # Replace all ? with H
                    picks = picks.replace("?", "H")
            case "away":
                if noPicks:
                    picks = "A" * 17
                else:
                    # Replace all ? with A
                    picks = picks.replace("?", "A")
            case "random":
                defaultPicks = []
                import random
                if noPicks:
                    for _ in range(17):
                        rNumber = random.uniform(0, 1)
                        if rNumber > 0.5:
                            defaultPicks += "H"
                        else:
                            defaultPicks += "A"
                    picks = "".join(defaultPicks)
                else:
                    # Replace all ? with a random pick
                    for i, c in enumerate(picks):
                        if c == "?":
                            rNumber = random.uniform(0, 1)
                            defaultPicks += (rNumber > 0.5 and "H" or "A")
                        else:
                            defaultPicks += c
                    picks = "".join(defaultPicks)
                    logger.info(f"Replaced ? with random picks: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Replaced ? with random picks: {picks}", "INFO")
            # For favorites and underdogs we need the schedule from 202X season to determine 
            # which team is the favorite and which is the underdog.
            # We will get the schedule from the DynamoDB table and then apply the
            # algorithm to replace the ? with the correct pick.
            case "favorites":
                scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
                # Underdog is defined in the DB as either H or A.
                # Favorite is NOT defined, so scan for it and invert it to get the favorite.
                response = scheduleTable.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('Week').eq(week)
                )
                schedule = response.get('Items', [])
                if not schedule: 
                    logger.error(f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table", "ERROR")
                    return Response(
                        status_code=500,
                        body=json.dumps({'error': 'No schedule items found'})
                    )
                if noPicks:
                    # For each game in the schedule, determine the favorite and set the pick
                    defaultPicks = []
                    for game in schedule:
                        gameObject = JSON.parse(game)
                        if gameObject.get('Underdog') == "H":
                            defaultPicks += "A"
                        elif gameObject.get('Underdog') == "A":
                            defaultPicks += "H"
                    picks = "".join(defaultPicks)
                    logger.info(f"Set picks to favorites: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Set picks to favorites: {picks}", "INFO") 
                else:
                    defaultPicks = []
                    # Replace all ? with the favorite
                    for i, c in enumerate(picks):
                        if c == "?":
                            # Find the game in the schedule
                            for game in schedule:
                                if game.get('Underdog') == "H":
                                    defaultPicks += "A"
                                elif game.get('Underdog') == "A":
                                    defaultPicks += "H"
                    picks = "".join(defaultPicks)
                    logger.info(f"Replaced ? with favorites picks: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Replaced ? with favorites picks: {picks}", "INFO")
            case "underdogs":
                scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
                # Underdog is defined in the DB as either H or A.
                response = scheduleTable.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('Week').eq(week)
                )
                schedule = response.get('Items', [])
                if not schedule:
                    logger.error(f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table", "ERROR")
                    return Response(
                        status_code=500,
                        body=json.dumps({'error': 'No schedule items found'})
                    )
                if noPicks:
                    defaultPicks = ""
                    for game in schedule:
                        if game.get('Underdog') == "H":
                            defaultPicks += "H"
                        elif game.get('Underdog') == "A":
                            defaultPicks += "A"
                    picks = defaultPicks
                    logger.info(f"Set picks to underdogs: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Set picks to underdogs: {picks}", "INFO")
                else:
                    defaultPicks = []
                    # Replace all ? with the underdog
                    for i, c in enumerate(picks):
                        if c == "?":
                            # Find the game in the schedule
                            for game in schedule:
                                if game.get('Underdog') == "H":
                                    defaultPicks += "H"
                                elif game.get('Underdog') == "A":
                                    defaultPicks += "A"
                    picks = "".join(defaultPicks)
                    logger.info(f"Replaced ? with underdog picks: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Replaced ? with underdog picks: {picks}", "INFO")                
                

        if noTieBreaker:
            tieBreaker = random.randint(2, 100)
        picksTable.update_item(
            Key={'email': email}, 
            UpdateExpression="SET #picks = :p, #tieBreaker = :t, #week = :w",
            ExpressionAttributeNames={'#picks': 'picks', '#tieBreaker': 'tieBreaker', '#week': 'week'},
            ExpressionAttributeValues={':p': picks, ':t': tieBreaker, ':w': week}
        )

        logger.info(f"Successfully validated and fixed picks: {picks} and tieBreaker: {tieBreaker} for email: {email} and week: {week}")
        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Successfully validated and fixed picks: {picks} and tieBreaker: {tieBreaker} for email: {email} and week: {week}", "INFO")
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"DynamoDB Error: {e}", "ERROR")
        return{
            'statusCode': 500,
            'body': json.dumps({'error': 'DynamoDB Error'}),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Unexpected error: {e}", "ERROR")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Unexpected error'}),
        }
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Successfully validated and fixed picks: {picks} and tieBreaker: {tieBreaker} for week {week}'}),
    }


def lambda_handler(event, context):
    return app.resolve(event, context)  