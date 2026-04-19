import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig


logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "REPLACE_ME_TABLE")
PARTITION_KEY = os.environ.get("PARTITION_KEY", "Week")
SORT_KEY = os.environ.get("SORT_KEY", "GameId")

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


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


@app.get("/replaceRoute")
def get_handler() -> dict[str, Any]:
    return {"statusCode": 200, "body": json.dumps({"ok": True})}


@app.post("/replaceRoute")
def post_handler() -> dict[str, Any]:
    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    # In Powertools resolver routes, this is parsed JSON when valid.
    body = app.current_event.json_body or {}

    # IMPORTANT: include the complete key for update_item on composite-key tables.
    pk_value = body.get(PARTITION_KEY)
    sk_value = body.get(SORT_KEY)
    winner_value = body.get("Winner")

    if pk_value is None or sk_value is None:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "Missing key fields",
                    "required": [PARTITION_KEY, SORT_KEY],
                }
            ),
        }

    try:
        table.update_item(
            Key={PARTITION_KEY: pk_value, SORT_KEY: sk_value},
            UpdateExpression="SET #winner = :winner",
            ExpressionAttributeNames={"#winner": "Winner"},
            ExpressionAttributeValues={":winner": winner_value},
            # Prevent accidental upsert if row is missing.
            ConditionExpression=(
                f"attribute_exists({PARTITION_KEY}) AND attribute_exists({SORT_KEY})"
            ),
            ReturnValues="UPDATED_NEW",
        )
    except ClientError as e:
        logger.exception("DynamoDB update failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "DynamoDB update failed", "detail": str(e)}),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"updated": True}, default=_json_default),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return app.resolve(event, context)
