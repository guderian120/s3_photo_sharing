import json
import boto3
import traceback

# Initialize the S3 client
# This creates a low-level client representing Amazon Simple Storage Service (S3)
s3 = boto3.client('s3')

# Define the S3 bucket name where thumbnails are stored
# This should be configured as an environment variable in production
BUCKET_NAME = 'photo-sharing-bucket-thumbnail'

def lambda_handler(event, context):
    """
    AWS Lambda function handler for retrieving photo thumbnails from S3.
    
    This function:
    - Handles CORS preflight OPTIONS requests
    - Lists objects (thumbnails) from the specified S3 bucket
    - Returns the thumbnail names in a JSON response
    - Includes comprehensive error handling
    
    Args:
        event (dict): AWS Lambda event object containing request data
        context (object): AWS Lambda context object with runtime information
        
    Returns:
        dict: Response object with status code, headers, and body
    """
    
    # CORS headers configuration
    # These headers enable cross-origin requests from any domain (*)
    # In production, you might want to restrict the allowed origin
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Allows requests from any origin
        "Access-Control-Allow-Headers": "Content-Type, Authorization",  # Allowed headers
        "Access-Control-Allow-Methods": "GET, OPTIONS"  # Allowed HTTP methods
    }

    # Log the incoming event for debugging purposes
    print("Event received:", json.dumps(event, indent=2))

    # Handle CORS preflight OPTIONS request
    # Browsers send OPTIONS requests first to check CORS permissions
    if event.get("httpMethod") == "OPTIONS":
        print("CORS preflight request received.")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        # Main function logic - retrieve thumbnails from S3
        
        print(f"Listing objects from bucket: {BUCKET_NAME}")
        
        # List objects in the S3 bucket
        # Using list_objects_v2 API with MaxKeys=20 to limit response size
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            MaxKeys=20  # Limit to 20 objects to prevent large responses
        )
        
        # Get the contents list or default to empty list if not present
        contents = response.get('Contents', [])
        print(f"Found {len(contents)} objects in bucket.")
        
        # Extract just the object names (keys) from the S3 response
        # We create a list of dictionaries with just the 'name' field
        # This structure makes it easier for frontend to consume
        thumbnails = [{"name": obj['Key']} for obj in contents]

        print(f"Returning {len(thumbnails)} thumbnail names.")
        
        # Successful response with thumbnails list
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "thumbnails": thumbnails  # The list of thumbnail names
            })
        }

    except Exception as e:
        # Comprehensive error handling
        
        # Log the full exception traceback for debugging
        print("Exception occurred:")
        traceback.print_exc()  # This prints the full stack trace
        
        # Return a 500 error with details (in development)
        # In production, you might want to sanitize error messages
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": "Failed to load thumbnails",  # User-friendly message
                "details": str(e)  # Technical details for debugging
            })
        }