import os
import openai
from tqdm import tqdm
import json
import time
import sys

# Set your OpenAI API key here or use an environment variable
openai.api_key = os.getenv("OPENAI_API_KEY", "sk-...")  # <-- Replace with your key or set env var

OUTPUT_DIR = "output"
SEGMENTS_JSON = "segments.json"
TRANSCRIPTIONS_JSON = "transcriptions.json"
GPT_MODEL = "gpt-4o-mini"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2
TIMEOUT = 60  # seconds

REFERENCE_PROMPT = '''
You are analyzing a transcript of a lecture to extract meaningful **main topics** and **subtopics**.

Here is the list of previously detected topics:

[
  {"title": "Photosynthesis", "start": "00:00:00", "end": "00:14:45"},
  {"title": "Chloroplast Structure", "start": "00:14:46", "end": "00:22:00"},
  {"title": "Light Reactions", "start": "00:22:01", "end": "00:30:00"}
]

You are now analyzing the next chunk of the transcript.

Please do the following:
1. Determine if any previous topic continues.
2. If a **subtopic** of a previous topic is introduced, include it with `parent_topic`.
3. If a **new topic** starts, start a new item.
4. Output the updated list of topics, with start and end timestamps.

Transcript (with timestamps):

[00:30:01 --> 00:30:30] Let's now dive deeper into ATP synthesis.
[00:30:30 --> 00:34:10] ATP is produced in the thylakoid membrane...
...

Output format:

[
  {"title": "Light Reactions", "start": "00:22:01", "end": "00:34:10"},
  {"title": "ATP Synthesis", "start": "00:30:01", "end": "00:34:10", "parent_topic": "Light Reactions"}
]
'''

