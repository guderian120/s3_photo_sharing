#!/bin/bash

# Configuration - CHANGE THESE VALUES
S3_BUCKET="photo-sharing-bucket-thumbnail"
REGION="eu-west-1" 
API_NAME="S3ImageProxy"
STAGE_NAME="prod"
API_PATH="images"
ROLE_NAME="APIGatewayS3AccessRole"

# Create IAM Role for API Gateway
aws --profile sandbox  iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "apigateway.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach S3 read policy to the role
aws --profile sandbox  iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name S3ReadAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::'$S3_BUCKET'/*"]
    }]
  }'

# Get role ARN
ROLE_ARN=$(aws --profile sandbox  iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Create API Gateway
API_ID=$(aws --profile sandbox  apigateway create-rest-api \
  --name $API_NAME \
  --description "API Gateway for S3 image access" \
  --region $REGION \
  --query 'id' \
  --output text)

# Get root resource ID
ROOT_RESOURCE_ID=$(aws --profile sandbox  apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[0].id' \
  --output text)

# Create images resource
RESOURCE_ID=$(aws --profile sandbox  apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_RESOURCE_ID \
  --path-part $API_PATH \
  --query 'id' \
  --output text)

# Create proxy resource for {filename}
PROXY_RESOURCE_ID=$(aws --profile sandbox  apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $RESOURCE_ID \
  --path-part '{filename}' \
  --query 'id' \
  --output text)

# Create GET method
aws --profile sandbox  apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method GET \
  --authorization-type "NONE" \
  --request-parameters '{"method.request.path.filename":true}'

# Set up S3 integration
aws --profile sandbox  apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method GET \
  --type AWS \
  --integration-http-method GET \
  --uri "arn:aws:apigateway:$REGION:s3:path/$S3_BUCKET/{filename}" \
  --credentials $ROLE_ARN \
  --request-parameters '{"integration.request.path.filename":"method.request.path.filename"}'

# Create method response
aws --profile sandbox  apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method GET \
  --status-code 200 \
  --response-parameters '{"method.response.header.Content-Type":true}'

# Create integration response
aws --profile sandbox  apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method GET \
  --status-code 200 \
  --selection-pattern "" \
  --response-parameters '{"method.response.header.Content-Type":"integration.response.header.Content-Type"}'

# Deploy the API
aws --profile sandbox  apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name $STAGE_NAME

# Enable binary media types for proper image handling
aws --profile sandbox  apigateway update-rest-api \
  --rest-api-id $API_ID \
  --patch-operations op='add',path='/binaryMediaTypes/*~1*'

# Output the final URL
echo "API Gateway deployed successfully!"
echo "Test URL format:"
echo "https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/$API_PATH/your-image.jpg"