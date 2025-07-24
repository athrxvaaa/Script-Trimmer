#!/usr/bin/env python3
"""
Script Trimmer - Complete Video Processing Pipeline
==================================================

This script orchestrates the entire workflow:
1. Extract audio from video
2. Chunk large audio files
3. Transcribe audio chunks
4. Analyze topics and timestamps
5. Extract video segments based on topics

Usage:
    python script_trimmer.py <video_file>
    python script_trimmer.py --help
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# Import our existing modules
try:
    # We'll create these functions inline since they're not directly importable
    pass
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required files are in the same directory")
    sys.exit(1)

def extract_audio_from_video(video_path: str) -> Optional[str]:
    """Extract audio from video using ffmpeg"""
    try:
        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate output filename
        video_name = Path(video_path).stem
        audio_filename = f"{video_name}_audio.mp3"
        audio_path = output_dir / audio_filename
        
        # Extract audio using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'mp3',
            '-y',
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and audio_path.exists():
            return str(audio_path)
        else:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

def chunk_audio_file(audio_path: str) -> List[str]:
    """Chunk audio file into smaller pieces"""
    try:
        from pydub import AudioSegment
        
        output_dir = Path("output")
        audio = AudioSegment.from_file(audio_path)
        
        # Chunk duration: 10 minutes
        chunk_duration_ms = 10 * 60 * 1000
        
        chunk_files = []
        total_duration = len(audio)
        
        for i, start_time in enumerate(range(0, total_duration, chunk_duration_ms)):
            end_time = min(start_time + chunk_duration_ms, total_duration)
            chunk = audio[start_time:end_time]
            
            chunk_filename = f"chunk_{i+1:03d}_{Path(audio_path).stem}.mp3"
            chunk_path = output_dir / chunk_filename
            
            chunk.export(str(chunk_path), format="mp3")
            chunk_files.append(str(chunk_path))
        
        return chunk_files
        
    except Exception as e:
        print(f"Error chunking audio: {e}")
        return []

def transcribe_audio_files(audio_files: List[str]) -> bool:
    """Transcribe audio files using our existing transcribe_segments.py logic"""
    try:
        # Import the transcribe function from our existing file
        import transcribe_segments
        
        # Use the existing transcribe function
        success = transcribe_segments.transcribe_audio_segments()
        return success
        
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return False

def create_segment_json() -> bool:
    """Create segment JSON using our existing logic"""
    try:
        import transcribe_segments
        
        # Get audio files from output directory
        output_dir = Path("output")
        audio_files = []
        
        for file_path in output_dir.glob("*.mp3"):
            audio_files.append({
                "filename": file_path.name,
                "path": str(file_path)
            })
        
        # Use the existing create_segment_json function
        transcribe_segments.create_segment_json(audio_files)
        return True
        
    except Exception as e:
        print(f"Error creating segment JSON: {e}")
        return False

def extract_video_segments() -> bool:
    """Extract video segments using our existing logic"""
    try:
        import extract_video_segments
        
        # Use the existing create_video_segments function
        extract_video_segments.create_video_segments()
        return True
        
    except Exception as e:
        print(f"Error extracting video segments: {e}")
        return False

class ScriptTrimmer:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.video_name = Path(video_path).stem
        self.output_dir = "output"
        self.video_segments_dir = "video_segments"
        self.segments_json = "segments.json"
        self.transcriptions_json = "transcriptions.json"
        
        # Create necessary directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.video_segments_dir, exist_ok=True)
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print("\n" + "="*60)
        print(f"🎬 {title}")
        print("="*60)
    
    def print_step(self, step: str, description: str):
        """Print a step with description"""
        print(f"\n📋 Step {step}: {description}")
        print("-" * 40)
    
    def validate_video_file(self) -> bool:
        """Validate that the video file exists and is supported"""
        if not os.path.exists(self.video_path):
            print(f"❌ Video file not found: {self.video_path}")
            return False
            
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
        if not any(self.video_path.lower().endswith(ext) for ext in video_extensions):
            print(f"❌ Unsupported video format: {self.video_path}")
            print(f"Supported formats: {', '.join(video_extensions)}")
            return False
            
        print(f"✅ Video file validated: {self.video_path}")
        return True
    
    def cleanup_old_files(self):
        """Delete old transcription and segment files before processing new video"""
        print("\n🧹 Cleaning up old files...")
        
        # Files to delete
        files_to_delete = [
            self.transcriptions_json,
            self.segments_json
        ]
        
        deleted_count = 0
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️  Deleted: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Could not delete {file_path}: {e}")
        
        if deleted_count > 0:
            print(f"✅ Cleaned up {deleted_count} old file(s)")
        else:
            print("✅ No old files to clean up")
    
    def step1_extract_audio(self) -> Optional[str]:
        """Step 1: Extract audio from video"""
        self.print_step("1", "Extracting Audio from Video")
        
        try:
            # Extract audio using our function
            audio_path = extract_audio_from_video(self.video_path)
            if audio_path:
                print(f"✅ Audio extracted successfully: {audio_path}")
                return audio_path
            else:
                print("❌ Audio extraction failed")
                return None
        except Exception as e:
            print(f"❌ Error during audio extraction: {e}")
            return None
    
    def step2_chunk_audio(self, audio_path: str) -> List[str]:
        """Step 2: Chunk audio if it's too large"""
        self.print_step("2", "Chunking Audio (if needed)")
        
        try:
            # Check if chunking is needed
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            print(f"📊 Audio file size: {file_size:.1f} MB")
            
            if file_size > 25:
                print("📦 Audio file is large, chunking into smaller pieces...")
                chunked_files = chunk_audio_file(audio_path)
                print(f"✅ Created {len(chunked_files)} audio chunks")
                return chunked_files
            else:
                print("✅ Audio file is small enough, no chunking needed")
                return [audio_path]
        except Exception as e:
            print(f"❌ Error during audio chunking: {e}")
            return []
    
    def step3_transcribe_audio(self, audio_files: List[str]) -> bool:
        """Step 3: Transcribe audio files"""
        self.print_step("3", "Transcribing Audio with Whisper API")
        
        try:
            # Check if transcriptions already exist
            if os.path.exists(self.transcriptions_json):
                print("📁 Found existing transcriptions, loading...")
                return True
            
            print("🎤 Starting transcription with Whisper API...")
            success = transcribe_audio_files(audio_files)
            
            if success:
                print("✅ Transcription completed successfully")
                return True
            else:
                print("❌ Transcription failed")
                return False
        except Exception as e:
            print(f"❌ Error during transcription: {e}")
            return False
    
    def step4_analyze_topics(self) -> bool:
        """Step 4: Analyze topics and create segments"""
        self.print_step("4", "Analyzing Topics and Creating Segments")
        
        try:
            # Check if segments already exist
            if os.path.exists(self.segments_json):
                print("📁 Found existing segments, loading...")
                return True
            
            print("🧠 Analyzing topics with GPT-4o-mini...")
            success = create_segment_json()
            
            if success:
                print("✅ Topic analysis completed successfully")
                return True
            else:
                print("❌ Topic analysis failed")
                return False
        except Exception as e:
            print(f"❌ Error during topic analysis: {e}")
            return False
    
    def step5_extract_video_segments(self) -> bool:
        """Step 5: Extract video segments based on topics"""
        self.print_step("5", "Extracting Video Segments")
        
        try:
            # Check if video segments already exist
            if os.path.exists(self.video_segments_dir) and os.listdir(self.video_segments_dir):
                print("📁 Found existing video segments")
                return True
            
            print("🎬 Extracting video segments based on topics...")
            success = extract_video_segments()
            
            if success:
                print("✅ Video segments extracted successfully")
                return True
            else:
                print("❌ Video segment extraction failed")
                return False
        except Exception as e:
            print(f"❌ Error during video extraction: {e}")
            return False
    
    def print_summary(self):
        """Print a summary of the results"""
        self.print_header("Processing Complete!")
        
        # Count video segments
        if os.path.exists(self.video_segments_dir):
            video_files = [f for f in os.listdir(self.video_segments_dir) if f.endswith('.mp4')]
            print(f"📹 Video Segments Created: {len(video_files)}")
            
            if video_files:
                print("\n🎬 Generated Video Segments:")
                for i, file in enumerate(sorted(video_files), 1):
                    file_path = os.path.join(self.video_segments_dir, file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"  {i:2d}. {file} ({size_mb:.1f} MB)")
        
        # Show segments.json info
        if os.path.exists(self.segments_json):
            with open(self.segments_json, 'r') as f:
                segments = json.load(f)
            print(f"\n📊 Topics Analyzed: {len(segments)}")
            
            if segments:
                print("\n🏷️  Detected Topics:")
                for i, segment in enumerate(segments[:10], 1):  # Show first 10
                    topic = segment.get('topic', 'Unknown')
                    start = segment.get('start', '00:00')
                    end = segment.get('end', '00:00')
                    print(f"  {i:2d}. {topic} ({start}-{end})")
                
                if len(segments) > 10:
                    print(f"  ... and {len(segments) - 10} more topics")
        
        print(f"\n📁 Output Directory: {self.video_segments_dir}/")
        print(f"📄 Segments Data: {self.segments_json}")
        print(f"📝 Transcriptions: {self.transcriptions_json}")
        
        print("\n🎉 Script Trimmer processing complete!")
        print("You can now navigate to specific topics in your video segments!")
    
    def run_pipeline(self) -> bool:
        """Run the complete pipeline"""
        self.print_header("Script Trimmer - Video Processing Pipeline")
        print(f"🎬 Processing: {self.video_path}")
        print(f"📁 Output: {self.video_segments_dir}/")
        
        start_time = time.time()
        
        # Clean up old files before processing new video
        self.cleanup_old_files()
        
        # Step 1: Validate video file
        if not self.validate_video_file():
            return False
        
        # Step 2: Extract audio
        audio_path = self.step1_extract_audio()
        if not audio_path:
            return False
        
        # Step 3: Chunk audio if needed
        audio_files = self.step2_chunk_audio(audio_path)
        if not audio_files:
            return False
        
        # Step 4: Transcribe audio
        if not self.step3_transcribe_audio(audio_files):
            return False
        
        # Step 5: Analyze topics
        if not self.step4_analyze_topics():
            return False
        
        # Step 6: Extract video segments
        if not self.step5_extract_video_segments():
            return False
        
        # Print summary
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Total processing time: {elapsed_time/60:.1f} minutes")
        
        self.print_summary()
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Script Trimmer - Complete Video Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script_trimmer.py "lecture.mp4"
  python script_trimmer.py "Day 2 _ React Bootcamp.mp4"
  python script_trimmer.py --help
        """
    )
    
    parser.add_argument(
        "video_file",
        help="Path to the video file to process"
    )
    
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip processing if output files already exist"
    )
    
    args = parser.parse_args()
    
    # Create and run the pipeline
    trimmer = ScriptTrimmer(args.video_file)
    success = trimmer.run_pipeline()
    
    if success:
        print("\n✅ Pipeline completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 