# 🎬 Script Trimmer - AI Video Processing Platform

A modern, AI-powered video processing platform that automatically segments videos into meaningful chunks using advanced audio analysis and topic detection. Built with FastAPI on Modal with real-time progress tracking.

## 🚀 Live Demo

**Frontend**: https://video-processor-frontend-1dmshdkxm-atharvas-projects-edc46cc8.vercel.app

## 📡 Deployed API Endpoints

### 1. Get Presigned URL Endpoint
**URL**: `https://lu-labs--script-trimmer-boto3-get-presigned-url-endpoint.modal.run`  
**Method**: `POST`  
**Purpose**: Generate presigned URLs for direct S3 uploads

**Request Body**:
```json
{
  "filename": "video.mp4"
}
```

**Response**:
```json
{
  "message": "Presigned URL generated successfully",
  "presigned_url": "https://bucket.s3.region.amazonaws.com/...",
  "s3_url": "https://bucket.s3.region.amazonaws.com/video.mp4",
  "s3_key": "uploads/video.mp4",
  "expires_in": 3600
}
```

### 2. Extract Audio Endpoint
**URL**: `https://lu-labs--script-trimmer-boto3-extract-audio-endpoint.modal.run`  
**Method**: `POST`  
**Purpose**: Process uploaded videos for audio extraction and segmentation

**Request Body**:
```json
{
  "s3_url": "https://bucket.s3.region.amazonaws.com/video.mp4"
}
```

**Response**:
```json
{
  "s3_url": "https://bucket.s3.region.amazonaws.com/video.mp4",
  "queue_key": "md5_hash_of_s3_url",
  "status": "pending",
  "message": "Video processing job started successfully",
  "progress": 0.0
}
```

### 3. Progress Stream Endpoint
**URL**: `https://lu-labs--script-trimmer-boto3-progress-stream-endpoint.modal.run`  
**Method**: `GET`  
**Purpose**: Real-time progress updates via Server-Sent Events (SSE)

**Query Parameters**:
- `s3_url`: URL-encoded S3 URL of the video being processed

**Response**: Server-Sent Events stream with real-time updates

**Example Events**:
```json
{"type": "connection", "message": "Connected to progress stream", "s3_url": "..."}
{"s3_url": "...", "status": "running", "message": "Downloading video from S3...", "progress": 15.0, "timestamp": "..."}
{"s3_url": "...", "status": "running", "message": "Extracting audio...", "progress": 30.0, "timestamp": "..."}
{"s3_url": "...", "status": "completed", "message": "Video processing completed successfully!", "progress": 100.0, "result": {...}, "timestamp": "..."}
```

## ✨ Features

### 🎥 **Enhanced Video Display**
- **Embedded Video Players** - Videos play directly in the browser
- **Compact Preview Windows** - Small, clean video players with hover effects
- **Responsive Grid Layout** - Automatically adapts to screen size
- **File Size Display** - Shows size in MB for each video segment
- **Modern UI** - Professional design with rounded corners and smooth animations

### 🔧 **Backend Improvements**
- **Boto3 Integration** - Native AWS S3 client for reliable uploads
- **Enhanced Error Handling** - Better error messages and debugging
- **Improved Logging** - Detailed logs for troubleshooting
- **S3 Multipart Upload** - Efficient large file handling (50MB chunks)
- **Real-time Progress** - Modal Queue for live progress updates

### 🎯 **Simplified UI**
- **Video Segments Only** - Shows only video segments with embedded players
- **Interaction Segments** - Separate display for interaction segments
- **No Clutter** - Clean design focused on video content
- **Drag & Drop Upload** - Intuitive file upload interface

## 🏗️ Architecture

### Frontend (Vercel)
- **Framework**: Pure HTML/CSS/JavaScript
- **Deployment**: Vercel (Static Site)
- **Features**: Drag & drop upload, progress tracking, video preview
- **URL**: https://video-processor-frontend-1dmshdkxm-atharvas-projects-edc46cc8.vercel.app

