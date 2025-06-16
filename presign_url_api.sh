# Create REST API
aws --profile sandbox apigateway create-rest-api --name 'Presigned URL Generator'

# Get API ID and root resource ID
API_ID=$(aws --profile sandbox apigateway get-rest-apis --query "items[?name=='Presigned URL Generator'].id" --output text)
ROOT_ID=$(aws --profile sandbox apigateway get-resources --rest-api-id $API_ID --query "items[0].id" --output text)

# Create /generate-url resource
RESOURCE_ID=$(aws --profile sandbox apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part generate-url \
    --query "id" \
    --output text)

# Create POST method
aws --profile sandbox apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE

# Set Lambda integration
aws --profile sandbox apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-west-1:288761743924:function:photo-share-presign/invocations

# Deploy the API
aws --profile sandbox apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod

# Output your endpoint URL
echo "Your endpoint: https://${API_ID}.execute-api.eu-west-1.amazonaws.com/prod/generate-url"