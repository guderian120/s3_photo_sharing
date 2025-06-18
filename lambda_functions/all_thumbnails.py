import json
import boto3
import traceback

s3 = boto3.client('s3')
BUCKET_NAME = 'photo-sharing-bucket-thumbnail'

def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, OPTIONS"
    }

    print("Event received:", json.dumps(event))  # Log the incoming event

    if event.get("httpMethod") == "OPTIONS":
        print("CORS preflight request received.")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        print(f"Listing objects from bucket: {BUCKET_NAME}")
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=20)
        contents = response.get('Contents', [])
        print(f"Found {len(contents)} objects in bucket.")

        # Only collect names (keys)
        thumbnails = [{"name": obj['Key']} for obj in contents]

        print(f"Returning {len(thumbnails)} thumbnail names.")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"thumbnails": thumbnails})
        }

    except Exception as e:
        print("Exception occurred:")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": "Failed to load thumbnails", "details": str(e)})
        }
