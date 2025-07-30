import os
import json
import subprocess
import re
from pathlib import Path

# Configuration
SEGMENTS_JSON = "segments.json"
INTERACTION_SEGMENTS_JSON = "interaction_segments.json"
OUTPUT_DIR = "video_segments"
INTERACTION_OUTPUT_DIR = "video_segments/interactions"  # Subfolder for interactions
ORIGINAL_VIDEO = None  # Will be auto-detected

def sanitize_filename(filename):
    """Convert topic title to a valid filename"""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces 
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename

def find_original_video():
    """Find the original video file in the uploads directory"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    
    # Look in uploads directory first
    uploads_dir = Path('uploads')
    if uploads_dir.exists():
        for file in uploads_dir.iterdir():
            if file.is_file() and any(file.name.lower().endswith(ext) for ext in video_extensions):
                return str(file)
    
    # Fallback to current directory
    for file in os.listdir('.'):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            return file
    
    return None

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def extract_video_segment(video_path, start_time, duration, output_path, topic_title):
    """Extract a video segment using ffmpeg"""
    
    # Format times for ffmpeg
    start_str = format_time(start_time)
    duration_str = format_time(duration)
    end_str = format_time(start_time + duration)
    
    print(f"Extracting: {topic_title}")
    print(f"  Time: {start_str} - {end_str} (Duration: {duration_str})")
    print(f"  Output: {output_path}")
    
    try:
        # Use proper quoting for file paths with spaces
        cmd = [
            'ffmpeg',
            '-i', video_path,  # ffmpeg handles spaces automatically
            '-ss', start_str,
            '-t', duration_str,
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  ✅ Successfully extracted: {output_path}")
        return True, None
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error extracting {output_path}: {e}")
        return False, e.stderr

def create_video_segments(video_path=None):
    """Main function to create video segments from segments.json"""
    
    # Check if segments.json exists
    if not os.path.exists(SEGMENTS_JSON):
        print(f"❌ {SEGMENTS_JSON} not found!")
        return False
    
    # Find original video
    global ORIGINAL_VIDEO
    if video_path:
        ORIGINAL_VIDEO = video_path
    else:
        ORIGINAL_VIDEO = find_original_video()
    
    if not ORIGINAL_VIDEO:
        print("❌ No video file found in uploads/ directory or current directory!")
        print("Supported formats: .mp4, .avi, .mov, .mkv, .webm, .flv, .wmv")
        return False
    
    print(f"📹 Found original video: {ORIGINAL_VIDEO}")
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INTERACTION_OUTPUT_DIR, exist_ok=True)
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"💬 Interaction directory: {INTERACTION_OUTPUT_DIR}")
    
    # Load segments
    with open(SEGMENTS_JSON, 'r') as f:
        segments = json.load(f)
    
    print(f"📋 Found {len(segments)} segments to extract")
    
    # Separate regular segments and interaction segments
    regular_segments = []
    interaction_segments = []
    
    for segment in segments:
        if segment.get('segment_type') == 'interaction':
            interaction_segments.append(segment)
        else:
            regular_segments.append(segment)
    
    print(f"📚 Regular topic segments: {len(regular_segments)}")
    print(f"💬 Interaction segments: {len(interaction_segments)}")
    
    # Extract regular segments
    successful_extractions = 0
    failed_extractions = 0
    interaction_extractions = 0
    interaction_failures = 0
    
    # Process regular segments
    for i, segment in enumerate(regular_segments, 1):
        topic_title = segment.get('title', f'Unknown_Topic_{i}')
        start_time = segment.get('start_time', 0)
        end_time = segment.get('end_time', 0)
        
        # Validate timestamps
        if start_time >= end_time:
            print(f"⚠️  Skipping regular segment {i}: Invalid timestamps ({start_time} >= {end_time})")
            failed_extractions += 1
            continue
        
        # Create filename
        sanitized_title = sanitize_filename(topic_title)
        output_filename = f"{i:02d}_{sanitized_title}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Extract segment
        success, error = extract_video_segment(ORIGINAL_VIDEO, start_time, end_time - start_time, output_path, topic_title)
        if success:
            successful_extractions += 1
        else:
            failed_extractions += 1
            if error:
                print(f"  Error output: {error}")
        
        print()  # Empty line for readability
    
    # Process interaction segments
    for i, segment in enumerate(interaction_segments, 1):
        topic_title = segment.get('title', f'Unknown_Interaction_{i}')
        start_time = segment.get('start_time', 0)
        end_time = segment.get('end_time', 0)
        interaction_type = segment.get('interaction_type', 'Unknown')
        
        # Validate timestamps
        if start_time >= end_time:
            print(f"⚠️  Skipping interaction segment {i}: Invalid timestamps ({start_time} >= {end_time})")
            interaction_failures += 1
            continue
        
        # Create filename with interaction type
        sanitized_title = sanitize_filename(topic_title)
        output_filename = f"{i:02d}_{interaction_type}_{sanitized_title}.mp4"
        output_path = os.path.join(INTERACTION_OUTPUT_DIR, output_filename)
        
        # Extract segment
        success, error = extract_video_segment(ORIGINAL_VIDEO, start_time, end_time - start_time, output_path, f"{topic_title} ({interaction_type})")
        if success:
            interaction_extractions += 1
        else:
            interaction_failures += 1
            if error:
                print(f"  Error output: {error}")
        
        print()  # Empty line for readability
    
    # Summary
    print("=" * 50)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"✅ Successful regular extractions: {successful_extractions}")
    print(f"❌ Failed regular extractions: {failed_extractions}")
    print(f"💬 Successful interaction extractions: {interaction_extractions}")
    print(f"❌ Failed interaction extractions: {interaction_failures}")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"💬 Interaction directory: {INTERACTION_OUTPUT_DIR}")
    
    total_successful = successful_extractions + interaction_extractions
    if total_successful > 0:
        print(f"\n🎉 Successfully extracted {total_successful} video segments!")
        print(f"📂 Check the '{OUTPUT_DIR}' folder for regular topic segments.")
        print(f"💬 Check the '{INTERACTION_OUTPUT_DIR}' folder for interaction segments.")
        return True
    else:
        print("❌ No video segments were successfully extracted.")
        return False

def list_segments():
    """List all segments from segments.json"""
    if not os.path.exists(SEGMENTS_JSON):
        print(f"❌ {SEGMENTS_JSON} not found!")
        return
    
    with open(SEGMENTS_JSON, 'r') as f:
        segments = json.load(f)
    
    # Separate regular segments and interaction segments
    regular_segments = []
    interaction_segments = []
    
    for segment in segments:
        if segment.get('segment_type') == 'interaction':
            interaction_segments.append(segment)
        else:
            regular_segments.append(segment)
    
    print(f"📋 Found {len(segments)} total segments:")
    print(f"📚 Regular topic segments: {len(regular_segments)}")
    print(f"💬 Interaction segments: {len(interaction_segments)}")
    print("=" * 80)
    
    # List regular segments
    if regular_segments:
        print("\n📚 REGULAR TOPIC SEGMENTS:")
        print("-" * 40)
        for i, segment in enumerate(regular_segments, 1):
            topic_title = segment.get('title', f'Unknown_Topic_{i}')
            start_time = segment.get('start_time', 0)
            end_time = segment.get('end_time', 0)
            chunk_number = segment.get('chunk_number', 'N/A')
            
            start_str = format_time(start_time)
            end_str = format_time(end_time)
            duration = end_time - start_time
            duration_str = format_time(duration)
            
            print(f"{i:2d}. {topic_title}")
            print(f"    Time: {start_str} - {end_str} (Duration: {duration_str})")
            print(f"    Chunk: {chunk_number}")
            print()
    
    # List interaction segments
    if interaction_segments:
        print("\n💬 SPEAKER-STUDENT INTERACTION SEGMENTS:")
        print("-" * 40)
        for i, segment in enumerate(interaction_segments, 1):
            topic_title = segment.get('title', f'Unknown_Interaction_{i}')
            start_time = segment.get('start_time', 0)
            end_time = segment.get('end_time', 0)
            chunk_number = segment.get('chunk_number', 'N/A')
            interaction_type = segment.get('interaction_type', 'Unknown')
            
            start_str = format_time(start_time)
            end_str = format_time(end_time)
            duration = end_time - start_time
            duration_str = format_time(duration)
            
            print(f"{i:2d}. {topic_title} ({interaction_type})")
            print(f"    Time: {start_str} - {end_str} (Duration: {duration_str})")
            print(f"    Chunk: {chunk_number}")
            print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_segments()
        elif sys.argv[1] == "extract":
            create_video_segments()
        else:
            print("Usage:")
            print("  python extract_video_segments.py list    - List all segments")
            print("  python extract_video_segments.py extract - Extract video segments")
    else:
        print("🎬 Video Segment Extractor")
        print("=" * 30)
        print("This script extracts video segments from your original video based on")
        print("the timestamps in segments.json and names them using topic titles.")
        print()
        print("NEW: Now also extracts speaker-student interaction segments!")
        print("Regular topic segments go to: video_segments/")
        print("Interaction segments go to: video_segments/interactions/")
        print()
        print("Usage:")
        print("  python extract_video_segments.py list    - List all segments")
        print("  python extract_video_segments.py extract - Extract video segments")
        print()
        print("Requirements:")
        print("  - ffmpeg must be installed")
        print("  - Original video file in uploads/ directory")
        print("  - segments.json file (generated by transcribe_segments.py)") 