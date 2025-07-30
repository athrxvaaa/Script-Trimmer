#!/usr/bin/env python3
"""
Example client for the unified Modal endpoint.
This shows how to interact with the single endpoint for all functionality.
"""

import requests
import json
import base64

# Replace with your Modal endpoint URL after deployment
MODAL_ENDPOINT_URL = "https://your-modal-endpoint-url.modal.run"

def health_check():
    """Check if the API is healthy"""
    payload = {"type": "health"}
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

def process_youtube_video(youtube_url: str):
    """Process a YouTube video URL"""
    payload = {
        "type": "youtube",
        "youtube_url": youtube_url
    }
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

def upload_video_file(file_path: str):
    """Upload and process a video file"""
    # Read file and encode as base64
    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    payload = {
        "type": "upload",
        "file_data": file_data,
        "filename": file_path.split("/")[-1]  # Get filename from path
    }
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

def list_video_segments():
    """List all video segments"""
    payload = {"type": "list_segments"}
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

def download_file(filename: str, file_type: str = "video"):
    """Download a file"""
    payload = {
        "type": "download",
        "filename": filename,
        "file_type": file_type
    }
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

def cleanup_files():
    """Manual cleanup"""
    payload = {"type": "cleanup"}
    response = requests.post(MODAL_ENDPOINT_URL, json=payload)
    return response.json()

# Example usage
if __name__ == "__main__":
    print("=== Unified Modal Endpoint Client Example ===\n")
    
    # 1. Health check
    print("1. Health Check:")
    try:
        health = health_check()
        print(f"   Status: {health}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 2. Process YouTube video
    print("2. Process YouTube Video:")
    try:
        youtube_result = process_youtube_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print(f"   Result: {json.dumps(youtube_result, indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 3. Upload video file (example)
    print("3. Upload Video File:")
    print("   (Uncomment and modify the file path to test)")
    # try:
    #     upload_result = upload_video_file("/path/to/your/video.mp4")
    #     print(f"   Result: {json.dumps(upload_result, indent=2)}")
    # except Exception as e:
    #     print(f"   Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 4. List segments
    print("4. List Video Segments:")
    try:
        segments = list_video_segments()
        print(f"   Result: {json.dumps(segments, indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 5. Cleanup
    print("5. Cleanup:")
    try:
        cleanup_result = cleanup_files()
        print(f"   Result: {cleanup_result}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n=== End of Example ===") 