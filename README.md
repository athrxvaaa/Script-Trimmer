# Audio Extraction API

A FastAPI-based service that extracts audio from video files, transcribes the audio, analyzes topics, and creates video segments based on the detected topics.

## Features

- Extract audio from various video formats (MP4, AVI, MOV, etc.) using FFmpeg
- Automatic chunking of audio files larger than 25MB
- **Automatic transcription** using OpenAI Whisper API
- **Topic analysis and segmentation** using GPT-4o-mini
- **Automatic video segment extraction** based on detected topics
- **Automatic S3 upload** of video segments with direct URLs
- **Automatic cleanup** of remnant files from previous runs
- **Final cleanup** of local video segments after S3 upload
- **YouTube video processing** with automatic download and processing
- Configurable chunk duration (default: 10 minutes per chunk)
- File management endpoints (list, download, delete)
- Async file processing
- Automatic cleanup of temporary files
- High-quality audio extraction with configurable bitrate and sample rate

## Complete Pipeline

When you upload a video file, the API automatically:

1. **Clean Previous Files** - Remove any remnant files from previous runs
2. **Download Video** - Download YouTube video (for YouTube URLs only)
3. **Extract Audio** - Extract audio from the video file
4. **Chunk Audio** - Split large audio files into smaller chunks (if needed)
5. **Transcribe** - Transcribe audio using OpenAI Whisper API
6. **Analyze Topics** - Use GPT-4o-mini to detect topics and timestamps
7. **Extract Video Segments** - Create video segments based on detected topics
8. **Upload to S3** - Upload video segments to S3 with direct URLs
9. **Final Cleanup** - Remove local video segments after successful S3 upload
10. **Return Results** - Provide audio files, transcripts, and S3 URLs

## Recent Success Example

**Input:** 90-minute React Bootcamp video (2GB)
**Output:**

- ✅ **Audio Extraction:** 79.73MB audio file
- ✅ **Audio Chunking:** 9 audio chunks (10 minutes each)
- ✅ **Transcription:** Complete transcript with timestamps
- ✅ **Topic Analysis:** 32 distinct topics detected
- ✅ **Video Segments:** 32 video segments created successfully
- ✅ **Processing Time:** 477 seconds (under 8 minutes)

## Setup

### 1. Virtual Environment

The virtual environment has already been created. To activate it:

```bash
source venv/bin/activate
```

### 2. Dependencies

All required dependencies are already installed. If you need to reinstall:

```bash
pip install -r requirements.txt
```

### 3. Run the API

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Extract Audio (Full Pipeline)

**POST** `/extract-audio/`

Upload a video file to extract its audio, transcribe it, analyze topics, and create video segments.

### 2. Process YouTube Video (Full Pipeline)

**POST** `/process-youtube`

Process a YouTube video URL through the complete pipeline (download, extract audio, transcribe, analyze topics, create video segments, upload to S3).

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response Example:**
```json
{
  "message": "YouTube video processed successfully. Audio chunked into 9 parts (original size: 79.73MB)",
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "chunk_files": [
    "output/chunk_001_audio.mp3",
    "output/chunk_002_audio.mp3"
  ],
  "total_chunks": 9,
  "video_segments": [
    "video_segments/01_Introduction_and_Audio_Check.mp4",
    "video_segments/02_Discussion_on_Props_and_Event_Handling.mp4"
  ],
  "total_video_segments": 32,
  "segments_json_path": "segments.json",
  "s3_urls": [
    {
      "filename": "01_Introduction_and_Audio_Check.mp4",
      "s3_url": "https://lisa-research.s3.ap-south-1.amazonaws.com/video-segments/20241201_143022_01_Introduction_and_Audio_Check.mp4",
      "s3_key": "video-segments/20241201_143022_01_Introduction_and_Audio_Check.mp4",
      "size_mb": 15.2
    }
  ],
  "processing_time_seconds": 477.5
}
```

**Request:**

- Content-Type: `multipart/form-data`
- Body:
  - Key: `video_file` (type: File)
  - Value: Select your video file

**Response Example:**

```json
{
  "message": "Audio extracted and chunked into 9 parts (original size: 79.73MB)",
  "audio_file_path": null,
  "chunk_files": [
    "output/chunk_001_audio.mp3",
    "output/chunk_002_audio.mp3",
    "output/chunk_003_audio.mp3"
  ],
  "total_chunks": 9,
  "video_segments": [
    "video_segments/01_Introduction_and_Audio_Check.mp4",
    "video_segments/02_Discussion_on_Props_and_Event_Handling.mp4",
    "video_segments/03_Understanding_Prop_Drilling.mp4"
  ],
  "total_video_segments": 32,
  "segments_json_path": "segments.json",
  "s3_urls": [
    {
      "filename": "01_Introduction_and_Audio_Check.mp4",
      "s3_url": "https://lisa-research.s3.ap-south-1.amazonaws.com/video-segments/20241201_143022_01_Introduction_and_Audio_Check.mp4",
      "s3_key": "video-segments/20241201_143022_01_Introduction_and_Audio_Check.mp4",
      "size_mb": 15.2
    },
    {
      "filename": "02_Discussion_on_Props_and_Event_Handling.mp4",
      "s3_url": "https://lisa-research.s3.ap-south-1.amazonaws.com/video-segments/20241201_143022_02_Discussion_on_Props_and_Event_Handling.mp4",
      "s3_key": "video-segments/20241201_143022_02_Discussion_on_Props_and_Event_Handling.mp4",
      "size_mb": 22.8
    }
  ]
}
```

