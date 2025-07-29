import os
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydub import AudioSegment
import tempfile
import uuid
import sys
import boto3
from botocore.exceptions import ClientError
sys.path.append(str(Path(__file__).parent))
import transcribe_segments
import extract_video_segments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Extraction API", description="Extract audio from video files, transcribe, and create video segments")

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
VIDEO_SEGMENTS_DIR = Path("video_segments")
MAX_AUDIO_SIZE_MB = 25
CHUNK_DURATION_MINUTES = 10  # Duration of each chunk in minutes

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
VIDEO_SEGMENTS_DIR.mkdir(exist_ok=True)

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "lisa-research")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

def get_s3_client():
    """Get S3 client with credentials from environment variables"""
    if not S3_ACCESS_KEY or not S3_SECRET_KEY:
        logger.warning("⚠️  S3 credentials not found in environment variables")
        return None
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION
        )
        return s3_client
    except Exception as e:
        logger.error(f"❌ Failed to create S3 client: {e}")
        return None

def upload_file_to_s3(file_path: Path, s3_key: str) -> Optional[str]:
    """Upload a file to S3 and return the URL"""
    s3_client = get_s3_client()
    if not s3_client:
        logger.error("❌ S3 client not available")
        return None
    
    try:
        logger.info(f"📤 Uploading {file_path.name} to S3...")
        s3_client.upload_file(
            str(file_path),
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        
        # Generate the S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"✅ Successfully uploaded to S3: {s3_url}")
        return s3_url
        
    except ClientError as e:
        logger.error(f"❌ S3 upload failed for {file_path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error during S3 upload: {e}")
        return None

def upload_video_segments_to_s3(video_segments: List[str]) -> List[dict]:
    """Upload all video segments to S3 and return their URLs"""
    s3_urls = []
    
    if not video_segments:
        logger.warning("⚠️  No video segments to upload")
        return s3_urls
    
    logger.info(f"🚀 Starting S3 upload for {len(video_segments)} video segments...")
    
    for segment_path in video_segments:
        segment_file = Path(segment_path)
        if not segment_file.exists():
            logger.warning(f"⚠️  Video segment not found: {segment_path}")
            continue
        
        # Create S3 key with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"video-segments/{timestamp}_{segment_file.name}"
        
        s3_url = upload_file_to_s3(segment_file, s3_key)
        if s3_url:
            s3_urls.append({
                "filename": segment_file.name,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "size_mb": get_file_size_mb(segment_file)
            })
        else:
            logger.error(f"❌ Failed to upload {segment_file.name} to S3")
    
    logger.info(f"✅ S3 upload completed: {len(s3_urls)}/{len(video_segments)} segments uploaded")
    return s3_urls

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Audio Extraction API is running",
        "endpoints": {
            "extract_audio": "/extract-audio",
            "download": "/download/{filename}",
            "list_files": "/files",
            "delete_file": "/files/{filename}",
            "delete_all": "/files",
            "list_video_segments": "/video-segments",
            "download_video_segment": "/download-video/{filename}",
            "cleanup": "/cleanup",
            "logs": "/logs",
            "docs": "/docs"
        }
    }

