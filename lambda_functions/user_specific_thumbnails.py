import json
import boto3
import os
import traceback
from boto3.dynamodb.conditions import Key  # For DynamoDB key conditions

# Initialize DynamoDB resource
# Using resource interface for higher-level abstraction
dynamodb = boto3.resource('dynamodb')

# Get table name (consider using environment variable in production)
table_name = os.environ.get('PHOTO_SHARE_TABLE', 'PhotoShareTable')  # Default to 'PhotoShareTable' if not set
table = dynamodb.Table(table_name)  # Reference to our DynamoDB table

def lambda_handler(event, context):
    """
    AWS Lambda function to query user's photo thumbnails from DynamoDB.
    
    This function:
    1. Handles CORS preflight OPTIONS requests
    2. Extracts user email from Cognito JWT claims
    3. Queries DynamoDB using GSI (uploadedByIndex)
    4. Returns thumbnail metadata in a structured format
    
    Security:
    - Uses Cognito for authentication
    - Only returns thumbnails belonging to the authenticated user
    - Implements proper CORS headers
    
    Args:
        event (dict): AWS Lambda event containing:
            - HTTP method and headers
            - Cognito authorizer claims
        context (object): AWS Lambda context object
    
    Returns:
        dict: Response object with:
            - statusCode (int)
            - headers (dict)
            - body (JSON string)
    """
    
    # CORS headers configuration
    # These headers enable cross-origin requests from web browsers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Allow any origin (restrict in production)
        "Access-Control-Allow-Headers": "Content-Type, Authorization",  # Allowed headers
        "Access-Control-Allow-Methods": "GET, OPTIONS"  # Allowed HTTP methods
    }

    # Log the incoming event for debugging (sanitize in production)
    print("Received event:", json.dumps(event, indent=2))

    # --- Handle CORS Preflight Request ---
    # Browsers send OPTIONS requests first to check CORS permissions
    if event.get("httpMethod") == "OPTIONS":
        print("Handling CORS preflight request")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    # --- Extract User Identity ---
    try:
        # Get claims from Cognito authorizer (JWT token)
        claims = event['requestContext']['authorizer']['claims']
        
        # Extract email - our primary user identifier
        user_email = claims.get('email')
        if not user_email:
            raise ValueError("User email not found in token claims")
            
        print(f"Querying thumbnails for user: {user_email}")
        
    except Exception as e:
        # Log full error for debugging
        traceback.print_exc()
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "error": "Unauthorized",
                "details": str(e),
                "message": "Failed to authenticate user"
            })
        }

    # --- Query DynamoDB ---
    try:
        # Query using Global Secondary Index (GSI) on uploadedBy
        # This allows efficient lookup of all items for a user
        response = table.query(
            IndexName='uploadedByIndex',  # Name of our GSI
            KeyConditionExpression=Key('uploadedBy').eq(user_email)  # Exact match on email
            # Consider adding Limit and pagination for production
        )

        # Get items or default to empty list if none found
        items = response.get('Items', [])
        print(f"Found {len(items)} thumbnails for {user_email}")

        # Transform DynamoDB items into client-friendly format
        thumbnails = [
            {
                "name": item["thumbnailKey"],  # S3 key for thumbnail
                "originalFileName": item["originalFileName"],  # Original filename
                # Consider adding more metadata like:
                # "uploadDate": item.get("uploadDate"),
                # "dimensions": item.get("dimensions")
            } 
            for item in items
        ]

        # Successful response
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "thumbnails": thumbnails,
                "count": len(thumbnails)
                # Consider adding pagination info:
                # "lastEvaluatedKey": response.get('LastEvaluatedKey')
            })
        }

    except Exception as e:
        # Log full error for debugging
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": "Failed to fetch thumbnails",
                "details": str(e),
                "message": "Server error while processing your request"
            })
        }