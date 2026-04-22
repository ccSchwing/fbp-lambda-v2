import json
import os
import re
import boto3
import logging
from decimal import Decimal
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from fbplib.fbpLog import fbpLog
from fbplib.getCurrentWeek import getCurrentWeek


'''
This function calcualates the weekly results for each user based on their picks and the actual game results for the week.

'''

logger = logging.getLogger()
logger.info("Initializing UpdateWeeklyResults Lambda function")  # Log initialization message
logger.setLevel(logging.INFO)




cors_config = CORSConfig(
    allow_origin="*",
    allow_headers=[
        "Content-Type",
        "X-Amz-Date",
        "Authorization",
        "X-Api-Key",
        "X-Amz-Security-Token",
    ],
    max_age=86400,
    allow_credentials=False,
)

app = APIGatewayHttpResolver(cors=cors_config)


@app.get("/updateWeeklyResults")
def updateWeeklyResults():
    FBP_WEEKLY_RESULTS_TABLE = os.environ.get('FBPWeeklyResultsTable', 'FBP-Weekly-Results')
    logger.info(f"Using DynamoDB table: {FBP_WEEKLY_RESULTS_TABLE}")  # Log the table name being used
    fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", "Lambda function initialized", "INFO")
    fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", "Retrieving weekly results", "INFO")
    '''
    FBP_USERS_TABLE contains the entries for each user, including their email, totalCorrectPicks, and totalIncorrectPicks,
    and whether the user was the winner for the week. This table is updated with the total correct and incorrect picks for
    the week for each user after each week.
    FBP_PICKS_TABLE contains the entries for each user's picks for each week, including
    email address week and tieBreaker.
    This table is the raw data for calculating the weekly results. It is updated with the number of correct picks,
    correct picks, and incorrect picks
    FBP_WEEKLY_RESULTS_TABLE contains the entries for each user's results for each week, including email,
    week, correctPicks, incorrectPicks, and whether they were the winner for the week.
    This table is updated with the number of correct picks, incorrect picks, and whether they were the winner for the week after each week.
    '''
    FBP_USERS_TABLE_NAME = os.environ.get('FBPUsersTableName', 'FBP-Users')
    logger.info(f"Using FBP Users DynamoDB table: {FBP_USERS_TABLE_NAME}")
    dynamodb = boto3.resource('dynamodb')
    resultsTable = dynamodb.Table(FBP_WEEKLY_RESULTS_TABLE) 
    usersTable = dynamodb.Table(FBP_USERS_TABLE_NAME)

    FBP_PICKS_TABLE_NAME = os.environ.get('FBPPicksTableName', 'FBP-Picks')
    logger.info(f"Using FBP Picks DynamoDB table: {FBP_PICKS_TABLE_NAME}")
    picksTable = dynamodb.Table(FBP_PICKS_TABLE_NAME)
    logger.info(f"Using FBP Picks DynamoDB table: {FBP_PICKS_TABLE_NAME}")

    week=getCurrentWeek()
    if week is None:
        fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", "Could not determine current week", "ERROR")
        return Response (
            status_code=500,
             content_type="application/json",
             body=json.dumps({'error': 'Could not determine current week'}),
        )
    logger.info(f"Retrieving results for week: {week}")
    fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"Retrieving results for week: {week}", "INFO")

    try:
        '''
        Get all picks for the week from the FBP_PICKS_TABLE and calculate the number of correct and incorrect picks for each user.
        Then update the FBP_WEEKLY_RESULTS_TABLE with the number of correct and incorrect picks for each user and
        whether they were the winner for the week. Finally, update the FBP_USERS_TABLE
        '''
        response = picksTable.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('week').eq(week)
        )
        allUserPicks  = response.get('Items', [])

        if not allUserPicks:
            logger.warning(f"No picks found for week {week}")
            fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"No picks found for week {week}", "WARNING")
            return Response (
                status_code=404,
                content_type="application/json",
                body=json.dumps({'error': f'No picks found for week {week}'}),
            )
        else:
            logger.info(f"Retrieved {len(allUserPicks)} picks for week {week}")
            fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"Retrieved {len(allUserPicks)} picks for week {week}", "INFO")
            '''
            Just update FBP_WEEKLY_RESULTS_TABLE with the correct and incorrect picks for each user for the week.
            Leave it to GetWeklyResults to determine the winner and update the FBP_USERS_TABLE with the total correct
            and incorrect picks for each user.
            '''
            success = updateWeeklyUserResults(allUserPicks=allUserPicks, resultsTable=resultsTable, usersTable=usersTable, week=week)
            if not success:
                logger.error("Failed to update weekly user results")
                fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", "Failed to update weekly user results", "ERROR")
                return Response (
                    status_code=500,
                    content_type="application/json",
                    body=json.dumps({'error': 'Failed to update weekly user results'}),
                )
            else:
                logger.info(f"Updated weekly user results for week {week}")
                fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"Updated weekly user results for week {week}", "INFO")
                return Response (
                    status_code=200,
                    content_type="application/json",
                    body=json.dumps({'message': f'Weekly results updated for week {week}'}),
                )
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"DynamoDB Error: {e}", "ERROR")
        return Response (
            status_code=500,
            content_type="application/json",
            body=json.dumps({'error': 'DynamoDB Error'}),
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"Unexpected error: {e}", "ERROR")
        return Response (
            status_code=500,
            content_type="application/json",
            body=json.dumps({'error': 'Unexpected error'}),
        )

