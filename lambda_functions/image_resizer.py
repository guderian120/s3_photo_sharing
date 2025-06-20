import json
import boto3
from PIL import Image  # Python Imaging Library for image processing
import io  # For handling byte streams
import os
from urllib.parse import unquote_plus  # For URL decoding S3 keys
import uuid
from datetime import datetime

# Initialize the S3 client
s3 = boto3.client('s3')

# Dictionary of supported image formats with their corresponding:
# - PIL format identifiers
# - MIME content types
SUPPORTED_FORMATS = {
    'jpg': {'format': 'JPEG', 'content_type': 'image/jpeg'},
    'jpeg': {'format': 'JPEG', 'content_type': 'image/jpeg'},
    'png': {'format': 'PNG', 'content_type': 'image/png'},
    'webp': {'format': 'WEBP', 'content_type': 'image/webp'},
    'gif': {'format': 'GIF', 'content_type': 'image/gif'},
    'bmp': {'format': 'BMP', 'content_type': 'image/bmp'},
    'tiff': {'format': 'TIFF', 'content_type': 'image/tiff'}
}

def lambda_handler(event, context):
    """
    AWS Lambda function to generate thumbnails from uploaded images.
    
    This function:
    1. Triggers on S3 upload events
    2. Downloads the uploaded image
    3. Validates the image format and content
    4. Creates a 150x150 thumbnail while maintaining aspect ratio
    5. Uploads the thumbnail to a separate S3 bucket
    6. Preserves original metadata and adds processing information
    
    Args:
        event (dict): AWS Lambda event containing S3 upload information
        context (object): AWS Lambda runtime context
    
    Returns:
        dict: Response object with status code and processing details
    """
    try:
        # --- Extract S3 Object Information ---
        # Parse the S3 event notification to get bucket and key
        # The key is URL-encoded, so we need to decode it
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        raw_key = event['Records'][0]['s3']['object']['key']
        source_key = unquote_plus(raw_key)  # Decode URL-encoded characters
        
        print(f"Processing image: s3://{source_bucket}/{source_key}")
        
        # --- Validate File Format ---
        # Extract file extension and check against supported formats
        file_extension = source_key.split('.')[-1].lower()
        if file_extension not in SUPPORTED_FORMATS:
            supported = ', '.join(SUPPORTED_FORMATS.keys())
            raise ValueError(
                f"Unsupported image format: {file_extension}. "
                f"Supported formats: {supported}"
            )
        
        # --- Download Image ---
        # Get the image object from S3 and read its contents
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        image_data = response['Body'].read()
        
        # Validate we actually received image data
        if not image_data:
            raise ValueError("Downloaded image is empty (0 bytes)")
        
        # --- Image Verification ---
        # Create an in-memory buffer for the image data
        image_buffer = io.BytesIO(image_data)
        image_buffer.seek(0)  # Reset buffer position to start
        
        # First pass: Verify the image is valid
        try:
            with Image.open(image_buffer) as image:
                image.verify()  # Verify file integrity without loading pixels
        except Exception as verify_error:
            raise ValueError(f"Invalid image file: {str(verify_error)}")
        
        # --- Image Processing ---
        # Reset buffer for actual processing
        image_buffer.seek(0)
        with Image.open(image_buffer) as image:
            # Extract metadata from original upload
            metadata = response.get('Metadata', {})
            user_email = metadata.get('uploadedBy', 'unknown')
            
            # Convert JPEG images to RGB mode if they aren't already
            # This prevents issues with CMYK or other color spaces
            if file_extension in ['jpg', 'jpeg'] and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get original dimensions
            width, height = image.size
            
            # Create thumbnail (max 150x150 while maintaining aspect ratio)
            image.thumbnail((150, 150))
            thumb_width, thumb_height = image.size
            
            # --- Prepare Thumbnail for Upload ---
            thumb_buffer = io.BytesIO()
            image.save(
                thumb_buffer,
                format=SUPPORTED_FORMATS[file_extension]['format'],
                quality=85  # Good balance between quality and file size
            )
            thumb_buffer.seek(0)  # Reset buffer position after saving
            
            # Generate target key with 'thumb-' prefix
            target_key = f"thumb-{source_key}"
            
            # --- Upload Thumbnail ---
            s3.put_object(
                Bucket="photo-sharing-bucket-thumbnail",
                Key=target_key,
                Body=thumb_buffer,
                ContentType=SUPPORTED_FORMATS[file_extension]['content_type'],
                Metadata={
                    'original-key': source_key,
                    'processed-by': 'thumbnail-generator',
                    'uploadedBy': user_email,  # Preserve uploader info
                    'original-dimensions': f"{width}x{height}",
                    'thumbnail-dimensions': f"{thumb_width}x{thumb_height}",
                    'processing-date': datetime.utcnow().isoformat()
                }
            )
        
        # --- Success Response ---
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Thumbnail created successfully',
                'thumbnail_key': target_key,
                'original_key': source_key,
                'original_dimensions': f"{width}x{height}",
                'thumbnail_dimensions': f"{thumb_width}x{thumb_height}"
            })
        }
        
    except Exception as e:
        # --- Error Handling ---
        error_message = f"Error processing {source_key if 'source_key' in locals() else 'unknown'}: {str(e)}"
        print(error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'object_key': source_key if 'source_key' in locals() else 'unknown',
                'stack_trace': traceback.format_exc() if 'traceback' in globals() else 'Not available'
            })
        }