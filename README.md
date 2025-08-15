# 🎬 Lisa - AI Video Processing Platform

**Transform long videos into organized, searchable segments using AI**

Lisa automatically analyzes your videos, extracts meaningful topics, and creates downloadable segments. Perfect for educational content, live sessions, and recorded lectures.

## 🚀 Live Demo

**Frontend**: https://video-processor-frontend-ijkl54wfg-atharvas-projects-edc46cc8.vercel.app

## ✨ Features

### 🎥 **Smart Video Processing**

- **Topic-based Segmentation** - AI identifies and segments by topics
- **Interaction Detection** - Finds Q&A sessions and student interactions
- **Live vs Recorded** - Different processing for live sessions vs recorded videos
- **YouTube Support** - Process YouTube videos directly (with optional cookies)

### 📁 **Multiple Input Sources**

- **File Upload** - Drag & drop video files (up to 10GB)
- **S3 URLs** - Process videos already in S3
- **YouTube URLs** - Direct YouTube video processing
- **Live Streams** - Support for YouTube live streams

### 🎯 **Smart Organization**

- **Topic Segments** - Organized by content topics
- **Interaction Segments** - Q&A and student interaction moments
- **Download All** - Download all segments as ZIP files
- **Local Storage** - Results persist for 24 hours

## 🏗️ Architecture

### Frontend (Vercel)

- **Modern UI** - Clean, responsive design with Lisa branding
- **Real-time Progress** - Live progress tracking
- **Video Previews** - Embedded video players
- **Drag & Drop** - Intuitive file upload

### Backend (Modal)

- **AI Processing** - GPT-4 for topic analysis and interaction detection
- **Unified Pipeline** - Same processing for S3 and YouTube videos
- **Real-time Updates** - Modal Queue for progress tracking
- **High Performance** - 16GB RAM, 4 CPU cores, 4-hour timeout

## 📡 API Endpoints

### 1. Get Presigned URL

```
POST https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run
```

Generate S3 upload URLs for direct file uploads.

### 2. Process Video

```
POST https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run
```

Process videos from S3 URLs or YouTube URLs.

### 3. Progress Stream

```
GET https://lu-labs--script-trimmer-progress-stream-endpoint.modal.run
```

Real-time progress updates via Server-Sent Events.

## 🎯 How to Use

### Step 1: Choose Your Input

- **Upload File**: Drag & drop a video file
- **S3 URL**: Paste an S3 video URL
- **YouTube URL**: Paste a YouTube video URL

### Step 2: Select Video Type

- **Live Session**: Includes topic segments + interaction segments
- **Recorded Video**: Topic segments only

### Step 3: Process

- Click "Process Video"
- Watch real-time progress
- View results with video previews
- Download all segments as ZIP

## 🔧 Recent Updates

### ✅ **YouTube Integration**

- Direct YouTube video processing
- Support for live streams and regular videos
- Optional cookies for age-restricted content
- Unified pipeline (same processing as S3 videos)

### ✅ **Enhanced AI Processing**

- Increased max_tokens to 2048 (prevents truncated responses)
- Better JSON parsing and error handling
- Improved topic and interaction detection
- 2-minute timeout with retry logic

### ✅ **Improved UI**

- Modern drag & drop interface
- URL type detection (S3 vs YouTube)
- Optional cookies input for YouTube
- Better progress tracking and error messages

### ✅ **Unified Pipeline**

- Single processing function for all video types
- Consistent chunking and segmentation
- Same quality for S3 and YouTube videos
- Simplified maintenance

## 🚀 Quick Start

1. **Visit**: https://video-processor-frontend-ijkl54wfg-atharvas-projects-edc46cc8.vercel.app
2. **Upload** a video file or paste a YouTube/S3 URL
3. **Select** video type (Live Session or Recorded Video)
4. **Process** and wait for AI analysis
5. **Download** organized video segments

## 📊 Processing Pipeline

```
Video Input (File/S3/YouTube)
    ↓
Download & Audio Extraction
    ↓
AI Transcription (Whisper)
    ↓
Topic Analysis (GPT-4)
    ↓
Interaction Detection (GPT-4) [Live sessions only]
    ↓
Video Segmentation (FFmpeg)
    ↓
S3 Upload & Results
```

## 🔧 Technical Details

### Supported Formats

- **Video**: MP4, AVI, MOV, MKV, WebM, FLV, WMV
- **Audio**: MP3 (extracted from video)
- **Size**: Up to 10GB per file

### AI Models

- **Transcription**: OpenAI Whisper API
- **Topic Analysis**: GPT-4 (gpt-4o-mini)
- **Interaction Detection**: GPT-4 (gpt-4o-mini)

### Performance

- **Processing Time**: 2-10 minutes (depends on video length)
- **Chunking**: 10-minute audio chunks for large files
- **Timeout**: 2 minutes per AI call with retry logic
- **Max Tokens**: 2048 for complete responses

## 🛠️ Development

### Backend Deployment

```bash
modal deploy modal_app.py
```

### Frontend Deployment

```bash
vercel --prod
```

### Environment Setup

```bash
# Modal secrets for AWS and OpenAI
modal secret create script-trimmer-secrets
modal secret create youtube-cookies
```

## 📁 Project Structure

```
├── modal_app.py              # Main Modal FastAPI app
├── index.html               # Frontend application
├── transcribe_segments.py   # AI transcription & analysis
├── extract_video_segments.py # Video segmentation
├── requirements_modal.txt   # Dependencies
└── README.md               # This file
```

## 🎯 Use Cases

- **Educational Content**: Segment lectures by topics
- **Live Sessions**: Extract Q&A and interaction moments
- **Training Videos**: Organize content by subject
- **YouTube Content**: Process YouTube videos directly
- **Research**: Analyze video content structure

## 🔒 Security & Privacy

- **No Data Storage**: Videos processed and deleted
- **Secure Uploads**: Presigned S3 URLs
- **API Keys**: Stored in Modal secrets
- **CORS**: Proper cross-origin configuration

---

**Built with**: FastAPI, Modal, OpenAI, AWS S3, Vercel  
**Last Updated**: December 2024  
**Version**: 2.0.0
