import cv2
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import subprocess

# Define the directory for temporary files
script_dir = os.path.dirname(os.path.abspath(__file__))
temp_dir = os.path.join(script_dir, 'temp_files')

# Create the temp_files directory if it does not exist
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Load the reference image in grayscale and resize it
reference_image_path = 'offine.png'
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

fourcc = cv2.VideoWriter_fourcc(*'H264')
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
            # Update the same line in terminal
            sys.stdout.write(f"\rFrame {processed_frames}: Removed matching frame. Total removed: {removed_frames}     ")
            sys.stdout.flush()
        else:
            frames_to_write.append(result)
            if len(frames_to_write) >= batch_size:
                for buffered_frame in frames_to_write:
                    video_writer.write(buffered_frame)
                frames_to_write = []

            # Update the same line in terminal
            sys.stdout.write(f"\rFrame {processed_frames}: Frame kept. Total removed: {removed_frames}     ")
            sys.stdout.flush()

        processed_frames += 1

# Write any remaining frames in buffer
if frames_to_write:
    for buffered_frame in frames_to_write:
        video_writer.write(buffered_frame)

# Release resources
cap.release()
video_writer.release()

print(f"Intermediate video saved as {temp_video_file}.")
print("Processing complete. Re-compressing video...")

# Detect GPU availability and set appropriate codec
def detect_gpu():
    try:
        # Check if NVIDIA GPU is available
        result = subprocess.run(['ffmpeg', '-hwaccels'], capture_output=True, text=True)
        if 'cuda' in result.stdout.lower():
            return 'h264_nvenc'
        # Check if AMD GPU is available
        if 'amf' in result.stdout.lower():
            return 'h264_amf'
    except Exception as e:
        print(f"Error detecting GPU: {e}")

    # Default to CPU if no GPU is detected or available
    return 'libx264'

# Select codec based on GPU availability
codec = detect_gpu()

# Re-compress the video using ffmpeg with GPU acceleration if available
ffmpeg_command = [
    'ffmpeg', '-i', temp_video_file,
    '-b:v', '6M',        # Set video bitrate to 7M
    '-r', '30',          # Set frame rate to 30 fps
    '-an',               # Remove audio track
    '-c:v', codec,       # Use GPU-accelerated codec if available
    final_output_file
]

subprocess.run(ffmpeg_command, check=True)

print(f"Final video saved as {final_output_file}.")