@app.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent logs from the API"""
    try:
        with open('api.log', 'r') as f:
            lines = f.readlines()
            # Return the last 'limit' lines
            recent_logs = lines[-limit:] if len(lines) > limit else lines
            return {
                "total_lines": len(lines),
                "returned_lines": len(recent_logs),
                "logs": recent_logs
            }
    except FileNotFoundError:
        return {"error": "Log file not found", "logs": []}

class AudioExtractionResponse(BaseModel):
    message: str
    audio_file_path: Optional[str] = None
    chunk_files: Optional[List[str]] = None
    total_chunks: Optional[int] = None
    video_segments: Optional[List[str]] = None
    total_video_segments: Optional[int] = None
    segments_json_path: Optional[str] = None
    s3_urls: Optional[List[dict]] = None

class VideoSegmentResponse(BaseModel):
    filename: str
    title: str
    start_time: float
    end_time: float
    duration: float
    size_mb: float

def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    return file_path.stat().st_size / (1024 * 1024)

def cleanup_previous_files():
    """Clean up remnant files from previous processing runs"""
    logger.info("🧹 Cleaning up remnant files from previous runs...")
    
    files_to_clean = [
        "transcriptions.json",
        "segments.json", 
        "processing_status.json"
    ]
    
    cleaned_count = 0
    for filename in files_to_clean:
        file_path = Path(filename)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"🗑️  Deleted remnant file: {filename}")
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Could not delete {filename}: {e}")
    
    # Clean up empty directories
    directories_to_clean = [OUTPUT_DIR, VIDEO_SEGMENTS_DIR]
    for directory in directories_to_clean:
        if directory.exists():
            try:
                # Remove all files in directories
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        logger.info(f"🗑️  Deleted remnant file: {file_path}")
                        cleaned_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Could not clean directory {directory}: {e}")
    
    if cleaned_count > 0:
        logger.info(f"✅ Cleaned up {cleaned_count} remnant files")
    else:
        logger.info("✅ No remnant files found to clean")
    
    return cleaned_count

def cleanup_intermediate_files(video_path: Path, audio_path: Path = None):
    """Clean up intermediate files after video segment extraction is complete"""
    logger.info("🧹 Cleaning up intermediate files after video segment extraction...")
    
    cleaned_count = 0
    
    # Clean up intermediate JSON files
    intermediate_files = ["transcriptions.json", "segments.json"]
    for filename in intermediate_files:
        file_path = Path(filename)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"🗑️  Deleted intermediate file: {filename}")
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Could not delete {filename}: {e}")
    
    # Clean up audio chunks in output directory
    if OUTPUT_DIR.exists():
        try:
            for file_path in OUTPUT_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.aac', '.wav']:
                    file_path.unlink()
                    logger.info(f"🗑️  Deleted audio file: {file_path.name}")
                    cleaned_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Could not clean audio files: {e}")
    
    # Clean up original video file
    if video_path.exists():
        try:
            video_path.unlink()
            logger.info(f"🗑️  Deleted original video file: {video_path.name}")
            cleaned_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Could not delete video file: {e}")
    
    # Clean up original audio file if it exists
    if audio_path and audio_path.exists():
        try:
            audio_path.unlink()
            logger.info(f"🗑️  Deleted original audio file: {audio_path.name}")
            cleaned_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Could not delete audio file: {e}")
    
    logger.info(f"✅ Cleaned up {cleaned_count} intermediate files")
    return cleaned_count

def run_video_segment_extraction(video_path: Path) -> List[str]:
    """Run video segment extraction and return list of created video segments"""
    logger.info("🎬 Starting video segment extraction...")
    
    try:
        # Run video segment extraction with the provided video path
        success = extract_video_segments.create_video_segments(str(video_path))
        
        if not success:
            logger.error("❌ Video segment extraction failed")
            return []
        
        # Get list of created video segments
        video_segments = []
        if VIDEO_SEGMENTS_DIR.exists():
            for file_path in VIDEO_SEGMENTS_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    video_segments.append(str(file_path))
        
        logger.info(f"✅ Video segment extraction completed! Created {len(video_segments)} segments")
        return video_segments
        
    except Exception as e:
        logger.error(f"❌ Error during video segment extraction: {str(e)}")
        return []

def chunk_audio(audio_path: Path, output_dir: Path, chunk_duration_minutes: int = 10) -> List[str]:
    """Split audio file into chunks"""
    logger.info(f"🎵 Starting audio chunking process for: {audio_path}")
    
    try:
        audio = AudioSegment.from_file(str(audio_path))
        logger.info(f"✅ Audio file loaded successfully. Duration: {len(audio)/1000/60:.2f} minutes")
        
        # Convert minutes to milliseconds
        chunk_duration_ms = chunk_duration_minutes * 60 * 1000
        logger.info(f"📏 Chunk duration set to: {chunk_duration_minutes} minutes ({chunk_duration_ms}ms)")
        
        chunk_files = []
        total_duration = len(audio)
        total_chunks = (total_duration + chunk_duration_ms - 1) // chunk_duration_ms
        
        logger.info(f"📊 Total duration: {total_duration/1000/60:.2f} minutes")
        logger.info(f"🔢 Expected chunks: {total_chunks}")
        
        for i, start_time in enumerate(range(0, total_duration, chunk_duration_ms)):
            end_time = min(start_time + chunk_duration_ms, total_duration)
            chunk = audio[start_time:end_time]
            
            chunk_filename = f"chunk_{i+1:03d}_{audio_path.stem}.mp3"
            chunk_path = output_dir / chunk_filename
            
            logger.info(f"✂️  Creating chunk {i+1}/{total_chunks}: {chunk_filename}")
            logger.info(f"   ⏱️  Time range: {start_time/1000/60:.2f} - {end_time/1000/60:.2f} minutes")
            
            chunk.export(str(chunk_path), format="mp3")
            
            # Get chunk file size
            chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
            logger.info(f"   💾 Chunk size: {chunk_size_mb:.2f}MB")
            
            chunk_files.append(str(chunk_path))
        
        logger.info(f"✅ Audio chunking completed successfully! Created {len(chunk_files)} chunks")
        return chunk_files
        
    except Exception as e:
        logger.error(f"❌ Error during audio chunking: {str(e)}")
        raise

@app.post("/extract-audio", response_model=AudioExtractionResponse)
@app.post("/extract-audio/", response_model=AudioExtractionResponse)
async def extract_audio(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...)
):
    """
    Extract audio from uploaded video file and chunk if necessary
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 NEW VIDEO UPLOAD REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.info(f"📁 Original filename: {video_file.filename}")
    logger.info(f"📋 Content type: {video_file.content_type}")
    logger.info(f"🆔 Request ID: {start_time.strftime('%Y%m%d_%H%M%S')}")
    
    # Clean up remnant files from previous runs
    cleanup_previous_files()
    
    # Validate file upload
    if not video_file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Validate file type
    if not video_file.content_type:
        logger.error("❌ Could not determine file type")
        raise HTTPException(status_code=400, detail="Could not determine file type")
    
    # Accept both video/* and specific video formats
    video_types = ['video/', 'application/octet-stream']  # Some clients send octet-stream
    if not any(video_file.content_type.startswith(vt) for vt in video_types):
        # Also check file extension as fallback
        if not video_file.filename or not any(video_file.filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']):
            logger.error(f"❌ Invalid file type: {video_file.content_type}")
            raise HTTPException(status_code=400, detail=f"File must be a video. Received: {video_file.content_type}")
    
    logger.info(f"✅ File validation passed")
    
    # Create unique filename
    file_id = str(uuid.uuid4())
    video_filename = f"{file_id}_{video_file.filename}"
    video_path = UPLOAD_DIR / video_filename
    logger.info(f"🆔 Generated file ID: {file_id}")
    logger.info(f"📂 Video will be saved as: {video_filename}")
    
    try:
        # Save uploaded video file
        logger.info("💾 Starting video file upload...")
        async with aiofiles.open(video_path, 'wb') as f:
            content = await video_file.read()
            if not content:
                logger.error("❌ Empty file uploaded")
                raise HTTPException(status_code=400, detail="Empty file uploaded")
            await f.write(content)
        
        # Get video file size
        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Video file saved successfully: {video_size_mb:.2f}MB")
        logger.info(f"📂 Video path: {video_path}")
        
        # Extract audio using ffmpeg (stream copy only, no fallback)
        logger.info("🎵 Starting audio extraction process...")
        try:
            # First, probe the input file to get the audio codec
            logger.info("🔍 Probing video file for audio codec...")
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            audio_codec = probe_result.stdout.strip()
            logger.info(f"🎼 Detected audio codec: {audio_codec}")
            
            # Map codec to extension
            codec_ext = {'aac': 'aac', 'mp3': 'mp3', 'wav': 'wav', 'flac': 'flac', 'opus': 'opus', 'm4a': 'm4a', 'ogg': 'ogg'}
            out_ext = codec_ext.get(audio_codec, 'audio')
            audio_filename = f"{file_id}_audio.{out_ext}"
            audio_path = OUTPUT_DIR / audio_filename
            logger.info(f"📄 Audio will be saved as: {audio_filename}")
            
            # Try stream copy only
            logger.info("⚡ Extracting audio using FFmpeg (stream copy)...")
            cmd_copy = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',
                '-acodec', 'copy',
                '-y',
                str(audio_path)
            ]
            result_copy = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result_copy.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
                logger.error(f"❌ FFmpeg extraction failed: {result_copy.stderr}")
                raise HTTPException(status_code=500, detail=f"FFmpeg error: {result_copy.stderr}")
            
            # Get extracted audio file size
            audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Audio extraction completed successfully: {audio_size_mb:.2f}MB")
            logger.info(f"📂 Audio path: {audio_path}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error extracting audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error extracting audio: {str(e)}")
        
        # Check if audio file needs chunking
        audio_size_mb = get_file_size_mb(audio_path)
        logger.info(f"📊 Audio file size: {audio_size_mb:.2f}MB (max before chunking: {MAX_AUDIO_SIZE_MB}MB)")
        
        if audio_size_mb > MAX_AUDIO_SIZE_MB:
            logger.info(f"✂️  Audio file exceeds {MAX_AUDIO_SIZE_MB}MB, starting chunking process...")
            # Create chunks
            chunk_files = chunk_audio(audio_path, OUTPUT_DIR, CHUNK_DURATION_MINUTES)
            
            # Clean up original large audio file
            logger.info("🗑️  Cleaning up original large audio file...")
            audio_path.unlink()
            logger.info("✅ Original audio file deleted")
            
            # After chunking, run transcription and topic analysis
            logger.info("📝 Starting transcription and topic analysis...")
            try:
                audio_files = transcribe_segments.transcribe_audio_segments(output_dir=str(OUTPUT_DIR))
                logger.info("✅ Transcription completed. Now analyzing topics...")
                segment_json = transcribe_segments.create_segment_json(audio_files)
                with open("segments.json", "w") as f:
                    import json
                    json.dump(segment_json, f, indent=2)
                logger.info("✅ Topic analysis and segment creation completed!")
            except Exception as e:
                logger.error(f"❌ Error during transcription or topic analysis: {str(e)}")
            
            # Run video segment extraction after transcription
            logger.info("🎬 Starting video segment extraction after transcription...")
            try:
                video_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Clean up intermediate files after successful video segment extraction
                if video_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"✂️  Created {len(chunk_files)} chunks")
            logger.info(f"🎬 Created {len(video_segments)} video segments")
            logger.info(f"📁 Output directory: {OUTPUT_DIR}")
            logger.info(f"📁 Video segments directory: {VIDEO_SEGMENTS_DIR}")
            logger.info("=" * 60)
            
            # Upload video segments to S3
            s3_urls = []
            if video_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(video_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            return AudioExtractionResponse(
                message=f"Audio extracted and chunked into {len(chunk_files)} parts (original size: {audio_size_mb:.2f}MB)",
                chunk_files=chunk_files,
                total_chunks=len(chunk_files),
                video_segments=video_segments,
                total_video_segments=len(video_segments),
                segments_json_path="segments.json",
                s3_urls=s3_urls
            )
        else:
            logger.info(f"✅ Audio file is under {MAX_AUDIO_SIZE_MB}MB, no chunking needed")
            
            # After chunking, run transcription and topic analysis
            logger.info("📝 Starting transcription and topic analysis...")
            try:
                audio_files = transcribe_segments.transcribe_audio_segments(output_dir=str(OUTPUT_DIR))
                logger.info("✅ Transcription completed. Now analyzing topics...")
                segment_json = transcribe_segments.create_segment_json(audio_files)
                with open("segments.json", "w") as f:
                    import json
                    json.dump(segment_json, f, indent=2)
                logger.info("✅ Topic analysis and segment creation completed!")
            except Exception as e:
                logger.error(f"❌ Error during transcription or topic analysis: {str(e)}")

            # Run video segment extraction after transcription
            logger.info("🎬 Starting video segment extraction after transcription...")
            try:
                video_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Clean up intermediate files after successful video segment extraction
                if video_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"🎬 Created {len(video_segments)} video segments")
            logger.info(f"📁 Output directory: {OUTPUT_DIR}")
            logger.info("=" * 60)
            
            # Upload video segments to S3
            s3_urls = []
            if video_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(video_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            return AudioExtractionResponse(
                message=f"Audio extracted successfully (size: {audio_size_mb:.2f}MB)",
                audio_file_path=str(audio_path),
                video_segments=video_segments,
                total_video_segments=len(video_segments),
                segments_json_path="segments.json",
                s3_urls=s3_urls
            )
    
    except Exception as e:
        logger.error(f"❌ Error processing video: {str(e)}")
        # Clean up files on error
        if video_path.exists():
            logger.info("🗑️  Cleaning up video file due to error...")
            video_path.unlink()
        if 'audio_path' in locals() and audio_path.exists():
            logger.info("🗑️  Cleaning up audio file due to error...")
            audio_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
    
    # Note: Video file cleanup is now handled in cleanup_intermediate_files() after video segment extraction

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download extracted audio file or chunk"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='audio/mpeg'
    )

