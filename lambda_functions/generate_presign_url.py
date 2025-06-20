import traceback
import boto3
import json
import os
from datetime import datetime, timedelta
import uuid

# Initialize AWS clients
s3 = boto3.client('s3')  # For S3 operations
dynamodb = boto3.resource('dynamodb')  # For DynamoDB operations

# Initialize DynamoDB table reference
table_name = 'PhotoShareTable'  # Should match your DynamoDB table name
table = dynamodb.Table(table_name)  # Reference to our DynamoDB table

def generate_unique_filename(original_name):
    """
    Generates a unique filename to prevent collisions in S3.
    
    Combines:
    - Original filename base
    - Current timestamp
    - Short UUID segment
    
    Example:
    "photo.jpg" → "photo-20230815-143022-abc12345.jpg"
    
    Args:
        original_name (str): The original filename from the client
        
    Returns:
        str: Unique filename with timestamp and UUID components
    """
    # Split filename and extension
    base_name, ext = os.path.splitext(original_name)
    
    # Generate unique components
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # YYYYMMDD-HHMMSS format
    unique_id = str(uuid.uuid4())[:8]  # First 8 characters of UUID
    
    # Construct new filename
    return f"{base_name}-{timestamp}-{unique_id}{ext}"

def lambda_handler(event, context):
    """
    AWS Lambda handler for generating pre-signed S3 upload URLs.
    
    This function:
    1. Validates the upload request
    2. Generates a unique filename
    3. Creates a pre-signed S3 upload URL
    4. Stores metadata in DynamoDB
    5. Returns upload information to client
    
    Security:
    - Uses Cognito for authentication
    - Generates time-limited pre-signed URLs
    - Tracks upload ownership
    
    Args:
        event (dict): AWS Lambda event containing:
            - body: JSON with fileName and fileType
            - requestContext: Cognito authorizer claims
        context: AWS Lambda context object
    
    Returns:
        dict: Response with:
            - statusCode (int)
            - headers (dict)
            - body (JSON string)
    """
    
    # --- Configuration ---
    # Get bucket name from environment variable
    try:
        bucket_name = os.environ['UPLOAD_BUCKET']
        print(f"Using upload bucket: {bucket_name}")
    except KeyError:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Upload bucket not configured'})
        }
    
    # --- Request Validation ---
    try:
        # Parse and validate request body
        body = json.loads(event['body'])
        original_name = body['fileName']
        file_type = body['fileType']
        
        if not original_name or not file_type:
            raise ValueError("fileName and fileType are required")
            
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request format',
                'details': str(e)
            })
        }
    
    # --- User Identification ---
    # Extract user email from Cognito claims
    user_email = 'unknown'
    try:
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            claims = event['requestContext']['authorizer'].get('claims', {})
            user_email = claims.get('email', 'unknown')
            print(f"Upload request from: {user_email}")
    except Exception as e:
        print(f"Warning: Could not extract user email - {str(e)}")
    
    # --- File Preparation ---
    # Generate unique filename to prevent collisions
    unique_filename = generate_unique_filename(original_name)
    thumbnail_key = f"thumb-{unique_filename}"  # Future thumbnail path
    
    # Prepare metadata for tracking
    upload_date = datetime.utcnow().isoformat()
    metadata = {
        'uploadedBy': user_email,
        'originalFileName': original_name,
        'uniqueFileName': unique_filename,
        'thumbnailKey': thumbnail_key,
        'uploadDate': upload_date,
        'contentType': file_type,
        'status': 'pending'
    }
    
    # --- Generate Pre-signed URL ---
    try:
        # Create pre-signed URL with 1-hour expiration
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': unique_filename,
                'ContentType': file_type,
                'Metadata': {
                    'uploadedBy': user_email,
                    'originalFileName': original_name,
                    'thumbnailKey': thumbnail_key,
                    'uniqueFileName': unique_filename
                }
            },
            ExpiresIn=3600  # 1 hour expiration
        )
        print(f"Generated pre-signed URL for {unique_filename}")
        
        # --- Store Metadata in DynamoDB ---
        table.put_item(
            Item={
                # Primary key
                'photoMetadata': unique_filename,
                
                # File identification
                'originalFileName': original_name,
                'thumbnailKey': thumbnail_key,
                'uniqueFileName': unique_filename,
                
                # Storage info
                'originalBucket': bucket_name,
                'contentType': file_type,
                
                # Ownership tracking
                'uploadedBy': user_email,
                'uploadDate': upload_date,
                
                # Status fields (to be updated later)
                'status': 'pending',
                'fileSize': 0,  # Will be updated after upload
                'dimensions': '0x0'  # Will be updated after processing
            }
        )
        print(f"Stored metadata for {unique_filename} in DynamoDB")
        
        # --- Success Response ---
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({
                'presignedUrl': presigned_url,
                'originalFileName': original_name,
                'uniqueFileName': unique_filename,
                'thumbnailKey': thumbnail_key,
                'metadata': metadata
            })
        }
        
    except Exception as e:
        print(f"Error generating pre-signed URL: {str(e)}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({
                'error': 'Failed to generate upload URL',
                'details': str(e)
            })
        }