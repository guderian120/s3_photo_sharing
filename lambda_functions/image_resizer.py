import json
import boto3
from PIL import Image
import io
import os
from urllib.parse import unquote_plus
import uuid
from datetime import datetime

s3 = boto3.client('s3')

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
    try:
        # Get S3 object information
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        raw_key = event['Records'][0]['s3']['object']['key']
        source_key = unquote_plus(raw_key)
        
        print(f"Processing image: s3://{source_bucket}/{source_key}")
        
        # Validate file extension
        file_extension = source_key.split('.')[-1].lower()
        if file_extension not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {file_extension}")
        
        # Download and verify image
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        image_data = response['Body'].read()
        
        if not image_data:
            raise ValueError("Downloaded image is empty")
        
        # Create BytesIO object and verify image
        image_buffer = io.BytesIO(image_data)
        image_buffer.seek(0)  # Ensure we're at the start
        
        try:
            with Image.open(image_buffer) as image:
                # Verify the image is valid
                image.verify()
        except Exception as verify_error:
            raise ValueError(f"Invalid image file: {str(verify_error)}")
        
        # Reset buffer for actual processing
        image_buffer.seek(0)
        with Image.open(image_buffer) as image:
            # Get metadata
            metadata = response.get('Metadata', {})
            user_email = metadata.get('uploadedBy', 'unknown')
            
            # Process image
            if file_extension in ['jpg', 'jpeg'] and image.mode != 'RGB':
                image = image.convert('RGB')
            
            width, height = image.size
            image.thumbnail((150, 150))
            thumb_width, thumb_height = image.size
            
            # Prepare thumbnail
            thumb_buffer = io.BytesIO()
            image.save(
                thumb_buffer,
                format=SUPPORTED_FORMATS[file_extension]['format'],
                quality=85
            )
            thumb_buffer.seek(0)
            
            # Generate unique names
            target_key = f"thumb-{source_key}"
            
            # Upload thumbnail
            s3.put_object(
                Bucket="photo-sharing-bucket-thumbnail",
                Key=target_key,
                Body=thumb_buffer,
                ContentType=SUPPORTED_FORMATS[file_extension]['content_type'],
                Metadata={
                    'original-key': source_key,
                    'processed-by': 'thumbnail-generator',
                    'uploadedBy': user_email,
                    'original-dimensions': f"{width}x{height}",
                    'thumbnail-dimensions': f"{thumb_width}x{thumb_height}"
                }
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Thumbnail created successfully',
                'thumbnail_key': target_key,
                'original_key': source_key
            })
        }
        
    except Exception as e:
        print(f"Error processing {source_key}: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'object_key': source_key if 'source_key' in locals() else 'unknown'
            })
        }   