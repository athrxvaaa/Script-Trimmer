#!/usr/bin/env python3
"""
Test script for the integrated video processing pipeline
"""

import os
import sys
from pathlib import Path

def test_integration():
    """Test the integrated functionality"""
    print("🧪 Testing Integrated Video Processing Pipeline")
    print("=" * 50)
    
    # Check if all required files exist
    required_files = [
        "main.py",
        "transcribe_segments.py", 
        "extract_video_segments.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files found")
    
    # Check if directories exist or can be created
    directories = ["uploads", "output", "video_segments"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory '{directory}' ready")
    
    # Check if FFmpeg is available
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
        else:
            print("❌ FFmpeg is not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed")
        return False
    
    # Check if OpenAI API key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "sk-...":
        print("✅ OpenAI API key is set")
    else:
        print("⚠️  OpenAI API key not set (transcription will fail)")
    
    print("\n🎉 Integration test completed!")
    print("\nTo test the full pipeline:")
    print("1. Start the server: python main.py")
    print("2. Upload a video file to: http://localhost:8000/extract-audio/")
    print("3. Check the results at: http://localhost:8000/video-segments/")
    
    return True

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1) 