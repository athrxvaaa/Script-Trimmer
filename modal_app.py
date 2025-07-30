import modal
import os
import sys
import logging
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydub import AudioSegment
import subprocess
import boto3
from botocore.exceptions import ClientError
import yt_dlp
import re
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This ensures logs go to stdout/stderr for Modal
    ]
)
logger = logging.getLogger(__name__)

# Create Modal app
app = modal.App("script-trimmer")

# Define the image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements(
    "requirements_modal.txt"
).apt_install(
    "ffmpeg",  # For video processing
    "git",     # For yt-dlp
    "curl",    # For downloads
    "wget"     # Alternative downloader
).add_local_file("transcribe_segments.py", "/root/transcribe_segments.py").add_local_file("extract_video_segments.py", "/root/extract_video_segments.py")

# Create a volume for persistent storage
volume = modal.Volume.from_name("script-trimmer-storage", create_if_missing=True)

# Create a secret for API keys
secret = modal.Secret.from_name("script-trimmer-secrets")

# Configuration
UPLOAD_DIR = Path("/data/uploads")
OUTPUT_DIR = Path("/data/output")
VIDEO_SEGMENTS_DIR = Path("/data/video_segments")
MAX_AUDIO_SIZE_MB = 25
CHUNK_DURATION_MINUTES = 10

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "lisa-research")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

# Pydantic models
class AudioExtractionResponse(BaseModel):
    message: str
    audio_file_path: Optional[str] = None
    chunk_files: Optional[List[str]] = None
    total_chunks: Optional[int] = None
    video_segments: Optional[List[str]] = None
    total_video_segments: Optional[int] = None
    interaction_segments: Optional[List[str]] = None
    total_interaction_segments: Optional[int] = None
    segments_json_path: Optional[str] = None
    s3_urls: Optional[List[dict]] = None

class YouTubeProcessRequest(BaseModel):
    youtube_url: str

class YouTubeProcessResponse(BaseModel):
    message: str
    youtube_url: str
    audio_file_path: Optional[str] = None
    chunk_files: Optional[List[str]] = None
    total_chunks: Optional[int] = None
    video_segments: Optional[List[str]] = None
    total_video_segments: Optional[int] = None
    interaction_segments: Optional[List[str]] = None
    total_interaction_segments: Optional[int] = None
    segments_json_path: Optional[str] = None
    s3_urls: Optional[List[dict]] = None
    processing_time_seconds: float

# Helper functions
def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    return file_path.stat().st_size / (1024 * 1024)

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
        
        # Determine if this is an interaction segment based on path
        if "interactions" in str(segment_file):
            s3_key = f"video-segments/interactions/{timestamp}_{segment_file.name}"
            segment_type = "interaction"
        else:
            s3_key = f"video-segments/topics/{timestamp}_{segment_file.name}"
            segment_type = "topic"
        
        s3_url = upload_file_to_s3(segment_file, s3_key)
        if s3_url:
            s3_urls.append({
                "filename": segment_file.name,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "size_mb": get_file_size_mb(segment_file),
                "segment_type": segment_type
            })
            logger.info(f"✅ Uploaded {segment_type} segment: {segment_file.name}")
        else:
            logger.error(f"❌ Failed to upload {segment_file.name} to S3")
    
    logger.info(f"✅ S3 upload completed: {len(s3_urls)}/{len(video_segments)} segments uploaded")
    return s3_urls

