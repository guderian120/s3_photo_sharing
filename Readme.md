
# Photo Sharing Application

[![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Serverless](https://img.shields.io/badge/Serverless-FD5750?style=for-the-badge&logo=serverless&logoColor=white)](https://serverless.com)

A serverless photo sharing application that:
1. Generates secure upload URLs
2. Automatically creates thumbnails
3. Displays images in a responsive gallery

## System Architecture

```mermaid
graph TD
    A[User] --> B[Frontend Web App]
    B --> C[API Gateway]
    C --> D[Presigned URL Lambda]
    D --> E[S3 Raw Bucket]
    B -->|4. Upload Image| E
    E -->|5. Put Event| C
    C -->|6. Invoke| F[Thumbnail Lambda]
    F -->|7. Download| E
    F -->|8. Upload Thumbnail| G[S3 Thumbnails Bucket]
    B -->|9. Display Thumbnail| G
```

## Workflow

### Upload Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API_Gateway
    participant PresignLambda
    participant S3_Raw
    participant ThumbnailLambda
    participant S3_Thumbs
    
    User->>Frontend: Select Image File
    Frontend->>API_Gateway: POST /generate-url
    API_Gateway->>PresignLambda: Invoke
    PresignLambda->>S3_Raw: Generate Presigned URL
    PresignLambda-->>API_Gateway: Return URL
    API_Gateway-->>Frontend: Return Presigned URL
    Frontend->>S3_Raw: PUT Image (Direct Upload)
    S3_Raw->>API_Gateway: PutObject Event
    API_Gateway->>ThumbnailLambda: Invoke
    ThumbnailLambda->>S3_Raw: Get Original Image
    ThumbnailLambda->>ThumbnailLambda: Resize Image (150x150)
    ThumbnailLambda->>S3_Thumbs: Save Thumbnail
    loop Polling
        Frontend->>S3_Thumbs: GET Thumbnail
        S3_Thumbs-->>Frontend: Return Thumbnail
    end
```

## Components

### 1. Frontend Application
- Single-page HTML/CSS/JavaScript app
- Features:
  - Drag-and-drop upload
  - Progress tracking
  - Thumbnail gallery
- Hosted on S3 Static Website

### 2. Backend Services
| Service | Description | Endpoint |
|---------|-------------|----------|
| Presigned URL Generator | Creates secure upload URLs | `POST /generate-url` |
| Thumbnail Processor | Resizes uploaded images | Auto-triggered |

### 3. Storage Buckets
| Bucket | Purpose | Event Configuration |
|--------|---------|---------------------|
| photo-uploads-raw | Original images | Trigger on PutObject |
| photo-uploads-thumb | Processed thumbnails | - |

## Deployment

### Prerequisites
- AWS Account
- AWS CLI configured
- Node.js 16+

### Installation
```bash
# Clone repository
git clone https://github.com/your-repo/photo-sharing-app.git
cd photo-sharing-app

# Deploy backend
cd backend
npm install
sls deploy

# Deploy frontend
cd ../frontend
aws s3 sync . s3://your-bucket-name
```

## Error Handling

```mermaid
flowchart TD
    A[Start Upload] --> B{Valid File?}
    B -->|Yes| C[Get Presigned URL]
    B -->|No| D[Show Error]
    C --> E{URL Generated?}
    E -->|Yes| F[Upload to S3]
    E -->|No| G[Retry/Abort]
    F --> H{Upload Success?}
    H -->|Yes| I[Wait for Thumbnail]
    H -->|No| J[Retry/Abort]
    I --> K{Poll Thumbnail}
    K -->|Exists| L[Display]
    K -->|Timeout| M[Show Error]
```

## Monitoring
- CloudWatch Alarms for:
  - Failed uploads
  - Thumbnail generation errors
  - API Gateway 5xx errors

## License
Apache 2.0 - See [LICENSE](LICENSE) for details
```

Key features of this README:

1. **Visual Documentation** - All Mermaid diagrams render automatically in:
   - GitHub/GitLab Markdown viewers
   - VS Code with Mermaid plugin
   - Documentation systems like GitBook

2. **Structured Information** - Organized into logical sections:
   - Architecture overview
   - Detailed workflow
   - Component specifications
   - Deployment guide
   - Error handling procedures

3. **Badges** - Quick visual indicators for technologies used

4. **Responsive Design** - Displays properly on all devices

5. **Copy-Paste Ready** - Can be used directly in your repository

To render these diagrams:
1. On GitHub/GitLab - Works natively
2. Locally - Use VS Code with Mermaid extension
3. For PDFs - Use `mermaid-cli` to generate SVGs

