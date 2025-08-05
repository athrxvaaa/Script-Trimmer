# Modal Queue Integration for Real-time Progress Updates

This document describes the implementation of Modal Queue for real-time progress updates in the Script Trimmer application.

## Overview

The application now uses Modal Queue instead of job-based polling for real-time progress updates. This provides:

- **Real-time updates**: Progress updates are sent immediately as they happen
- **No polling overhead**: Eliminates the need for repeated API calls
- **Better user experience**: Users see live progress without delays
- **Scalable architecture**: Queue-based system handles multiple concurrent requests

## Architecture Changes

### 1. Modal Queue Initialization
```python
# Modal Queue for real-time progress updates
progress_queue = modal.Queue.new()
```

### 2. S3 URL Hashing
Each S3 URL is hashed to create a unique queue key:
```python
def hash_s3_url(s3_url: str) -> str:
    """Hash S3 URL to use as queue key"""
    return hashlib.md5(s3_url.encode()).hexdigest()
```

### 3. Progress Update Function
```python
def send_progress_update(s3_url: str, status: str, message: str, progress: float = None, result: dict = None, error: str = None):
    """Send progress update to Modal Queue"""
    queue_key = hash_s3_url(s3_url)
    update_data = {
        "s3_url": s3_url,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    # Add optional fields
    if progress is not None:
        update_data["progress"] = progress
    if result is not None:
        update_data["result"] = result
    if error is not None:
        update_data["error"] = error
    
    progress_queue.put((queue_key, update_data))
```

## API Endpoints

### 1. Extract Audio Endpoint (Updated)
**POST** `/extract-audio-endpoint`

**Request:**
```json
{
  "s3_url": "https://bucket.s3.region.amazonaws.com/video.mp4"
}
```

**Response:**
```json
{
  "s3_url": "https://bucket.s3.region.amazonaws.com/video.mp4",
  "queue_key": "md5_hash_of_s3_url",
  "status": "pending",
  "message": "Video processing job started successfully",
  "progress": 0.0
}
```

### 2. Progress Stream Endpoint (New)
**GET** `/progress-stream-endpoint?s3_url=<encoded_s3_url>`

**Response:** Server-Sent Events (SSE) stream with real-time updates

**Example events:**
```json
{"type": "connection", "message": "Connected to progress stream", "s3_url": "..."}
{"s3_url": "...", "status": "running", "message": "Downloading video from S3...", "progress": 15.0, "timestamp": "..."}
{"s3_url": "...", "status": "running", "message": "Extracting audio...", "progress": 30.0, "timestamp": "..."}
{"s3_url": "...", "status": "completed", "message": "Video processing completed successfully!", "progress": 100.0, "result": {...}, "timestamp": "..."}
```

## Frontend Integration

### 1. EventSource Connection
```javascript
function startProgressStream(s3Url) {
    const eventSource = new EventSource(`${PROGRESS_STREAM_URL}?s3_url=${encodeURIComponent(s3Url)}`);
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.status === 'running') {
            updateProgress(data.progress || 0, data.message);
        } else if (data.status === 'completed') {
            updateProgress(100, "Processing completed successfully!");
            displayResults(data.result);
            eventSource.close();
        } else if (data.status === 'failed') {
            showStatus(`❌ Processing failed: ${data.error}`, "error");
            eventSource.close();
        }
    };
}
```

### 2. Processing Flow
1. User uploads video to S3
2. User clicks "Process Video"
3. Frontend calls `/extract-audio-endpoint` with S3 URL
4. Backend starts processing and returns immediately
5. Frontend connects to `/progress-stream-endpoint` with S3 URL
6. Real-time progress updates are received via SSE
7. UI updates in real-time showing current progress
8. When complete, results are displayed automatically

## Progress Update Points

The backend sends progress updates at these key points:

1. **5%** - "Starting video processing..."
2. **15%** - "Downloading video from S3..."
3. **30%** - "Extracting audio..."
4. **50%** - "Processing audio chunks..."
5. **70%** - "Transcribing audio..."
6. **85%** - "Extracting video segments..."
7. **95%** - "Uploading segments to S3..."
8. **100%** - "Video processing completed successfully!"

## Error Handling

- **Connection errors**: Frontend shows error message and re-enables process button
- **Processing errors**: Backend sends error status with details via queue
- **Timeout handling**: No more polling timeouts - real-time updates prevent this

## Benefits

1. **Real-time feedback**: Users see progress immediately
2. **Reduced server load**: No polling requests
3. **Better UX**: No more "processing may be running in background" messages
4. **Scalable**: Queue handles multiple concurrent requests
5. **Reliable**: Modal Queue provides persistent message delivery

## Migration from Job System

The old job-based system has been completely removed:

- ❌ `create_job()` function
- ❌ `update_job()` function  
- ❌ `get_job_status()` function
- ❌ `job_progress_endpoint` endpoint
- ❌ Job storage files

All functionality is now handled by the Modal Queue system.

## Testing

To test the new system:

1. Upload a video file to S3
2. Click "Process Video"
3. Watch real-time progress updates in the UI
4. Verify that results appear automatically when complete

The system provides immediate feedback and eliminates the need for manual polling or page refreshes. 