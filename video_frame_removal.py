import cv2
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import subprocess
import shutil
import re

# Define the directory for temporary files
script_dir = os.path.dirname(os.path.abspath(__file__))
temp_dir = os.path.join(script_dir, 'temp_files')

# Create the temp_files directory if it does not exist
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Load the reference image in grayscale and resize it
reference_image_path = 'reference.png'
reference_image = cv2.imread(reference_image_path, cv2.IMREAD_GRAYSCALE)

if reference_image is None:
    raise FileNotFoundError(f"Reference image at {reference_image_path} not found or unable to load.")

# Resize reference image to improve performance, if needed.
resize_factor = 0.05
reference_image = cv2.resize(reference_image, (0, 0), fx=resize_factor, fy=resize_factor)

def images_are_similar(frame, reference, threshold=0.9):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_resized = cv2.resize(frame_gray, (reference.shape[1], reference.shape[0]))
    result = cv2.matchTemplate(frame_resized, reference, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold

def process_frame(frame):
    if images_are_similar(frame, reference_image):
        return None  # Indicate that the frame should be removed
    else:
        return frame  # Return the frame to be kept

# Set input and output videos
input_file = 'stream.webm'
temp_video_file = os.path.join(temp_dir, 'temp_video.mp4')
final_output_file = 'stream_trimmed.mp4'

cap = cv2.VideoCapture(input_file)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Calculate total number of frames
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

fourcc = cv2.VideoWriter_fourcc(*'avc1')
video_writer = cv2.VideoWriter(temp_video_file, fourcc, fps, (frame_width, frame_height))

processed_frames = 0
removed_frames = 0
batch_size = 30
frames_to_write = []

print("Processing video...")

# Adjust thread workers to your own CPU limits.
with ThreadPoolExecutor(max_workers=8) as executor:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        future = executor.submit(process_frame, frame)
        result = future.result()
        
        if result is None:
            removed_frames += 1
            # Update the same line in terminal with frame processing status
            progress = (processed_frames / total_frames) * 100
            sys.stdout.write(f"\rFrame {processed_frames}/{total_frames} ({progress:.2f}%): Removed matching frame. Total removed: {removed_frames}     ")
            sys.stdout.flush()
        else:
            frames_to_write.append(result)
            if len(frames_to_write) >= batch_size:
                for buffered_frame in frames_to_write:
                    video_writer.write(buffered_frame)
                frames_to_write = []

            # Update the same line in terminal with frame processing status
            progress = (processed_frames / total_frames) * 100
            sys.stdout.write(f"\rFrame {processed_frames}/{total_frames} ({progress:.2f}%): Frame kept. Total removed: {removed_frames}     ")
            sys.stdout.flush()

        processed_frames += 1

# Write any remaining frames in buffer
if frames_to_write:
    for buffered_frame in frames_to_write:
        video_writer.write(buffered_frame)

# Release resources
cap.release()
video_writer.release()

print(f"\nIntermediate video saved as {temp_video_file}.")
print("Video trimming complete. Re-compressing video with FFMPEG. Please wait...")

# Detect GPU availability and set appropriate codec
def detect_gpu():
    try:
        # Check if NVIDIA GPU is available
        result = subprocess.run(['ffmpeg', '-hwaccels'], capture_output=True, text=True)
        if 'cuda' in result.stdout.lower():
            return 'h264_nvenc', 'GPU'
        # Check if AMD GPU is available
        if 'amf' in result.stdout.lower():
            return 'h264_amf', 'GPU'
    except Exception as e:
        print(f"Error detecting GPU: {e}")

    # Default to CPU if no GPU is detected or available
    return 'libx264', 'CPU'

# Select codec and processing type based on GPU availability
codec, processing_type = detect_gpu()

# Get the total duration of the video in seconds
def get_video_duration_in_seconds(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(command, capture_output=True, text=True)
    return float(result.stdout.strip())

total_duration_seconds = get_video_duration_in_seconds(temp_video_file)

# Convert time string from FFmpeg to seconds
def time_to_seconds(time_str):
    h, m, s = map(float, time_str.split(':'))
    return h * 3600 + m * 60 + s

# Re-compress the video using ffmpeg with GPU acceleration if available
ffmpeg_command = [
    'ffmpeg', '-i', temp_video_file,
    '-b:v', '6M',        # Set video bitrate to 6M
    '-r', '30',          # Set frame rate to 30 fps
    '-an',               # Remove audio track
    '-c:v', codec,       # Use GPU-accelerated codec if available
    final_output_file
]

# Function to parse and display FFmpeg progress with percentage
def run_ffmpeg_with_progress(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Regular expression to parse time from FFmpeg output
    progress_pattern = re.compile(r'time=(\d+:\d+:\d+.\d+)')
    
    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # Parse and display progress
            match = progress_pattern.search(output)
            if match:
                time_str = match.group(1)
                current_time_seconds = time_to_seconds(time_str)
                percentage = (current_time_seconds / total_duration_seconds) * 100
                sys.stdout.write(f"\rProgress: {time_str} / {total_duration_seconds} seconds ({percentage:.2f}%) - Processing with {processing_type}   ")
                sys.stdout.flush()

    return process.wait()

# Run ffmpeg command with progress display
run_ffmpeg_with_progress(ffmpeg_command)

print(f"\nFinal video saved as {final_output_file}.")

# Clean up temporary files and directory
try:
    shutil.rmtree(temp_dir)
    print(f"Temporary files and directory '{temp_dir}' have been deleted.")
except Exception as e:
    print(f"Error deleting temporary files: {e}")