### Backend (Modal)
- **Framework**: FastAPI on Modal
- **Processing**: AI-powered video segmentation
- **Storage**: AWS S3 with presigned URLs
- **Compute**: Modal's serverless infrastructure
- **Real-time Updates**: Modal Queue for progress tracking

## 📋 Prerequisites

- AWS S3 bucket with proper CORS configuration
- Modal account with deployed backend
- Vercel account (for frontend deployment)

## 🔧 Setup Instructions

### 1. Backend Deployment (Modal)

```bash
# Deploy the Modal app
modal deploy modal_app.py

# Check deployment status
modal app list

# View logs
modal app logs <app-id>
```

### 2. Frontend Deployment (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy to production
vercel --prod
```

### 3. Environment Configuration

#### Modal Secrets

```bash
# Create Modal secrets for AWS credentials
modal secret create script-trimmer-secrets \
  --data '{
    "S3_ACCESS_KEY": "your-access-key",
    "S3_SECRET_KEY": "your-secret-key",
    "S3_BUCKET_NAME": "your-bucket-name",
    "S3_REGION": "ap-south-1"
  }'
```

#### S3 CORS Configuration

Apply the CORS configuration in `cors-config.json` to your S3 bucket:

```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}
```

## 🎯 Usage Guide

### Step 1: Upload Video
1. **Select File**: Click the upload area or drag & drop a video file
2. **File Validation**: The app validates file type and size (max 10GB)
3. **Upload to S3**: Click "Upload to S3" to start the upload process
4. **Progress Tracking**: Watch the real-time progress bar
5. **Confirmation**: See upload status and video information

### Step 2: Process Video
1. **Process Button**: After successful upload, click "Process Video"
2. **Processing**: The app calls your Modal backend for video analysis
3. **Real-time Progress**: Watch live progress updates via SSE
4. **Results**: View processing results including:
   - Audio extraction details
   - Video segments with embedded players
   - S3 file URLs
   - Processing time

## 📁 Project Structure

```
├── modal_app.py              # Main Modal FastAPI application
├── index.html               # Frontend application
├── transcribe_segments.py   # Audio transcription module
├── extract_video_segments.py # Video segmentation module
├── requirements_modal.txt   # Modal dependencies
├── cors-config.json        # S3 CORS configuration
├── vercel.json            # Vercel deployment config
└── README.md              # This file
```

## 🔧 Configuration

### Modal App Configuration
- **CPU**: 4.0 cores for heavy video processing
- **Memory**: 16GB RAM for large file handling
- **Timeout**: 4 hours for very large file processing
- **Storage**: Modal Volume for persistent data
- **Queue**: Modal Queue for real-time progress updates

### S3 Configuration
- **Bucket**: Configured via environment variables
- **Region**: ap-south-1 (configurable)
- **Multipart Upload**: 50MB chunks for large files
- **CORS**: Configured for cross-origin requests

## 🚀 Performance Features

- **Large File Support**: Up to 10GB video files
- **Multipart Uploads**: Efficient S3 uploads for large files
- **Real-time Progress**: Live updates via Modal Queue
- **Background Processing**: Non-blocking video analysis
- **Error Recovery**: Robust error handling and retry logic

## 📊 Monitoring

- **Modal Logs**: View processing logs with `modal app logs`
- **S3 Monitoring**: Track upload/download progress
- **Queue Monitoring**: Real-time progress updates
- **Error Tracking**: Comprehensive error logging

## 🔒 Security

- **Presigned URLs**: Secure, time-limited S3 access
- **Environment Variables**: Sensitive data stored in Modal secrets
- **CORS Configuration**: Proper cross-origin request handling
- **Input Validation**: File type and size validation

## 📈 Scalability

- **Serverless**: Modal's auto-scaling infrastructure
- **Queue-based**: Handles multiple concurrent requests
- **S3 Integration**: Scalable cloud storage
- **Background Processing**: Non-blocking operations

---

**Deployment Branch**: `deployment`  
**Last Updated**: December 2024  
**Version**: 1.0.0