def is_valid_youtube_url(url: str) -> bool:
    """Check if the URL is a valid YouTube URL"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

def download_youtube_video(youtube_url: str, output_dir: Path) -> Optional[Path]:
    """Download YouTube video and return the file path"""
    try:
        logger.info(f"📥 Starting YouTube video download: {youtube_url}")
        
        # Generate a unique filename to avoid conflicts
        file_id = str(uuid.uuid4())
        output_filename = f"{file_id}_youtube_video.%(ext)s"
        
        # Try multiple strategies for downloading
        strategies = [
            # Strategy 1: Standard approach with enhanced headers
            {
                'format': 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best[ext=webm]/best',
                'outtmpl': str(output_dir / output_filename),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'no_color': True,
                'nocheckcertificate': True,
                'progress_hooks': [lambda d: logger.info(f"📥 Download progress: {d.get('_percent_str', 'N/A')}") if d['status'] == 'downloading' else None],
                'format_sort': ['res:720', 'ext:mp4:m4a', 'hasvid', 'hasaud'],
                'format_sort_force': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'no_check_certificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip,deflate',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                'extractor_retries': 3,
                'fragment_retries': 3,
                'retries': 3,
                'file_access_retries': 3,
                'sleep_interval': 1,
                'max_sleep_interval': 5,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web', 'android', 'mweb'],
                        'player_skip': ['webpage', 'configs'],
                        'skip': ['dash', 'hls'],
                    }
                }
            },
            # Strategy 2: More aggressive approach with different user agent
            {
                'format': 'best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best',
                'outtmpl': str(output_dir / output_filename),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'no_color': True,
                'nocheckcertificate': True,
                'progress_hooks': [lambda d: logger.info(f"📥 Download progress: {d.get('_percent_str', 'N/A')}") if d['status'] == 'downloading' else None],
                'format_sort': ['res:480', 'ext:mp4:m4a', 'hasvid', 'hasaud'],
                'format_sort_force': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'no_check_certificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                },
                'extractor_retries': 5,
                'fragment_retries': 5,
                'retries': 5,
                'file_access_retries': 5,
                'sleep_interval': 2,
                'max_sleep_interval': 10,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web', 'android', 'mweb'],
                        'player_skip': ['webpage', 'configs'],
                        'skip': ['dash', 'hls'],
                    }
                }
            },
            # Strategy 3: Minimal approach for restricted videos
            {
                'format': 'worst[ext=mp4]/worst[ext=webm]/worst',
                'outtmpl': str(output_dir / output_filename),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'no_color': True,
                'nocheckcertificate': True,
                'progress_hooks': [lambda d: logger.info(f"📥 Download progress: {d.get('_percent_str', 'N/A')}") if d['status'] == 'downloading' else None],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
                'extractor_retries': 2,
                'fragment_retries': 2,
                'retries': 2,
                'file_access_retries': 2,
                'sleep_interval': 3,
                'max_sleep_interval': 15,
            }
        ]
        
        for i, strategy in enumerate(strategies, 1):
            logger.info(f"🔄 Trying download strategy {i}/{len(strategies)}...")
            
            try:
                with yt_dlp.YoutubeDL(strategy) as ydl:
                    # Get video info first
                    logger.info("🔍 Fetching video information...")
                    try:
                        info = ydl.extract_info(youtube_url, download=False)
                        video_title = info.get('title', 'Unknown Title')
                        duration = info.get('duration', 0)
                        
                        logger.info(f"📹 Video Title: {video_title}")
                        logger.info(f"⏱️  Duration: {duration} seconds")
                        
                        # Check if video is downloadable
                        formats = info.get('formats', [])
                        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('vcodec') is not None]
                        
                        # Filter out image-only formats (like thumbnails)
                        video_formats = [f for f in video_formats if f.get('format_id') != 'sb0' and not f.get('format_note', '').startswith('storyboard')]
                        
                        if not video_formats:
                            logger.error("❌ No video formats available for download")
                            continue
                        
                        logger.info(f"✅ Found {len(video_formats)} video formats available")
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Could not fetch video info: {e}")
                        video_title = "Unknown Title"
                        duration = 0
                    
                    # Download the video
                    logger.info("⬇️  Downloading video...")
                    try:
                        ydl.download([youtube_url])
                        
                        # Find the downloaded file
                        logger.info("🔍 Searching for downloaded video file...")
                        
                        # First, try to find files with our unique ID
                        downloaded_files = list(output_dir.glob(f"{file_id}_youtube_video.*"))
                        logger.info(f"📁 Found {len(downloaded_files)} files with unique ID")
                        
                        if not downloaded_files:
                            # Try to find any video files that were recently created in output_dir
                            video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v', '.3gp']
                            all_files = []
                            for ext in video_extensions:
                                all_files.extend(list(output_dir.glob(f"*{ext}")))
                            
                            # Sort by modification time (newest first)
                            downloaded_files = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)
                            logger.info(f"📁 Found {len(downloaded_files)} potential video files in {output_dir}")
                        
                        if downloaded_files:
                            video_path = downloaded_files[0]
                            file_size_mb = get_file_size_mb(video_path)
                            logger.info(f"✅ YouTube video downloaded successfully: {video_path.name} ({file_size_mb:.2f}MB)")
                            return video_path
                        else:
                            logger.error("❌ No video files found after download")
                            continue
                            
                    except Exception as download_error:
                        error_msg = str(download_error)
                        if "Sign in to confirm you're not a bot" in error_msg:
                            logger.warning(f"⚠️  Strategy {i} failed due to bot detection, trying next strategy...")
                            continue
                        elif "Video unavailable" in error_msg:
                            logger.error("❌ Video is unavailable or private")
                            raise Exception("Video is unavailable or private. Please check the URL and try again.")
                        else:
                            logger.warning(f"⚠️  Strategy {i} failed: {error_msg}")
                            continue
                            
            except Exception as e:
                logger.warning(f"⚠️  Strategy {i} failed completely: {str(e)}")
                continue
        
        # If all strategies failed
        logger.error("❌ All download strategies failed")
        raise Exception("All download strategies failed. This video may be restricted or require authentication.")
                
    except Exception as e:
        logger.error(f"❌ Error downloading YouTube video: {str(e)}")
        return None

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
    import sys
    sys.path.append("/root")
    import extract_video_segments
    
    logger.info("🎬 Starting video segment extraction...")
    
    try:
        # Run video segment extraction with the provided video path
        success = extract_video_segments.create_video_segments(str(video_path))
        
        if not success:
            logger.error("❌ Video segment extraction failed")
            return []
        
        # Get list of created video segments (both regular and interaction segments)
        video_segments = []
        interaction_segments = []
        
        # Get regular segments from main video_segments directory (current working directory)
        video_segments_dir = Path("video_segments")
        if video_segments_dir.exists():
            for file_path in video_segments_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    video_segments.append(str(file_path))
        
        # Get interaction segments from interactions subdirectory
        interaction_dir = video_segments_dir / "interactions"
        if interaction_dir.exists():
            for file_path in interaction_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                    interaction_segments.append(str(file_path))
        
        # Combine all segments
        all_segments = video_segments + interaction_segments
        
        logger.info(f"✅ Video segment extraction completed!")
        logger.info(f"📚 Regular topic segments: {len(video_segments)}")
        logger.info(f"💬 Interaction segments: {len(interaction_segments)}")
        logger.info(f"📊 Total segments: {len(all_segments)}")
        
        return all_segments
        
    except Exception as e:
        logger.error(f"❌ Error during video segment extraction: {str(e)}")
        return []

# Main processing functions
def process_video_file(video_path: Path, filename: str) -> dict:
    """Process uploaded video file through the complete pipeline"""
    import sys
    sys.path.append("/root")
    import transcribe_segments
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 NEW VIDEO UPLOAD REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.info(f"📁 Original filename: {filename}")
    logger.info(f"🆔 Request ID: {start_time.strftime('%Y%m%d_%H%M%S')}")
    
    # Clean up remnant files from previous runs
    cleanup_previous_files()
    
    try:
        # Get video file size
        video_size_mb = get_file_size_mb(video_path)
        logger.info(f"✅ Video file ready: {video_size_mb:.2f}MB")
        
        # Extract audio using ffmpeg
        logger.info("🎵 Starting audio extraction from video...")
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
            file_id = str(uuid.uuid4())
            audio_filename = f"{file_id}_audio.mp3"
            audio_path = OUTPUT_DIR / audio_filename
            logger.info(f"📄 Audio will be saved as: {audio_filename}")
            
            # Extract audio using FFmpeg
            logger.info("⚡ Extracting audio using FFmpeg...")
            cmd_copy = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',
                '-acodec', 'mp3',
                '-ab', '192k',
                '-y',
                str(audio_path)
            ]
            result_copy = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result_copy.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
                logger.error(f"❌ FFmpeg extraction failed: {result_copy.stderr}")
                raise Exception(f"FFmpeg error: {result_copy.stderr}")
            
            # Get extracted audio file size
            audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Audio extraction completed successfully: {audio_size_mb:.2f}MB")
            
        except Exception as e:
            logger.error(f"❌ Error extracting audio: {str(e)}")
            raise Exception(f"Error extracting audio: {str(e)}")
        
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
                all_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Separate regular segments from interaction segments
                video_segments = []
                interaction_segments = []
                
                for segment_path in all_segments:
                    segment_file = Path(segment_path)
                    if "interactions" in str(segment_file):
                        interaction_segments.append(segment_path)
                    else:
                        video_segments.append(segment_path)
                
                # Clean up intermediate files after successful video segment extraction
                if all_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []
                interaction_segments = []

            # Upload video segments to S3
            s3_urls = []
            if all_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(all_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"✂️  Created {len(chunk_files)} chunks")
            logger.info(f"🎬 Created {len(video_segments)} regular video segments")
            logger.info(f"💬 Created {len(interaction_segments)} interaction segments")
            logger.info(f"☁️  Uploaded {len(s3_urls)} segments to S3")
            logger.info("=" * 60)
            
            return {
                "message": f"Audio extracted and chunked into {len(chunk_files)} parts (original size: {audio_size_mb:.2f}MB)",
                "chunk_files": chunk_files,
                "total_chunks": len(chunk_files),
                "video_segments": video_segments,
                "total_video_segments": len(video_segments),
                "interaction_segments": interaction_segments,
                "total_interaction_segments": len(interaction_segments),
                "segments_json_path": "segments.json",
                "s3_urls": s3_urls
            }
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
                all_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Separate regular segments from interaction segments
                video_segments = []
                interaction_segments = []
                
                for segment_path in all_segments:
                    segment_file = Path(segment_path)
                    if "interactions" in str(segment_file):
                        interaction_segments.append(segment_path)
                    else:
                        video_segments.append(segment_path)
                
                # Clean up intermediate files after successful video segment extraction
                if all_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []
                interaction_segments = []

            # Upload video segments to S3
            s3_urls = []
            if all_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(all_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"🎬 Created {len(video_segments)} regular video segments")
            logger.info(f"💬 Created {len(interaction_segments)} interaction segments")
            logger.info(f"☁️  Uploaded {len(s3_urls)} segments to S3")
            logger.info("=" * 60)
            
            return {
                "message": f"Audio extracted successfully (size: {audio_size_mb:.2f}MB)",
                "audio_file_path": str(audio_path),
                "video_segments": video_segments,
                "total_video_segments": len(video_segments),
                "interaction_segments": interaction_segments,
                "total_interaction_segments": len(interaction_segments),
                "segments_json_path": "segments.json",
                "s3_urls": s3_urls
            }
    
    except Exception as e:
        logger.error(f"❌ Error processing video: {str(e)}")
        # Clean up files on error
        if video_path.exists():
            logger.info("🗑️  Cleaning up video file due to error...")
            video_path.unlink()
        if 'audio_path' in locals() and audio_path.exists():
            logger.info("🗑️  Cleaning up audio file due to error...")
            audio_path.unlink()
        raise Exception(f"Error processing video: {str(e)}")

def process_youtube_video(youtube_url: str) -> dict:
    """Process YouTube video through the complete pipeline"""
    import sys
    sys.path.append("/root")
    import transcribe_segments
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 NEW YOUTUBE VIDEO PROCESSING REQUEST")
    logger.info("=" * 60)
    logger.info(f"📺 YouTube URL: {youtube_url}")
    logger.info(f"🆔 Request ID: {start_time.strftime('%Y%m%d_%H%M%S')}")
    
    # Clean up remnant files from previous runs
    cleanup_previous_files()
    
    # Validate YouTube URL
    if not is_valid_youtube_url(youtube_url):
        raise Exception("Invalid YouTube URL provided")
    
    try:
        # Download YouTube video
        video_path = download_youtube_video(youtube_url, UPLOAD_DIR)
        if not video_path:
            raise Exception("Failed to download YouTube video - download returned None")
        if not video_path.exists():
            raise Exception("Failed to download YouTube video - file not found after download")
        
        # Get video file size
        video_size_mb = get_file_size_mb(video_path)
        logger.info(f"✅ Video file ready: {video_size_mb:.2f}MB")
        
        # Extract audio using ffmpeg
        logger.info("🎵 Starting audio extraction from YouTube video...")
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
            
            file_id = str(uuid.uuid4())
            audio_filename = f"{file_id}_youtube_audio.mp3"
            audio_path = OUTPUT_DIR / audio_filename
            logger.info(f"📄 Audio will be saved as: {audio_filename}")
            
            # Extract audio using FFmpeg
            logger.info("⚡ Extracting audio using FFmpeg...")
            cmd_copy = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',
                '-acodec', 'mp3',
                '-ab', '192k',
                '-y',
                str(audio_path)
            ]
            result_copy = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result_copy.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
                logger.error(f"❌ FFmpeg extraction failed: {result_copy.stderr}")
                raise Exception(f"FFmpeg error: {result_copy.stderr}")
            
            # Get extracted audio file size
            audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Audio extraction completed successfully: {audio_size_mb:.2f}MB")
            
        except Exception as e:
            logger.error(f"❌ Error extracting audio: {str(e)}")
            raise Exception(f"Error extracting audio: {str(e)}")
        
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
                all_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Separate regular segments from interaction segments
                video_segments = []
                interaction_segments = []
                
                for segment_path in all_segments:
                    segment_file = Path(segment_path)
                    if "interactions" in str(segment_file):
                        interaction_segments.append(segment_path)
                    else:
                        video_segments.append(segment_path)
                
                # Clean up intermediate files after successful video segment extraction
                if all_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []
                interaction_segments = []

            # Upload video segments to S3
            s3_urls = []
            if all_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(all_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 YOUTUBE VIDEO PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"✂️  Created {len(chunk_files)} chunks")
            logger.info(f"🎬 Created {len(video_segments)} regular video segments")
            logger.info(f"💬 Created {len(interaction_segments)} interaction segments")
            logger.info(f"☁️  Uploaded {len(s3_urls)} segments to S3")
            logger.info("=" * 60)
            
            return {
                "message": f"YouTube video processed successfully. Audio chunked into {len(chunk_files)} parts (original size: {audio_size_mb:.2f}MB)",
                "youtube_url": youtube_url,
                "chunk_files": chunk_files,
                "total_chunks": len(chunk_files),
                "video_segments": video_segments,
                "total_video_segments": len(video_segments),
                "interaction_segments": interaction_segments,
                "total_interaction_segments": len(interaction_segments),
                "segments_json_path": "segments.json",
                "s3_urls": s3_urls,
                "processing_time_seconds": processing_time
            }
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
                all_segments = run_video_segment_extraction(video_path)
                logger.info("✅ Video segment extraction completed!")
                
                # Separate regular segments from interaction segments
                video_segments = []
                interaction_segments = []
                
                for segment_path in all_segments:
                    segment_file = Path(segment_path)
                    if "interactions" in str(segment_file):
                        interaction_segments.append(segment_path)
                    else:
                        video_segments.append(segment_path)
                
                # Clean up intermediate files after successful video segment extraction
                if all_segments:
                    cleanup_intermediate_files(video_path, audio_path)
                else:
                    logger.warning("⚠️  No video segments created, keeping intermediate files for debugging")
                    
            except Exception as e:
                logger.error(f"❌ Error during video segment extraction after transcription: {str(e)}")
                video_segments = []
                interaction_segments = []

            # Upload video segments to S3
            s3_urls = []
            if all_segments:
                logger.info("☁️  Starting S3 upload for video segments...")
                s3_urls = upload_video_segments_to_s3(all_segments)
                logger.info(f"✅ S3 upload completed: {len(s3_urls)} segments uploaded")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info("🎉 YOUTUBE VIDEO PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
            logger.info(f"📊 Original video size: {video_size_mb:.2f}MB")
            logger.info(f"🎵 Extracted audio size: {audio_size_mb:.2f}MB")
            logger.info(f"🎬 Created {len(video_segments)} regular video segments")
            logger.info(f"💬 Created {len(interaction_segments)} interaction segments")
            logger.info(f"☁️  Uploaded {len(s3_urls)} segments to S3")
            logger.info("=" * 60)
            
            return {
                "message": f"YouTube video processed successfully (audio size: {audio_size_mb:.2f}MB)",
                "youtube_url": youtube_url,
                "audio_file_path": str(audio_path),
                "video_segments": video_segments,
                "total_video_segments": len(video_segments),
                "interaction_segments": interaction_segments,
                "total_interaction_segments": len(interaction_segments),
                "segments_json_path": "segments.json",
                "s3_urls": s3_urls,
                "processing_time_seconds": processing_time
            }
    
    except Exception as e:
        logger.error(f"❌ Error processing YouTube video: {str(e)}")
        # Clean up files on error
        if 'video_path' in locals() and video_path is not None and video_path.exists():
            logger.info("🗑️  Cleaning up video file due to error...")
            video_path.unlink()
        if 'audio_path' in locals() and audio_path is not None and audio_path.exists():
            logger.info("🗑️  Cleaning up audio file due to error...")
            audio_path.unlink()
        raise Exception(f"Error processing YouTube video: {str(e)}")

# Web endpoints
@app.function(
    image=image,
    cpu=4.0,  # 4 CPU cores for heavy video processing
    memory=8192,  # 8GB RAM for large file handling
    timeout=7200,  # 2 hours timeout for large file processing
    volumes={"/data": volume},
    secrets=[secret]
)
@modal.fastapi_endpoint(method="POST")
async def extract_audio_endpoint(video_file: UploadFile = File(...)):
    """Extract audio from uploaded video file and process through pipeline"""
    print("🚀 extract_audio_endpoint called")
    print(f"📁 Received file: {video_file.filename}")
    
    # Validate file type
    allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.3gp']
    file_extension = Path(video_file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Please upload a video file. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (limit to 2GB for large videos)
    content = await video_file.read()
    file_size_mb = len(content) / (1024 * 1024)
    print(f"📊 File size: {file_size_mb:.2f} MB")
    
    if file_size_mb > 2048:  # 2GB limit
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size_mb:.2f}MB). Maximum size is 2GB. Please compress your video or use a smaller file."
        )
    
    # Add progress logging for large files
    if file_size_mb > 100:
        print(f"⚠️  Large file detected ({file_size_mb:.2f}MB). This may take some time to process...")
    
    await video_file.seek(0)  # Reset file pointer after reading
    
    try:
        # Create directories
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        
        print("📂 Directories created successfully")
        
        # Save uploaded file with streaming for large files
        file_id = str(uuid.uuid4())
        video_filename = f"{file_id}_{video_file.filename}"
        video_path = UPLOAD_DIR / video_filename
        
        # Use streaming for large files
        if file_size_mb > 100:
            print(f"📤 Streaming large file to disk...")
            with open(video_path, "wb") as f:
                while chunk := await video_file.read(8192):  # 8KB chunks
                    f.write(chunk)
        else:
            # For smaller files, write directly
            content = await video_file.read()
            with open(video_path, "wb") as f:
                f.write(content)
        
        print(f"💾 File saved: {video_filename}")
        logger.info(f"📁 Saved uploaded file: {video_filename}")
        
        # Process the video file
        print("🔄 Starting video processing...")
        result = process_video_file(video_path, video_file.filename)
        
        print("✅ Processing completed successfully")
        return AudioExtractionResponse(**result)
        
    except Exception as e:
        print(f"❌ Error in extract_audio_endpoint: {str(e)}")
        logger.error(f"❌ Error in extract_audio_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

@app.function(
    image=image,
    cpu=4.0,  # 4 CPU cores for heavy video processing
    memory=8192,  # 8GB RAM for large file handling
    timeout=3600,  # 1 hour timeout for processing
    volumes={"/data": volume},
    secrets=[secret]
)
@modal.fastapi_endpoint(method="POST")
async def process_youtube_endpoint(request: YouTubeProcessRequest):
    """Process YouTube video URL through the complete pipeline"""
    print("🚀 process_youtube_endpoint called")
    print(f"📺 YouTube URL: {request.youtube_url}")
    
    try:
        # Create directories
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        
        print("📂 Directories created successfully")
        
        # Process the YouTube video
        print("🔄 Starting YouTube video processing...")
        result = process_youtube_video(request.youtube_url)
        
        print("✅ YouTube processing completed successfully")
        return YouTubeProcessResponse(**result)
        
    except Exception as e:
        print(f"❌ Error in process_youtube_endpoint: {str(e)}")
        logger.error(f"❌ Error in process_youtube_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing YouTube video: {str(e)}")