def transcribe_audio_segments(output_dir=OUTPUT_DIR, language="en"):
    # If transcriptions.json exists, load and return it
    if os.path.exists(TRANSCRIPTIONS_JSON):
        print(f"Loading transcriptions from {TRANSCRIPTIONS_JSON} for faster testing...")
        with open(TRANSCRIPTIONS_JSON, "r") as f:
            return json.load(f)
    
    audio_files = [f for f in sorted(os.listdir(output_dir)) if f.endswith((
        '.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus'
    ))]
    results = []
    print(f"Found {len(audio_files)} audio files to transcribe.")
    
    for filename in tqdm(audio_files, desc="Transcribing files", unit="file"):
        file_path = os.path.join(output_dir, filename)
        print(f"\n---\nStarting transcription: {file_path}")
        
        # Retry logic for transcription
        for attempt in range(MAX_RETRIES):
            try:
                with open(file_path, "rb") as audio_file:
                    transcript = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        language=language
                    )
                
                print(f"Finished transcription: {file_path}")
                print(f"Segments found: {len(transcript.segments)}")
                
                # Create a single object for this audio file with all segments
                file_transcription = {
                    "filename": filename,
                    "file_path": file_path,
                    "total_segments": len(transcript.segments),
                    "segments": []
                }
                
                # Add all segments with their timestamps and text
                for i, segment in enumerate(transcript.segments):
                    print(f"  Segment {i+1}: {segment['start']}s - {segment['end']}s")
                    file_transcription["segments"].append({
                        "segment_id": i + 1,
                        "start": segment['start'],
                        "end": segment['end'],
                        "text": segment['text']
                    })
                
                results.append(file_transcription)
                break  # Success, exit retry loop
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {filename}: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    print(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Failed to transcribe {filename} after {MAX_RETRIES} attempts. Skipping...")
                    # Add a placeholder entry to maintain file order
                    results.append({
                        "filename": filename,
                        "file_path": file_path,
                        "total_segments": 0,
                        "segments": [],
                        "error": str(e)
                    })
    
    print("\nAll files transcribed!")
    # Save to transcriptions.json for future fast runs
    with open(TRANSCRIPTIONS_JSON, "w") as f:
        json.dump(results, f, indent=2)
    return results

def _validate_timestamp(start_str, end_str, chunk_duration):
    """Validate that timestamps are within chunk duration"""
    try:
        # Parse MM:SS format
        start_parts = start_str.split(":")
        end_parts = end_str.split(":")
        
        if len(start_parts) != 2 or len(end_parts) != 2:
            return False
        
        start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
        end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # Check if within chunk duration
        if start_seconds < 0 or end_seconds > chunk_duration:
            return False
        
        # Check if start < end
        if start_seconds >= end_seconds:
            return False
        
        return True
    except (ValueError, IndexError):
        return False

def analyse_topic_gpt(transcript, previous_topics, chunk_duration, model=GPT_MODEL):
    max_minutes = int(chunk_duration // 60)
    max_seconds = int(chunk_duration % 60)
    
    prompt = f"""
You are analyzing a transcript of a React/JavaScript lecture to extract meaningful topics.

Previous topics detected:
{json.dumps(previous_topics, indent=2)}

Analyze this transcript and identify the main topic being discussed. The audio chunk is {max_minutes}:{max_seconds:02d} long.

{transcript}

Return ONLY a JSON array with topics. Each topic should have:
- "title": The topic name
- "start": Start time in MM:SS format (must be within 00:00 to {max_minutes}:{max_seconds:02d})
- "end": End time in MM:SS format (must be within 00:00 to {max_minutes}:{max_seconds:02d})
- "parent_topic": (optional) If this is a subtopic

IMPORTANT: 
- End times must NOT exceed {max_minutes}:{max_seconds:02d}
- Each topic should have different time ranges
- Be specific about when each topic starts and ends

Example output:
[
  {{"title": "React Hooks", "start": "00:00", "end": "02:30"}},
  {{"title": "useState Hook", "start": "02:30", "end": "05:45", "parent_topic": "React Hooks"}}
]

Return ONLY the JSON array, no markdown formatting or explanations.
"""
    
    # Retry logic for GPT analysis
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            
            # Clean the response - remove markdown code blocks
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]   # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove ```
            
            content = content.strip()
            
            # Try to parse the JSON output
            try:
                topics = json.loads(content)
                if isinstance(topics, list):
                    # Validate timestamps
                    validated_topics = []
                    for topic in topics:
                        if isinstance(topic, dict) and "title" in topic:
                            start_str = topic.get("start", "00:00")
                            end_str = topic.get("end", "00:00")
                            
                            # Validate timestamp format and range
                            if _validate_timestamp(start_str, end_str, chunk_duration):
                                validated_topics.append(topic)
                            else:
                                print(f"Invalid timestamp in topic '{topic['title']}': {start_str} - {end_str}")
                    
                    return validated_topics if validated_topics else [{"title": "Unknown", "start": "00:00", "end": f"{max_minutes}:{max_seconds:02d}"}]
                else:
                    print(f"GPT returned non-list JSON: {content}")
                    return [{"title": "Unknown", "start": "00:00", "end": f"{max_minutes}:{max_seconds:02d}"}]
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}")
                print(f"Raw content: {content}")
                return [{"title": "Unknown", "start": "00:00", "end": f"{max_minutes}:{max_seconds:02d}"}]
                
        except Exception as e:
            print(f"GPT analysis attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying GPT analysis in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"Failed GPT analysis after {MAX_RETRIES} attempts. Using fallback.")
                return [{"title": "Unknown", "start": "00:00", "end": f"{max_minutes}:{max_seconds:02d}"}]

def detect_speaker_student_interactions(transcript, chunk_duration):
    """
    Detect segments where the speaker is directly interacting with students.
    This includes Q&A sessions, student questions, direct addressing, etc.
    """
    max_minutes = int(chunk_duration // 60)
    max_seconds = int(chunk_duration % 60)
    
    prompt = f"""
You are analyzing a lecture transcript to identify segments where the speaker is directly interacting with students.

Look for:
- Questions asked by the speaker to students
- Student questions and speaker responses
- Direct addressing of students ("you", "class", "students")
- Interactive moments ("raise your hand", "what do you think")
- Q&A sessions
- Student participation moments

Analyze this transcript and identify segments with speaker-student interactions:

{transcript}

Return ONLY a JSON array with interaction segments. Each segment should have:
- "title": Descriptive title of the interaction
- "start": Start time in MM:SS format (must be within 00:00 to {max_minutes}:{max_seconds:02d})
- "end": End time in MM:SS format (must be within 00:00 to {max_minutes}:{max_seconds:02d})
- "interaction_type": Type of interaction (e.g., "Q&A", "Student Question", "Direct Address", "Interactive Moment")

IMPORTANT: 
- End times must NOT exceed {max_minutes}:{max_seconds:02d}
- Only include segments with clear speaker-student interaction
- Be specific about when each interaction starts and ends

Example output:
[
  {{"title": "Student Question about React Hooks", "start": "02:30", "end": "04:15", "interaction_type": "Student Question"}},
  {{"title": "Class Discussion on useState", "start": "05:00", "end": "07:30", "interaction_type": "Q&A"}}
]

Return ONLY the JSON array, no markdown formatting or explanations.
"""
    
    # Retry logic for interaction detection
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            
            # Clean the response - remove markdown code blocks
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]   # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove ```
            
            content = content.strip()
            
            # Try to parse the JSON output
            try:
                interactions = json.loads(content)
                if isinstance(interactions, list):
                    # Validate timestamps
                    validated_interactions = []
                    for interaction in interactions:
                        if isinstance(interaction, dict) and "title" in interaction:
                            start_str = interaction.get("start", "00:00")
                            end_str = interaction.get("end", "00:00")
                            
                            # Validate timestamp format and range
                            if _validate_timestamp(start_str, end_str, chunk_duration):
                                validated_interactions.append(interaction)
                            else:
                                print(f"Invalid timestamp in interaction '{interaction['title']}': {start_str} - {end_str}")
                    
                    return validated_interactions
                else:
                    print(f"GPT returned non-list JSON for interactions: {content}")
                    return []
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed for interactions: {e}")
                print(f"Raw content: {content}")
                return []
                
        except Exception as e:
            print(f"Interaction detection attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying interaction detection in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"Failed interaction detection after {MAX_RETRIES} attempts.")
                return []

def create_segment_json(audio_files):
    segment_json = []
    interaction_segments = []  # Separate list for speaker-student interactions
    prev_topics = []
    
    for audio_file in tqdm(audio_files, desc="Analysing topics and interactions", unit="file"):
        # Skip files with errors
        if audio_file.get("error"):
            print(f"Skipping {audio_file['filename']} due to transcription error")
            continue
            
        # Skip files with no segments
        if not audio_file["segments"]:
            print(f"Skipping {audio_file['filename']} - no segments found")
            continue
        
        # Get chunk duration and global start time
        chunk_duration = audio_file["segments"][-1]["end"] if audio_file["segments"] else 0
        chunk_start_time = audio_file["segments"][0]["start"] if audio_file["segments"] else 0
        
        # Calculate global start time based on chunk number
        try:
            # Try to extract chunk number from filename (old format)
            chunk_number = int(audio_file["filename"].split("_")[1])
        except (ValueError, IndexError):
            # New format: use 1 as default chunk number
            chunk_number = 1
        global_start_offset = (chunk_number - 1) * 600  # Each chunk is ~10 minutes
        
        # Create a single transcript with all segments for this file
        transcript_with_time = ""
        for segment in audio_file["segments"]:
            # Convert seconds to MM:SS format
            start_time = f"{int(segment['start']//60):02d}:{int(segment['start']%60):02d}"
            end_time = f"{int(segment['end']//60):02d}:{int(segment['end']%60):02d}"
            transcript_with_time += f"[{start_time} --> {end_time}] {segment['text']}\n"
        
        # Analyze topics for the entire file with chunk duration constraint
        topics = analyse_topic_gpt(transcript_with_time, prev_topics, chunk_duration)
        
        # Detect speaker-student interactions
        interactions = detect_speaker_student_interactions(transcript_with_time, chunk_duration)
        
        # Add new topics to the list
        for topic in topics:
            if isinstance(topic, dict) and "title" in topic:
                # Parse and validate timestamps
                start_str = topic.get("start", "00:00")
                end_str = topic.get("end", "00:00")
                
                # Convert MM:SS to seconds
                try:
                    start_parts = start_str.split(":")
                    end_parts = end_str.split(":")
                    
                    start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                    end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])
                    
                    # Ensure end time doesn't exceed chunk duration
                    if end_seconds > chunk_duration:
                        end_seconds = chunk_duration
                        end_str = f"{int(end_seconds//60):02d}:{int(end_seconds%60):02d}"
                    
                    # Calculate global timestamps
                    global_start = global_start_offset + start_seconds
                    global_end = global_start_offset + end_seconds
                    
                    segment_json.append({
                        "title": topic["title"],
                        "start": start_str,
                        "end": end_str,
                        "parent_topic": topic.get("parent_topic"),
                        "filename": audio_file["filename"],
                        "start_time": global_start,
                        "end_time": global_end,
                        "chunk_start": chunk_start_time,
                        "chunk_end": chunk_duration,
                        "chunk_number": chunk_number,
                        "segment_type": "topic"  # Mark as regular topic segment
                    })
                except (ValueError, IndexError) as e:
                    print(f"Invalid timestamp format in topic '{topic['title']}': {start_str} - {end_str}")
                    # Use fallback timestamps
                    segment_json.append({
                        "title": topic["title"],
                        "start": "00:00",
                        "end": f"{int(chunk_duration//60):02d}:{int(chunk_duration%60):02d}",
                        "parent_topic": topic.get("parent_topic"),
                        "filename": audio_file["filename"],
                        "start_time": global_start_offset,
                        "end_time": global_start_offset + chunk_duration,
                        "chunk_start": chunk_start_time,
                        "chunk_end": chunk_duration,
                        "chunk_number": chunk_number,
                        "segment_type": "topic"  # Mark as regular topic segment
                    })
        
        # Add interaction segments to separate list
        for interaction in interactions:
            if isinstance(interaction, dict) and "title" in interaction:
                # Parse and validate timestamps
                start_str = interaction.get("start", "00:00")
                end_str = interaction.get("end", "00:00")
                
                # Convert MM:SS to seconds
                try:
                    start_parts = start_str.split(":")
                    end_parts = end_str.split(":")
                    
                    start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                    end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])
                    
                    # Ensure end time doesn't exceed chunk duration
                    if end_seconds > chunk_duration:
                        end_seconds = chunk_duration
                        end_str = f"{int(end_seconds//60):02d}:{int(end_seconds%60):02d}"
                    
                    # Calculate global timestamps
                    global_start = global_start_offset + start_seconds
                    global_end = global_start_offset + end_seconds
                    
                    interaction_segments.append({
                        "title": interaction["title"],
                        "start": start_str,
                        "end": end_str,
                        "interaction_type": interaction.get("interaction_type", "Unknown"),
                        "filename": audio_file["filename"],
                        "start_time": global_start,
                        "end_time": global_end,
                        "chunk_start": chunk_start_time,
                        "chunk_end": chunk_duration,
                        "chunk_number": chunk_number,
                        "segment_type": "interaction"  # Mark as interaction segment
                    })
                except (ValueError, IndexError) as e:
                    print(f"Invalid timestamp format in interaction '{interaction['title']}': {start_str} - {end_str}")
                    # Use fallback timestamps
                    interaction_segments.append({
                        "title": interaction["title"],
                        "start": "00:00",
                        "end": f"{int(chunk_duration//60):02d}:{int(chunk_duration%60):02d}",
                        "interaction_type": interaction.get("interaction_type", "Unknown"),
                        "filename": audio_file["filename"],
                        "start_time": global_start_offset,
                        "end_time": global_start_offset + chunk_duration,
                        "chunk_start": chunk_start_time,
                        "chunk_end": chunk_duration,
                        "chunk_number": chunk_number,
                        "segment_type": "interaction"  # Mark as interaction segment
                    })
        
        prev_topics = topics
        time.sleep(0.5)
    
    # Combine regular segments and interaction segments
    all_segments = segment_json + interaction_segments
    
    # Save interaction segments separately for easy access
    if interaction_segments:
        with open("interaction_segments.json", "w") as f:
            json.dump(interaction_segments, f, indent=2)
        print(f"💬 Found {len(interaction_segments)} speaker-student interaction segments")
    
    return all_segments

if __name__ == "__main__":
    try:
        audio_files = transcribe_audio_segments()
        print("\n--- ANALYSING TOPICS ---\n")
        segment_json = create_segment_json(audio_files)
        with open(SEGMENTS_JSON, "w") as f:
            json.dump(segment_json, f, indent=2)
        print(f"\nSegment topics saved to {SEGMENTS_JSON}")
        print("\n--- TOPIC SEGMENTS ---\n")
        for i, seg in enumerate(segment_json, 1):
            print(f"Segment {i}:")
            for k, v in seg.items():
                print(f"  {k}: {v}")
            print()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Progress saved.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        sys.exit(1) 