# 🎬 Script Trimmer - AI Video Processing Platform

A modern, AI-powered video processing platform that automatically segments videos into meaningful chunks using advanced audio analysis and topic detection.

## 🚀 Live Demo

**Frontend**: https://video-processor-frontend-1dmshdkxm-atharvas-projects-edc46cc8.vercel.app

**Backend APIs**:

- Presigned URL: `https://lu-labs--script-trimmer-boto3-get-presigned-url-endpoint.modal.run`
- Extract Audio: `https://lu-labs--script-trimmer-boto3-extract-audio-endpoint.modal.run`

## ✨ Latest Features (Updated)

### 🎥 **Enhanced Video Display**

- **Embedded Video Players** - Videos play directly in the browser
- **Compact Preview Windows** - Small, clean video players with hover effects
- **Responsive Grid Layout** - Automatically adapts to screen size
- **File Size Display** - Shows size in MB for each video segment
- **Modern UI** - Professional design with rounded corners and smooth animations

### 🔧 **Backend Improvements**

- **Boto3 Integration** - Replaced curl/wget with native AWS S3 client
- **Enhanced Error Handling** - Better error messages and debugging
- **Improved Logging** - Detailed logs for troubleshooting
- **S3 Multipart Upload** - Efficient large file handling (50MB chunks)

### 🎯 **Simplified UI**

- **Video Segments Only** - Shows only video segments with embedded players
- **Interaction Segments** - Separate display for interaction segments
- **No Clutter** - Removed S3 files section and processing statistics
- **Clean Design** - Focus on video content with minimal distractions

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
modal secret create aws-credentials \
  --data '{"AWS_ACCESS_KEY_ID": "your-key", "AWS_SECRET_ACCESS_KEY": "your-secret"}'
```

#### S3 CORS Configuration

Apply the CORS configuration in `cors-config.json` to your S3 bucket:

```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedOrigins": [
        "http://localhost:8000",
        "https://*.vercel.app",
        "https://*.modal.run"
      ],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

## 🎯 Usage Guide

### Step 1: Upload Video

1. **Visit**: https://video-processor-frontend-1dmshdkxm-atharvas-projects-edc46cc8.vercel.app
2. **Drag & Drop** or click to select a video file
3. **File Validation**: Supports MP4, AVI, MOV, MKV, FLV, WMV, WEBM, M4V, 3GP (Max 10GB)
4. **Click "Upload to S3"** - Uses presigned URLs for direct browser-to-S3 upload

### Step 2: Process Video

1. **Click "Process Video"** after successful upload
2. **AI Processing**: Backend analyzes video content and creates segments
3. **View Results**: See video segments with embedded players

### Step 3: View Segments

- **Video Segments**: Topic-based segments with embedded players
- **Interaction Segments**: Interaction moments (if detected)
- **Compact Preview**: Small, clean video players with file information

## 📁 File Structure

```
Script_trimmerrr/
├── modal_app.py              # Main Modal backend application
├── index.html                # Frontend application
├── vercel.json              # Vercel deployment configuration
├── cors-config.json         # S3 CORS configuration
├── requirements.txt          # Python dependencies
├── requirements_modal.txt    # Modal-specific dependencies
├── transcribe_segments.py   # Audio transcription module
├── script_trimmer.py        # Core video processing logic
├── extract_video_segments.py # Video segmentation logic
├── main.py                  # Local development server
├── uploads/                 # Local upload directory
├── output/                  # Local output directory
└── video_segments/          # Local video segments directory
```

## 🔧 API Endpoints

### 1. Get Presigned URL

**Endpoint**: `POST https://lu-labs--script-trimmer-boto3-get-presigned-url-endpoint.modal.run`

**Request**:

```json
{
  "filename": "video.mp4",
  "content_type": "video/mp4"
}
```

**Response**:

```json
{
  "message": "Presigned URL generated successfully",
  "presigned_url": "https://bucket.s3.amazonaws.com/...",
  "s3_url": "https://bucket.s3.amazonaws.com/video.mp4",
  "s3_key": "videos/video.mp4",
  "expires_in": 3600
}
```

### 2. Extract Audio & Process Video

**Endpoint**: `POST https://lu-labs--script-trimmer-boto3-extract-audio-endpoint.modal.run`

**Request**:

```json
{
  "s3_url": "https://bucket.s3.amazonaws.com/video.mp4"
}
```

**Response**:

