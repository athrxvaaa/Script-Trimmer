#!/usr/bin/env python3
"""
Intermediate Script for S3 Upload and Video Processing
Handles the complete workflow: Upload to S3 -> Start Processing -> Poll for Results
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration
PRESIGNED_URL_ENDPOINT = "https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run"
EXTRACT_AUDIO_ENDPOINT = "https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run"
JOB_STATUS_ENDPOINT = "https://lu-labs--script-trimmer-job-status-endpoint.modal.run"

class VideoProcessor:
    def __init__(self):
        self.session = requests.Session()
    
    def get_presigned_url(self, filename: str, content_type: str = "video/mp4") -> Optional[Dict[str, Any]]:
        """Get presigned URL for S3 upload"""
        try:
            print(f"📤 Getting presigned URL for: {filename}")
            
            response = self.session.post(
                PRESIGNED_URL_ENDPOINT,
                json={
                    "filename": filename,
                    "content_type": content_type
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Presigned URL received: {data['s3_url']}")
                return data
            else:
                print(f"❌ Failed to get presigned URL: {response.status_code}")
                print(f"Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting presigned URL: {e}")
            return None
    
    def upload_to_s3(self, presigned_url: str, file_path: Path) -> bool:
        """Upload file to S3 using presigned URL"""
        try:
            print(f"☁️  Uploading {file_path.name} to S3...")
            
            with open(file_path, 'rb') as f:
                response = self.session.put(
                    presigned_url,
                    data=f,
                    headers={'Content-Type': 'video/mp4'},
                    timeout=300  # 5 minutes timeout for upload
                )
            
            if response.status_code == 200:
                print("✅ S3 upload completed successfully!")
                return True
            else:
                print(f"❌ S3 upload failed: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error uploading to S3: {e}")
            return False
    
    def start_processing_job(self, s3_url: str) -> Optional[str]:
        """Start video processing job and return job ID"""
        try:
            print(f"🚀 Starting processing job for: {s3_url}")
            
            response = self.session.post(
                EXTRACT_AUDIO_ENDPOINT,
                json={"s3_url": s3_url},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get('job_id')
                if job_id:
                    print(f"✅ Job started successfully! Job ID: {job_id}")
                    return job_id
                else:
                    print("❌ No job ID received")
                    return None
            else:
                print(f"❌ Failed to start job: {response.status_code}")
                print(f"Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error starting job: {e}")
            return None
    
    def poll_job_status(self, job_id: str, max_attempts: int = 180) -> Optional[Dict[str, Any]]:
        """Poll job status until completion"""
        print(f"📊 Polling job status for: {job_id}")
        print(f"⏱️  Max polling time: {max_attempts * 10} seconds ({max_attempts * 10 // 60} minutes)")
        
        for attempt in range(max_attempts):
            try:
                response = self.session.get(
                    f"{JOB_STATUS_ENDPOINT}?job_id={job_id}",
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    message = data.get('message', '')
                    progress = data.get('progress', 0)
                    
                    # Show progress
                    progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
                    print(f"📊 [{progress_bar}] {progress:.1f}% - {status.upper()}: {message}")
                    
                    if status == "completed":
                        print("✅ Processing completed successfully!")
                        return data.get('result')
                    elif status == "failed":
                        error = data.get('error', 'Unknown error')
                        print(f"❌ Processing failed: {error}")
                        return None
                    elif status in ["pending", "running"]:
                        # Continue polling
                        time.sleep(10)  # Wait 10 seconds before next poll
                    else:
                        print(f"⚠️  Unknown status: {status}")
                        time.sleep(10)
                        
                else:
                    print(f"❌ Failed to get job status: {response.status_code}")
                    print(f"Error: {response.text}")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Error polling job status: {e}")
                time.sleep(10)
        
        print("⏰ Polling timeout reached")
        return None
    
    def process_video_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Complete workflow: Upload to S3 -> Start Processing -> Poll for Results"""
        try:
            print("=" * 60)
            print("🎬 VIDEO PROCESSING WORKFLOW STARTED")
            print("=" * 60)
            print(f"📁 File: {file_path.name}")
            print(f"📏 Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
            print("=" * 60)
            
            # Step 1: Get presigned URL
            presigned_data = self.get_presigned_url(file_path.name)
            if not presigned_data:
                print("❌ Failed to get presigned URL")
                return None
            
            # Step 2: Upload to S3
            upload_success = self.upload_to_s3(presigned_data['presigned_url'], file_path)
            if not upload_success:
                print("❌ Failed to upload to S3")
                return None
            
            # Step 3: Start processing job
            job_id = self.start_processing_job(presigned_data['s3_url'])
            if not job_id:
                print("❌ Failed to start processing job")
                return None
            
            # Step 4: Poll for results
            result = self.poll_job_status(job_id)
            
            if result:
                print("=" * 60)
                print("🎉 PROCESSING COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"📊 Video Segments: {len(result.get('video_segments', []))}")
                print(f"💬 Interaction Segments: {len(result.get('interaction_segments', []))}")
                print(f"☁️  S3 URLs: {len(result.get('s3_urls', []))}")
                print("=" * 60)
                return result
            else:
                print("❌ Processing failed or timed out")
                return None
                
        except Exception as e:
            print(f"❌ Error in processing workflow: {e}")
            return None

def main():
    """Main function to run the video processing workflow"""
    if len(sys.argv) != 2:
        print("Usage: python upload_and_process.py <video_file_path>")
        print("Example: python upload_and_process.py /path/to/video.mp4")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.is_file():
        print(f"❌ Not a file: {file_path}")
        sys.exit(1)
    
    # Check file size (max 10GB)
    file_size_gb = file_path.stat().st_size / (1024*1024*1024)
    if file_size_gb > 10:
        print(f"❌ File too large: {file_size_gb:.2f} GB (max 10GB)")
        sys.exit(1)
    
    # Initialize processor and run workflow
    processor = VideoProcessor()
    result = processor.process_video_file(file_path)
    
    if result:
        print("\n🎬 PROCESSING RESULTS:")
        print("-" * 40)
        
        # Show video segments
        if result.get('video_segments'):
            print(f"\n📹 Video Segments ({len(result['video_segments'])}):")
            for i, segment in enumerate(result['video_segments'], 1):
                print(f"  {i}. {Path(segment).name}")
        
        # Show interaction segments
        if result.get('interaction_segments'):
            print(f"\n💬 Interaction Segments ({len(result['interaction_segments'])}):")
            for i, segment in enumerate(result['interaction_segments'], 1):
                print(f"  {i}. {Path(segment).name}")
        
        # Show S3 URLs
        if result.get('s3_urls'):
            print(f"\n☁️  S3 URLs ({len(result['s3_urls'])}):")
            for i, s3_item in enumerate(result['s3_urls'], 1):
                print(f"  {i}. {s3_item.get('filename', 'Unknown')} ({s3_item.get('size_mb', 0):.1f} MB)")
        
        print(f"\n⏱️  Processing Time: {result.get('processing_time_seconds', 0):.1f} seconds")
        print(f"📝 Message: {result.get('message', 'Processing completed')}")
        
        # Save results to file
        output_file = file_path.with_suffix('.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print("❌ Processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 