@app.get("/files/")
async def list_files():
    """List all extracted audio files"""
    files = []
    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix in ['.mp3', '.wav']:
            files.append({
                "filename": file_path.name,
                "size_mb": get_file_size_mb(file_path),
                "path": str(file_path)
            })
    return {"files": files}

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a specific audio file"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path.unlink()
    return {"message": f"File {filename} deleted successfully"}

@app.delete("/files/")
async def delete_all_files():
    """Delete all extracted audio files"""
    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix in ['.mp3', '.wav']:
            file_path.unlink()
    return {"message": "All audio files deleted successfully"}

@app.get("/video-segments/")
async def list_video_segments():
    """List all video segments with their details"""
    segments = []
    
    # Check if segments.json exists to get topic information
    segments_json_path = Path("segments.json")
    topic_info = {}
    if segments_json_path.exists():
        try:
            import json
            with open(segments_json_path, 'r') as f:
                segments_data = json.load(f)
                for i, segment in enumerate(segments_data, 1):
                    topic_info[f"{i:02d}"] = {
                        "title": segment.get('title', f'Unknown_Topic_{i}'),
                        "start_time": segment.get('start_time', 0),
                        "end_time": segment.get('end_time', 0)
                    }
        except Exception as e:
            logger.error(f"Error reading segments.json: {e}")
    
    # List video segments
    for file_path in VIDEO_SEGMENTS_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            # Extract segment number from filename (e.g., "01_Topic_Name.mp4" -> "01")
            filename = file_path.name
            segment_number = filename.split('_')[0] if '_' in filename else "unknown"
            
            # Get topic info
            topic_data = topic_info.get(segment_number, {})
            title = topic_data.get('title', filename.replace(file_path.suffix, ''))
            start_time = topic_data.get('start_time', 0)
            end_time = topic_data.get('end_time', 0)
            duration = end_time - start_time
            
            segments.append(VideoSegmentResponse(
                filename=filename,
                title=title,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                size_mb=get_file_size_mb(file_path)
            ))
    
    return {"video_segments": segments, "total_segments": len(segments)}

@app.get("/download-video/{filename}")
async def download_video_segment(filename: str):
    """Download a video segment"""
    file_path = VIDEO_SEGMENTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video segment not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='video/mp4'
    )

@app.post("/cleanup")
async def cleanup_files():
    """Manually trigger cleanup of remnant files"""
    try:
        cleaned_count = cleanup_previous_files()
        return {
            "message": f"Cleanup completed successfully",
            "files_cleaned": cleaned_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 