```json
{
  "message": "S3 video processed successfully (audio size: 3.58MB)",
  "audio_file_path": "/data/output/audio.mp3",
  "chunk_files": ["chunk_001.mp3", "chunk_002.mp3"],
  "total_chunks": 9,
  "video_segments": ["video_segments/01_topic.mp4"],
  "total_video_segments": 4,
  "interaction_segments": ["video_segments/interactions/01_interaction.mp4"],
  "total_interaction_segments": 3,
  "s3_urls": [
    {
      "filename": "01_topic.mp4",
      "s3_url": "https://bucket.s3.amazonaws.com/segments/01_topic.mp4",
      "size_mb": 17.96,
      "segment_type": "topic"
    }
  ],
  "processing_time_seconds": 45.2
}
```

## 🎨 UI Features

### Video Display

- **Embedded Players**: Videos play directly in the browser
- **Responsive Grid**: Automatically adjusts to screen size
- **Hover Effects**: Cards lift on hover with shadow
- **File Information**: Shows filename and size
- **Clean Design**: Modern, professional appearance

### Upload Interface

- **Drag & Drop**: Intuitive file selection
- **Progress Tracking**: Real-time upload progress
- **File Validation**: Type and size checking
- **Status Messages**: Clear feedback for users

## 🔒 Security & Performance

### Security Features

- **CORS Headers**: Configured for cross-origin requests
- **File Validation**: Client-side type and size checking
- **S3 Presigned URLs**: Secure, time-limited upload URLs
- **No User Data Storage**: Temporary processing only

### Performance Optimizations

- **Direct S3 Uploads**: Bypass server bandwidth
- **Boto3 Integration**: Native AWS SDK for better performance
- **Multipart Uploads**: Efficient large file handling
- **Progressive Loading**: Videos load on demand

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**

   - Ensure S3 bucket has proper CORS configuration
   - Check Modal app CORS settings
   - Verify Vercel domain is allowed

2. **Upload Failures**

   - Check presigned URL expiration
   - Verify S3 bucket permissions
   - Check browser console for errors

3. **Processing Errors**

   - Check Modal app logs: `modal app logs <app-id>`
   - Verify environment variables
   - Check AWS credentials

4. **Video Display Issues**
   - Ensure S3 URLs are publicly accessible
   - Check video format compatibility
   - Verify CORS headers on S3

### Debug Mode

Open browser console (F12) to see detailed logs and error messages.

## 📊 Monitoring

### Vercel Analytics

- **Traffic**: Monitor frontend usage
- **Performance**: Track loading times
- **Errors**: View client-side errors

### Modal Logs

```bash
# View real-time logs
modal app logs <app-id> --follow

# View recent logs
modal app logs <app-id>
```

### AWS S3 Monitoring

- **Storage Usage**: Monitor bucket size
- **Access Logs**: Track file access
- **Costs**: Monitor S3 charges

## 🔄 Updates & Maintenance

### Frontend Updates

```bash
# Make changes to index.html
# Deploy to Vercel
vercel --prod
```

### Backend Updates

```bash
# Update modal_app.py
# Redeploy to Modal
modal deploy modal_app.py
```

### Environment Updates

```bash
# Update Modal secrets
modal secret create aws-credentials --data '{"new": "values"}'

# Update S3 CORS
aws s3api put-bucket-cors --bucket your-bucket --cors-configuration file://cors-config.json
```

## 📱 Mobile Support

The app is fully responsive and works on:

- ✅ Desktop browsers (Chrome, Firefox, Safari, Edge)
- ✅ Tablets (iPad, Android tablets)
- ✅ Mobile phones (iPhone, Android)
- ✅ Touch devices

## 🚀 Performance Metrics

- **Upload Speed**: Direct S3 uploads (no server bottleneck)
- **Processing Time**: 30-120 seconds depending on video size
- **Video Quality**: Maintains original quality
- **Storage**: Efficient S3 storage with lifecycle policies

## 📞 Support

For issues or questions:

1. **Check Logs**: Browser console and Modal logs
2. **Test APIs**: Use curl or Postman to test endpoints
3. **Verify Configuration**: S3 CORS, Modal secrets, Vercel settings
4. **Monitor Resources**: AWS S3 usage, Modal compute usage

## 🔗 Links

- **Live App**: https://video-processor-frontend-1dmshdkxm-atharvas-projects-edc46cc8.vercel.app
- **Vercel Dashboard**: https://vercel.com/dashboard
- **Modal Dashboard**: https://modal.com/apps
- **AWS S3 Console**: https://s3.console.aws.amazon.com

---

**Happy Video Processing! 🎬✨**

_Last Updated: August 4, 2025_