### 3. Download Audio File

**GET** `/download/{filename}`

Download an extracted audio file or chunk.

### 4. List Audio Files

**GET** `/files/`

List all extracted audio files with their sizes.

### 5. Delete Audio File

**DELETE** `/files/{filename}`

Delete a specific audio file.

### 6. Delete All Audio Files

**DELETE** `/files/`

Delete all extracted audio files.

### 7. List Video Segments

**GET** `/video-segments/`

List all video segments with their details including topic titles, timestamps, and file sizes.

**Response Example:**

```json
{
  "video_segments": [
    {
      "filename": "01_Introduction_and_Audio_Check.mp4",
      "title": "Introduction and Audio Check",
      "start_time": 224.0,
      "end_time": 378.0,
      "duration": 154.0,
      "size_mb": 15.2
    },
    {
      "filename": "02_Discussion_on_Props_and_Event_Handling.mp4",
      "title": "Discussion on Props and Event Handling",
      "start_time": 386.0,
      "end_time": 584.0,
      "duration": 198.0,
      "size_mb": 22.8
    }
  ],
  "total_segments": 32
}
```

### 8. Download Video Segment

**GET** `/download-video/{filename}`

Download a specific video segment file.

### 9. Manual Cleanup

**POST** `/cleanup`

Manually trigger cleanup of remnant files from previous processing runs.

**Response Example:**

```json
{
  "message": "Cleanup completed successfully",
  "files_cleaned": 11,
  "status": "success"
}
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# OpenAI API Key (required for transcription)
OPENAI_API_KEY=your_openai_api_key_here

# S3 Configuration (required for video segment upload)
S3_ACCESS_KEY=your_s3_access_key_here
S3_SECRET_KEY=your_s3_secret_key_here
S3_BUCKET_NAME=lisa-research
S3_REGION=ap-south-1
```

**Note:** The S3 credentials you provided will be used to upload video segments to the `lisa-research` bucket in the `ap-south-1` region.

### Application Settings

You can modify the following constants in `main.py`:

- `MAX_AUDIO_SIZE_MB`: Maximum audio file size before chunking (default: 25MB)
- `CHUNK_DURATION_MINUTES`: Duration of each chunk in minutes (default: 10 minutes)

### FFmpeg Settings

The audio extraction uses FFmpeg with the following settings:

- Audio Codec: MP3
- Bitrate: 192k
- Sample Rate: 44100 Hz

You can modify these settings in the `extract_audio` function in `main.py`.

## Testing with Postman

1. **Extract Audio (Full Pipeline):**

   - Method: POST
   - URL: `http://localhost:8000/extract-audio/`
   - Body: form-data
   - Key: `video_file` (type: File)
   - Value: Select your video file

2. **Process YouTube Video (Full Pipeline):**

   - Method: POST
   - URL: `http://localhost:8000/process-youtube`
   - Body: raw (JSON)
   - Content-Type: `application/json`
   - Body:
     ```json
     {
       "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
     }
     ```

3. **Download Audio File:**

   - Method: GET
   - URL: `http://localhost:8000/download/{filename}`

3. **List Audio Files:**

   - Method: GET
   - URL: `http://localhost:8000/files/`

4. **List Video Segments:**

   - Method: GET
   - URL: `http://localhost:8000/video-segments/`

5. **Download Video Segment:**

   - Method: GET
   - URL: `http://localhost:8000/download-video/{filename}`

6. **Manual Cleanup:**

   - Method: POST
   - URL: `http://localhost:8000/cleanup`

## Directory Structure

```
Script_trimmerrr/
├── venv/                 # Virtual environment
├── uploads/              # Temporary video uploads (auto-cleaned)
├── output/               # Extracted audio files and chunks
├── video_segments/       # Extracted video segments
├── main.py              # Main API application
├── transcribe_segments.py # Transcription and topic analysis
├── extract_video_segments.py # Video segment extraction
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Supported Video Formats

The API supports all video formats that FFmpeg supports, including:

- MP4, AVI, MOV, MKV, WMV, FLV
- WebM, 3GP, M4V, TS, MTS
- And many more formats supported by FFmpeg

FFmpeg provides excellent format compatibility and high-quality audio extraction.

## Supported YouTube URL Formats

The API supports various YouTube URL formats:

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`

The system automatically downloads the best available quality and processes it through the complete pipeline.

## Error Handling

The API includes comprehensive error handling:

- Invalid file type validation
- File processing error handling
- Automatic cleanup of temporary files
- Proper HTTP status codes and error messages
- Graceful handling of transcription and video extraction failures

## Notes

- The API automatically cleans up uploaded video files after processing
- Large audio files (>25MB) are automatically chunked and the original is deleted
- All audio files are saved in MP3 format
- Video segments are saved in MP4 format
- File names include UUIDs to prevent conflicts
- Transcription requires a valid OpenAI API key
- Video segment extraction requires the original video file to be available
- **Automatic cleanup** runs at the start of each new processing request
- **Final cleanup** removes local video segments after successful S3 upload
- **Manual cleanup** endpoint available for maintenance
- **Final state:** Only S3 URLs remain; all local files are cleaned up

## Performance

**Recent Test Results:**

- **Input:** 90-minute video (2GB)
- **Processing Time:** 477 seconds (~8 minutes)
- **Audio Extraction:** 79.73MB
- **Audio Chunks:** 9 chunks (10 minutes each)
- **Video Segments:** 32 segments created successfully
- **Success Rate:** 100% (32/32 segments extracted successfully)
