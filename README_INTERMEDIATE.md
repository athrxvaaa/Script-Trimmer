# 🎬 Intermediate Video Processing Script

This intermediate script provides a complete workflow for uploading videos to S3 and processing them with real-time polling.

## 📁 Files Created

1. **`upload_and_process.py`** - Complete Python script for S3 upload + processing
2. **`polling_frontend.html`** - Simplified frontend for polling existing S3 URLs
3. **`README_INTERMEDIATE.md`** - This documentation

## 🚀 Usage Options

### Option 1: Complete Workflow (Python Script)

Use the Python script to handle the entire workflow from file upload to results:

```bash
# Install dependencies
pip install requests

# Run the script
python upload_and_process.py /path/to/your/video.mp4
```

**Features:**
- ✅ Automatic S3 upload using presigned URLs
- ✅ Job creation and management
- ✅ Real-time progress polling
- ✅ Results display and JSON export
- ✅ Error handling and retry logic

### Option 2: Polling Interface (HTML)

Use the HTML interface for existing S3 URLs:

```bash
# Serve the HTML file
python -m http.server 8000
# Then open http://localhost:8000/polling_frontend.html
```

**Features:**
- ✅ Simple S3 URL input
- ✅ Real-time polling with progress
- ✅ Video segment display
- ✅ Modern UI with status updates

## 🔧 API Endpoints Used

### 1. Get Presigned URL
```bash
POST https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run
{
  "filename": "video.mp4",
  "content_type": "video/mp4"
}
```

### 2. Start Processing Job
```bash
POST https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run
{
  "s3_url": "https://bucket.s3.amazonaws.com/video.mp4"
}
```

### 3. Poll Job Status
```bash
GET https://lu-labs--script-trimmer-job-status-endpoint.modal.run?job_id={job_id}
```

## 📊 Workflow Steps

### Python Script Workflow:

1. **File Validation** - Check file exists and size (max 10GB)
2. **Get Presigned URL** - Request S3 upload URL
3. **Upload to S3** - Upload file using presigned URL
4. **Start Job** - Create processing job and get job ID
5. **Poll Status** - Check job status every 10 seconds
6. **Display Results** - Show video segments when complete
7. **Save Results** - Export results to JSON file

### HTML Interface Workflow:

1. **Enter S3 URL** - User provides existing S3 URL
2. **Start Job** - Create processing job
3. **Poll Status** - Real-time progress updates
4. **Display Results** - Show embedded video players

## 🎯 Key Features

### Real-time Progress Tracking
- **Progress Bar**: Visual progress from 0-100%
- **Status Messages**: "Starting...", "Processing...", "Completed!"
- **Time Estimates**: Shows polling attempts and timeouts

### Error Handling
- **Network Errors**: Retry logic for failed requests
- **Timeout Handling**: Graceful timeout after 30 minutes
- **File Validation**: Size and format checks
- **Status Validation**: Proper error messages

### Results Display
- **Video Segments**: Topic-based segments with embedded players
- **Interaction Segments**: Interaction moments (if detected)
- **File Information**: Size, type, and metadata
- **JSON Export**: Complete results saved to file

## 📋 Example Usage

### Python Script Example:
```bash
# Process a video file
python upload_and_process.py /Users/atharva/Desktop/video.mp4

# Output:
# ============================================================
# 🎬 VIDEO PROCESSING WORKFLOW STARTED
# ============================================================
# 📁 File: video.mp4
# 📏 Size: 156.78 MB
# ============================================================
# 📤 Getting presigned URL for: video.mp4
# ✅ Presigned URL received: https://bucket.s3.amazonaws.com/video.mp4
# ☁️  Uploading video.mp4 to S3...
# ✅ S3 upload completed successfully!
# 🚀 Starting processing job for: https://bucket.s3.amazonaws.com/video.mp4
# ✅ Job started successfully! Job ID: abc123-def456
# 📊 Polling job status for: abc123-def456
# 📊 [████████░░] 80.0% - RUNNING: Processing video from S3...
# ✅ Processing completed successfully!
# 🎉 PROCESSING COMPLETED SUCCESSFULLY!
# ============================================================
# 📊 Video Segments: 4
# 💬 Interaction Segments: 3
# ☁️  S3 URLs: 7
# ============================================================
```

### HTML Interface Example:
1. Open `polling_frontend.html` in browser
2. Enter S3 URL: `https://bucket.s3.amazonaws.com/video.mp4`
3. Click "Start Processing"
4. Watch real-time progress updates
5. View video segments when complete

## 🔧 Configuration

### Python Script Configuration:
```python
# API Endpoints
PRESIGNED_URL_ENDPOINT = "https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run"
EXTRACT_AUDIO_ENDPOINT = "https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run"
JOB_STATUS_ENDPOINT = "https://lu-labs--script-trimmer-job-status-endpoint.modal.run"

# Polling Settings
max_attempts = 180  # 30 minutes with 10-second intervals
poll_interval = 10  # seconds between polls
```

### HTML Interface Configuration:
```javascript
// API Endpoints
const EXTRACT_AUDIO_ENDPOINT = "https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run";
const JOB_STATUS_ENDPOINT = "https://lu-labs--script-trimmer-job-status-endpoint.modal.run";

// Polling Settings
const maxAttempts = 180; // 30 minutes
const pollInterval = 10000; // 10 seconds
```

## 🐛 Troubleshooting

### Common Issues:

1. **File Upload Fails**
   - Check file size (max 10GB)
   - Verify file format (MP4, AVI, etc.)
   - Check network connection

2. **Job Creation Fails**
   - Verify S3 URL is accessible
   - Check Modal backend is running
   - Review error messages in console

3. **Polling Timeout**
   - Large videos may take 20-30 minutes
   - Check Modal logs for processing status
   - Verify job ID is valid

4. **Results Not Displaying**
   - Check browser console for errors
   - Verify S3 URLs are publicly accessible
   - Check CORS configuration

### Debug Mode:
```bash
# Python script with verbose logging
python upload_and_process.py video.mp4 2>&1 | tee debug.log

# HTML interface - open browser console (F12)
# Check Network tab for API calls
# Check Console tab for error messages
```

## 📊 Performance Metrics

### Processing Times:
- **Small videos** (< 100MB): 2-5 minutes
- **Medium videos** (100MB-1GB): 5-15 minutes
- **Large videos** (1GB-10GB): 15-30 minutes

### Polling Efficiency:
- **Poll interval**: 10 seconds
- **Max polling time**: 30 minutes
- **Progress updates**: Real-time percentage
- **Status messages**: Current processing stage

## 🔗 Integration

### With Existing Systems:
```python
# Import the VideoProcessor class
from upload_and_process import VideoProcessor

# Use in your own scripts
processor = VideoProcessor()
result = processor.process_video_file(Path("video.mp4"))
```

### With Web Applications:
```html
<!-- Include the polling interface -->
<iframe src="polling_frontend.html" width="100%" height="600px"></iframe>
```

## 🚀 Deployment

### Local Development:
```bash
# Run Python script
python upload_and_process.py video.mp4

# Serve HTML interface
python -m http.server 8000
```

### Production Deployment:
```bash
# Deploy to Vercel
vercel --prod

# Deploy to Modal
modal deploy modal_app.py
```

---

**Happy Video Processing! 🎬✨**

*This intermediate script provides a complete solution for handling large video processing with real-time feedback and robust error handling.* 