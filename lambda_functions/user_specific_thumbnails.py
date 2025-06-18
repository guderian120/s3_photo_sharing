import json
import boto3
import os
import traceback

dynamodb = boto3.resource('dynamodb')
table_name = 'PhotoShareTable'
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, OPTIONS"
    }

    print("Received event:", json.dumps(event))

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    # Extract user email from Cognito authorizer claims
    try:
        claims = event['requestContext']['authorizer']['claims']
        user_email = claims.get('email')
        if not user_email:
            raise ValueError("User email not found in token.")
        print(f"Querying thumbnails for user: {user_email}")
    except Exception as e:
        traceback.print_exc()
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({"error": "Unauthorized", "details": str(e)})
        }

    try:
        # Query DynamoDB using the GSI on uploadedBy
        response = table.query(
            IndexName='uploadedByIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('uploadedBy').eq(user_email)
        )

        items = response.get('Items', [])
        print(f"Found {len(items)} items for {user_email}")

        thumbnails = [{"name": item["thumbnailKey"], "originalFileName": item["originalFileName"]} for item in items]

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"thumbnails": thumbnails})
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Failed to fetch thumbnails", "details": str(e)})
        }
