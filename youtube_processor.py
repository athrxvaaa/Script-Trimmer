#!/usr/bin/env python3
"""
YouTube Video Processor for Script Trimmer
==========================================

This script handles YouTube video downloads using yt-dlp with cookies
to avoid bot detection. It downloads videos locally and processes them
through the same pipeline as S3 videos.

Features:
- YouTube video download with yt-dlp
- Cookie-based authentication to avoid bot detection
- Support for user-provided cookies (fresh from browser)
- Same video processing pipeline as S3 videos
- No S3 upload - direct local processing

Usage:
    python youtube_processor.py <youtube_url>
    python youtube_processor.py --help
"""

import os
import sys
import json
import tempfile
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import argparse
import yt_dlp
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
VIDEO_SEGMENTS_DIR = Path("video_segments")
COOKIES_FILE = Path("cookies.txt")  # YouTube cookies file
MAX_FILE_SIZE_GB = 10

def validate_youtube_url(url: str) -> bool:
    """Validate if the URL is a valid YouTube URL"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+'
    ]
    
    import re
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

def create_cookies_file(cookies_content: str) -> Optional[Path]:
    """Create a temporary cookies file from user-provided content"""
    try:
        # Create a temporary cookies file
        cookies_file = Path("/tmp/youtube_cookies.txt")
        with open(cookies_file, 'w') as f:
            f.write(cookies_content)
        
        logger.info(f"✅ Created temporary cookies file: {cookies_file}")
        return cookies_file
        
    except Exception as e:
        logger.error(f"❌ Failed to create cookies file: {e}")
        return None

def get_video_info(url: str, cookies_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Get video information using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        # Add cookies if available
        if cookies_file and cookies_file.exists():
            ydl_opts['cookiefile'] = str(cookies_file)
            logger.info(f"Using cookies from: {cookies_file}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
            
    except Exception as e:
        logger.error(f"❌ Failed to get video info: {e}")
        return None

def download_youtube_video(url: str, output_path: Path, cookies_file: Optional[Path] = None) -> Optional[str]:
    """Download YouTube video using yt-dlp"""
    try:
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer MP4, fallback to best available
            'outtmpl': str(output_path),
            'quiet': False,
            'progress_hooks': [lambda d: logger.info(f"Download progress: {d.get('_percent_str', 'N/A')}") if d['status'] == 'downloading' else None],
        }
        
        # Add cookies if available
        if cookies_file and cookies_file.exists():
            ydl_opts['cookiefile'] = str(cookies_file)
            logger.info(f"Using cookies from: {cookies_file}")
        
        logger.info(f"🎬 Starting YouTube video download: {url}")
        logger.info(f"📁 Output path: {output_path}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Check if file was downloaded successfully
        if output_path.exists():
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Video downloaded successfully: {output_path.name} ({file_size_mb:.2f} MB)")
            return str(output_path)
        else:
            logger.error("❌ Video file not found after download")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to download YouTube video: {e}")
        return None

def process_youtube_video(youtube_url: str, cookies_file: Optional[Path] = None, cookies_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Main function to process YouTube video"""
    try:
        # Validate URL
        if not validate_youtube_url(youtube_url):
            logger.error("❌ Invalid YouTube URL")
            return None
        
        # Handle user-provided cookies
        temp_cookies_file = None
        if cookies_content:
            logger.info("🔐 Using user-provided cookies")
            temp_cookies_file = create_cookies_file(cookies_content)
            if temp_cookies_file:
                cookies_file = temp_cookies_file
        
        # Get video info
        logger.info("🔍 Getting video information...")
        video_info = get_video_info(youtube_url, cookies_file)
        if not video_info:
            logger.error("❌ Failed to get video information")
            return None
        
        # Extract video title and create safe filename
        video_title = video_info.get('title', 'youtube_video')
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.mp4"
        download_path = UPLOAD_DIR / filename
        
        # Download video
        logger.info(f"📥 Downloading video: {video_title}")
        downloaded_path = download_youtube_video(youtube_url, download_path, cookies_file)
        if not downloaded_path:
            logger.error("❌ Failed to download video")
            return None
        
        # Check file size
        file_size_mb = Path(downloaded_path).stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_GB * 1024:
            logger.error(f"❌ File too large: {file_size_mb:.2f} MB (max: {MAX_FILE_SIZE_GB} GB)")
            return None
        
        # Clean up temporary cookies file
        if temp_cookies_file and temp_cookies_file.exists():
            try:
                temp_cookies_file.unlink()
                logger.info("🧹 Cleaned up temporary cookies file")
            except Exception as e:
                logger.warning(f"⚠️  Failed to clean up temporary cookies file: {e}")
        
        # Return result for local processing
        result = {
            "youtube_url": youtube_url,
            "video_title": video_title,
            "local_file_path": downloaded_path,
            "filename": filename,
            "file_size_mb": file_size_mb,
            "status": "success",
            "message": "YouTube video downloaded successfully and ready for processing"
        }
        
        logger.info("✅ YouTube video download completed successfully")
        logger.info(f"📁 Video ready for processing: {downloaded_path}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing YouTube video: {e}")
        return None

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description="Process YouTube videos for Script Trimmer")
    parser.add_argument("youtube_url", help="YouTube video URL")
    parser.add_argument("--cookies", "-c", help="Path to cookies.txt file")
    parser.add_argument("--cookies-content", help="Cookies content as string (from browser export)")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create necessary directories
    UPLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    VIDEO_SEGMENTS_DIR.mkdir(exist_ok=True)
    
    # Process video
    cookies_path = Path(args.cookies) if args.cookies else COOKIES_FILE
    result = process_youtube_video(args.youtube_url, cookies_path, args.cookies_content)
    
    if result:
        print(json.dumps(result, indent=2))
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Result saved to: {args.output}")
    else:
        print("❌ Failed to process YouTube video")
        sys.exit(1)

if __name__ == "__main__":
    main()