def updateWeeklyUserResults(allUserPicks: List[Dict[str, Any]], resultsTable, usersTable, week: int):
    FBP_SCHEDULE_TABLE_NAME = os.environ.get('FBPScheduleTableName', '2025-Schedule')
    logger.info(f"Using FBP Schedule DynamoDB table: {FBP_SCHEDULE_TABLE_NAME}")
    dynamodb = boto3.resource('dynamodb')
    scheduleTable = dynamodb.Table(FBP_SCHEDULE_TABLE_NAME)
    scheduleResults = scheduleTable.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('Week').eq(week)
    )
    if not scheduleResults.get('Items'):
        logger.warning(f"No schedule found for week {week}")
        fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"No schedule found for week {week}", "WARNING")
        return False

    scheduleItems  = scheduleResults.get('Items', [])
    scheduleItems = sorted(scheduleItems, key=lambda x: x['GameId'])  # Sort by GameId to ensure correct order
    gameResults = {}
    index = 0
    for game in scheduleItems:
        winnerOfGame = game['Winner']
        # gameId = game['GameId']
        # I think it's safe to assume that the game results are in the
        # same order as the picks for the week.
        gameResults[index] = winnerOfGame  # Either H or A 
        index += 1
    '''
    Now we have the results for each game for the week in gameResults.
    We can now calculate the number of correct and incorrect picks for each user.
    '''
    for picks in allUserPicks:
        '''
        Get the picks for the user and compare them to the game results to
        calculate the number of correct and incorrect picks for the user.
        '''
        index = 0
        userPicks= picks['picks']  # This is a list of picks for the user for the week
        userPicks=list(userPicks)  # Convert the picks to a list of picks in the correct order
        gameResultsList = [gameResults[i] for i in range(len(gameResults))]  # Convert gameResults to a list of results in the correct order
        correctPicks = 0
        incorrectPicks = 0
        for index in range(len(userPicks)):
            if index >= len(gameResultsList):
                logger.warning(f"Index {index} out of range for gameResults")
                return False
            else:
                if userPicks[index] == gameResultsList[index]:
                    correctPicks += 1
                else:
                    fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"userPick: {userPicks[index]} is incorrect for game result: {gameResultsList[index]}", "INFO")
                    incorrectPicks += 1
                index += 1
        email=picks['email']
        # correctPicks=picks['CorrectPicks']
        # incorrectPicks=picks['IncorrectPicks']
        try:
            resultsTable.update_item(
            Key={'email': email},
            UpdateExpression="SET #CorrectPicks = :c, #IncorrectPicks = :i",
            ExpressionAttributeNames={'#CorrectPicks': 'correctPicks', '#IncorrectPicks': 'incorrectPicks'},
            ExpressionAttributeValues={':c': correctPicks, ':i': incorrectPicks}
        )
        except ClientError as e:
            logger.error(f"DynamoDB Error: {e}")
            fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"DynamoDB Error: {e}", "ERROR")
            return False
        '''
        Update the FBP_USERS_TABLE with the Total Correct and Incorrect Picks for the user for the Season.
        '''
        try:
            usersTable.update_item(
                Key={'email': email},
                UpdateExpression="SET #totalCorrectPicks = if_not_exists(#totalCorrectPicks, :zero) + :c, #totalIncorrectPicks = if_not_exists(#totalIncorrectPicks, :zero) + :i",
                ExpressionAttributeNames={'#totalCorrectPicks': 'totalCorrectPicks', '#totalIncorrectPicks': 'totalIncorrectPicks'},
                ExpressionAttributeValues={':zero': 0, ':c': correctPicks, ':i': incorrectPicks}
        )
        except ClientError as e:
            logger.error(f"DynamoDB Error: {e}")
            fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"DynamoDB Error: {e}", "ERROR")
            return False
        logger.info(f"Updated weekly results for user: {email} with correct picks: {correctPicks} and incorrect picks: {incorrectPicks}")
        fbpLog("fbpadmin@my-fbp.com", "UpdateWeeklyResults", f"Updated weekly results for user: {email} with correct picks: {correctPicks} and incorrect picks: {incorrectPicks}", "INFO")
    return True


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))  # Log the received event for debugging
    return app.resolve(event, context)