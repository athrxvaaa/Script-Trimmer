# Audio Extraction API

A FastAPI-based service that extracts audio from video files and automatically chunks large audio files into smaller segments.

## Features

- Extract audio from various video formats (MP4, AVI, MOV, etc.) using FFmpeg
- Automatic chunking of audio files larger than 25MB
- Configurable chunk duration (default: 10 minutes per chunk)
- File management endpoints (list, download, delete)
- Async file processing
- Automatic cleanup of temporary files
- High-quality audio extraction with configurable bitrate and sample rate

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

### 1. Extract Audio

**POST** `/extract-audio/`

Upload a video file to extract its audio. If the audio is larger than 25MB, it will be automatically chunked.

**Request:**

- Content-Type: `multipart/form-data`
- Body: video file

**Response:**

```json
{
  "message": "Audio extracted successfully (size: 15.23MB)",
  "audio_file_path": "output/uuid_audio.mp3",
  "chunk_files": null,
  "total_chunks": null
}
```

Or for chunked files:

```json
{
  "message": "Audio extracted and chunked into 3 parts (original size: 45.67MB)",
  "audio_file_path": null,
  "chunk_files": [
    "output/chunk_001_uuid_audio.mp3",
    "output/chunk_002_uuid_audio.mp3",
    "output/chunk_003_uuid_audio.mp3"
  ],
  "total_chunks": 3
}
```

### 2. Download File

**GET** `/download/{filename}`

Download an extracted audio file or chunk.

### 3. List Files

**GET** `/files/`

List all extracted audio files with their sizes.

### 4. Delete File

**DELETE** `/files/{filename}`

Delete a specific audio file.

### 5. Delete All Files

**DELETE** `/files/`

Delete all extracted audio files.

## Configuration

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

1. **Extract Audio:**

   - Method: POST
   - URL: `http://localhost:8000/extract-audio/`
   - Body: form-data
   - Key: `video_file` (type: File)
   - Value: Select your video file

2. **Download File:**

   - Method: GET
   - URL: `http://localhost:8000/download/{filename}`

3. **List Files:**

   - Method: GET
   - URL: `http://localhost:8000/files/`

4. **Delete File:**
   - Method: DELETE
   - URL: `http://localhost:8000/files/{filename}`

## Directory Structure

```
Script_trimmerrr/
├── venv/                 # Virtual environment
├── uploads/              # Temporary video uploads (auto-cleaned)
├── output/               # Extracted audio files
├── main.py              # Main API application
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Supported Video Formats

The API supports all video formats that FFmpeg supports, including:
- MP4, AVI, MOV, MKV, WMV, FLV
- WebM, 3GP, M4V, TS, MTS
- And many more formats supported by FFmpeg

FFmpeg provides excellent format compatibility and high-quality audio extraction.

## Error Handling

The API includes comprehensive error handling:

- Invalid file type validation
- File processing error handling
- Automatic cleanup of temporary files
- Proper HTTP status codes and error messages

## Notes

- The API automatically cleans up uploaded video files after processing
- Large audio files (>25MB) are automatically chunked and the original is deleted
- All audio files are saved in MP3 format
- File names include UUIDs to prevent conflicts
 