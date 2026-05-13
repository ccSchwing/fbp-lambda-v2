from calendar import c
import json
from math import log
import random
import os
import re
from typing import Any
import boto3
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.decimalDefault import decimal_default
from fbplib.fbpLog import fbpLog
from fbplib.getCurrentWeek import getCurrentWeek


'''
This function will update user picks to the FBP-Picks DynamoDB table 
for the given email address in the event.
'''
logging.basicConfig(format='%(levelname)s %(message)s')
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

    week=getCurrentWeek()
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
        fbpLog(email, "SaveFBPPicksPython", f"Successfully saved picks: {picks} and tieBreaker: {tieBreaker} for week {week}", "INFO")
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

    week=getCurrentWeek()
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
            fbpLog("fbpadmin@my-fbp.com", "SaveFBPPicksPython", "Request body must be a JSON object", "ERROR")
            logger.error("Request body must be a JSON object")
            raise ValueError("Request body must be a JSON object")
        logger.info(f"Parsed JSON body: {body}")
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
            # Get default tieBreaker from DB for the user.
            response = usersTable.get_item(Key={'email': email})
            if 'Item' not in response:
                logger.error(f"User with email {email} not found in FBP-Users table")
                fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"User with email {email} not found in FBP-Users table: Continuing.", level="WARNING")
            else:
                user = response['Item']
                defaultTieBreaker = user.get('defaultTieBreaker')
                if defaultTieBreaker is not None:
                    tieBreaker = defaultTieBreaker
                    noTieBreaker = False
                    logger.info(f"Using default tieBreaker from DB for user {email}: {tieBreaker}")
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Using default tieBreaker from DB for user {email}: {tieBreaker}", level="INFO")
                else:
                    logger.warning(f"No default tieBreaker found in DB for user {email}")
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"No default tieBreaker found in DB for user {email}", level="WARNING")
                    # set tieBreaker to a random number between 21 and 49
                    tieBreaker = random.randint(a=21, b=49)
                    noTieBreaker = False
                    logger.info(f"Set tieBreaker to random number: {tieBreaker}")
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Set tieBreaker to random number: {tieBreaker}", level="INFO")
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
        if isValidPickString(str(picks)) and tieBreaker is not None:
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
        # need to query the schedule table for the week so that I can get the number
        # of games for that week and use it as a limit for the picks string.
        scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
        response = scheduleTable.scan(
            FilterExpression=Attr('Week').eq(week)
        )
        schedule = response.get('Items', [])
        if not schedule:
            logger.error(f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table for week {week}")
            fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"No schedule items found in {FBP_SCHEDULE_TABLE_NAME} table for week {week}", "ERROR")
            return Response(
                status_code=500,
                body=json.dumps({'error': 'No schedule items found'})
            )
        numberOfGames = len(schedule)
        match algorithm:
            case "home":
                if noPicks:
                    picks = "H" * numberOfGames
                else:
                    # Replace all ? with H
                    picks = str(picks).replace("?", "H")
            case "away":
                if noPicks:
                    picks = "A" * numberOfGames
                else:
                    # Replace all ? with A
                    picks = str(picks).replace("?", "A")
            case "random":
                defaultPicks = []
                if noPicks:
                    for _ in range(numberOfGames):
                        rNumber = random.uniform(0, 1)
                        if rNumber > 0.5:
                            defaultPicks += "H"
                        else:
                            defaultPicks += "A"
                    picks = "".join(defaultPicks)
                else:
                    # Replace all ? with a random pick
                    for i, c in enumerate(str(picks)):
                        if c == "?":
                            rNumber = random.uniform(0, 1)
                            defaultPicks += (rNumber > 0.5 and "H" or "A")
                        else:
                            defaultPicks += c
                    picks = "".join(defaultPicks)
                    logger.info(f"Replaced ? with random picks: {picks}")
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Replaced ? with random picks: {picks}", level="INFO")
            # For favorites and underdogs we need the schedule from 202X season to determine 
            # which team is the favorite and which is the underdog.
            # We will get the schedule from the DynamoDB table and then apply the
            # algorithm to replace the ? with the correct pick.
            case "favorites":
                scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
                # Underdog is defined in the DB as either H or A.
                # Favorite is NOT defined, so scan for it and invert it to get the favorite.
                response = scheduleTable.scan(
                FilterExpression=Attr('Week').eq(week)
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
                        if game.get('Underdog') == "H":
                            defaultPicks += "A"
                        elif game.get('Underdog') == "A":
                            defaultPicks += "H"
                    picks = "".join(defaultPicks)
                    logger.info(f"Set picks to favorites: {picks}")
                    fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Set picks to favorites: {picks}", "INFO") 
                else:
                    defaultPicks = []
                    # Replace all ? with the favorite
                    for i, c in enumerate(str(picks)):
                        if c == "?":
                            # Find the game in the schedule
                            for game in schedule:
                                if game.get('Underdog') == "H":
                                    defaultPicks += "A"
                                elif game.get('Underdog') == "A":
                                    defaultPicks += "H"
                    picks = "".join(defaultPicks)
                    logger.info(f"Replaced ? with favorites picks: {picks}")
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Replaced ? with favorites picks: {picks}", level="INFO")
            case "underdogs":
                scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
                # Underdog is defined in the DB as either H or A.
                response = scheduleTable.scan(
                FilterExpression=Attr('Week').eq(week)
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
                    fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Set picks to underdogs: {picks}", level="INFO")
                else:
                    defaultPicks = []
                    # Replace all ? with the underdog
                    for i, c in enumerate(str(picks)):
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
            tieBreaker = random.randint(a=21, b=49)
            fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Set tieBreaker to random number: {tieBreaker}", level="INFO")
        picksTable.update_item(
            Key={'email': email}, 
            UpdateExpression="SET #picks = :p, #tieBreaker = :t, #week = :w",
            ExpressionAttributeNames={'#picks': 'picks', '#tieBreaker': 'tieBreaker', '#week': 'week'},
            ExpressionAttributeValues={':p': picks, ':t': tieBreaker, ':w': week}
        )

        logger.info(f"Successfully validated and fixed picks: {picks} and tieBreaker: {tieBreaker} for email: {email} and week: {week}")
        fbpLog(email=email, action="method: validateAndFixFBPPicks", details=f"Successfully validated and fixed picks: {picks} and tieBreaker: {tieBreaker} for week {week}", level="INFO")
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog(email="fbpadmin@my-fbp.com", action="method: validateAndFixFBPPicks", details=f"DynamoDB Error: {e}", level="ERROR")
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
    #
    # Now that we've validated and fixed all of the picks, let's see if we have a tie
    # on the number of correct picks.  If so, we need to check against the Monday Night tieBreaker
    # to determin the winner.  If there is still a tie, I think I'll give each player 1/2 of a win.
    #
    try:
        # First, get all picks for the week from the FBP_PICKS_TABLE
        # and put them in a list of dictionaries with the email and picks
        # and tieBreaker fields.
        response = picksTable.scan(
            FilterExpression=Attr('week').eq(week)
        )
        picksList = response.get('Items', [])
        # Now, for each pick in the list, calculate the number of correct picks
        # and store it in the picks dictionary.
        for pick in picksList:
            email = pick['email']
            userPicks = pick['picks']
            correctPicks = 0
            # Get the schedule for the week
            response = scheduleTable.scan(
                FilterExpression=Attr('Week').eq(week)
            )
            schedule = response.get('Items', [])
            # For each game in the schedule, compare the user's pick to the actual result
            # and increment the correctPicks counter if the pick is correct.
            for i, game in enumerate(schedule):
                if i < len(str(userPicks)):
                    userPick = str(userPicks)[i]
                    if userPick == game['Winner']:
                        correctPicks += 1
            # Update the picks dictionary with the correct picks
            pick['correctPicks'] = correctPicks
        # Now, sort the picks list by correct picks in descending order

        picksList.sort(key=lambda x: decimal_default(x['correctPicks']), reverse=True)
        # Now, check if the top two picks have the same number of correct picks
        # If so, check the tieBreaker value for each and see who has the higher value
        # If there is still a tie, we'll give each player 1/2 of a win.
        if picksList[0]['correctPicks'] == picksList[1]['correctPicks']:
            # There is a tie, so check the tieBreaker values
            # The player with the higher tieBreaker value wins
            # If there is still a tie, we'll give each player 1/2 of a win.
            user1wins=decimal_default(picksList[0]['tieBreaker'])
            user2wins=decimal_default(picksList[1]['tieBreaker'])
            if user1wins > user2wins:
                # Player 1 wins
                picksTable.update_item(
                    Key={'email': picksList[0]['email']},
                    UpdateExpression="SET #Winner = :w",
                    ExpressionAttributeNames={'#Winner': 'Winner'},
                    ExpressionAttributeValues={':w': True} 
                )
                logger.info(f"Player {picksList[0]['email']} wins outright with {user1wins}.")
                fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Player {picksList[0]['email']} wins outright with {user1wins}.", "INFO")
            if user1wins == user2wins:
                # Use the tieBreaker to tell who won.  If there is still a tie, give each player 1/2 of a win.
                user1tieBreaker = decimal_default(picksList[0]['tieBreaker'])
                user2tieBreaker = decimal_default(picksList[1]['tieBreaker'])
                # Now get the total points from the monday night game.
                # Get the max of the gameId value.  Format: 01-XXX
                gamePrefix = ""
                gameIdNumber = 0
                gameId = ""
                for game in schedule:
                    gameId = str(game['gameId'])
                    gamePrefix = (gameId.split("-")[0])
                    gameIdNumber = str(gameId.split("-")[1])
                # when you get here, you should have the gameId for the Monday night game.
                # You can use this to get the tieBreaker result from the schedule table and then determine the winner.
                mondayNightGame=scheduleTable.query(
                        KeyConditionExpression=Key('gameId').eq(gameId)
                )   
                mondayNightTotalPoints = decimal_default(mondayNightGame['Items'][0].get('AwayScore', 0)) + decimal_default(mondayNightGame['Items'][0].get('HomeScore', 0))
                if user1tieBreaker == user2tieBreaker:
                    if user1tieBreaker == mondayNightTotalPoints:
                        # It's a tie, give each player 1/2 of a win
                        picksTable.update_item(
                            Key={'email': picksList[0]['email']},
                            UpdateExpression="SET #Winner = :w",
                            ExpressionAttributeNames={'#Winner': 'Winner'},
                            ExpressionAttributeValues={':w': True} 
                        )
                        picksTable.update_item(
                            Key={'email': picksList[1]['email']},
                            UpdateExpression="SET #Winner = :w",
                            ExpressionAttributeNames={'#Winner': 'Winner'},
                            ExpressionAttributeValues={':w': True} 
                        )
                        logger.info(f"Players {picksList[0]['email']} and {picksList[1]['email']} tie with {user1tieBreaker} and Monday night total points of {mondayNightTotalPoints}.")
                        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Players {picksList[0]['email']} and {picksList[1]['email']} tie with {user1tieBreaker} and Monday night total points of {mondayNightTotalPoints}.", "INFO")
                    elif abs(user1tieBreaker - mondayNightTotalPoints) < abs(user2tieBreaker - mondayNightTotalPoints):
                        # Player 1 wins
                        picksTable.update_item(
                            Key={'email': picksList[0]['email']},
                            UpdateExpression="SET #Winner = :w",
                            ExpressionAttributeNames={'#Winner': 'Winner'},
                            ExpressionAttributeValues={':w': True} 
                        )
                        logger.info(f"Player {picksList[0]['email']} wins the tiebreaker with a tieBreaker of {user1tieBreaker} compared to {user2tieBreaker} and Monday night total points of {mondayNightTotalPoints}.")
                        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Player {picksList[0]['email']} wins the tiebreaker with a tieBreaker of {user1tieBreaker} compared to {user2tieBreaker} and Monday night total points of {mondayNightTotalPoints}.", "INFO")
                    else:
                        # Player 2 wins
                        picksTable.update_item(
                            Key={'email': picksList[1]['email']},
                            UpdateExpression="SET #Winner = :w",
                            ExpressionAttributeNames={'#Winner': 'Winner'},
                            ExpressionAttributeValues={':w': True} 
                        )
                        logger.info(f"Player {picksList[1]['email']} wins the tiebreaker with a tieBreaker of {user2tieBreaker} compared to {user1tieBreaker} and Monday night total points of {mondayNightTotalPoints}.")
                        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"Player {picksList[1]['email']} wins the tiebreaker with a tieBreaker of {user2tieBreaker} compared to {user1tieBreaker} and Monday night total points of {mondayNightTotalPoints}.", "INFO")
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "method: validateAndFixFBPPicks", f"DynamoDB Error: {e}", "ERROR")
        return {
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