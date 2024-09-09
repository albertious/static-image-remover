import cv2
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
import shutil
import subprocess

# Record the start time
start_time = time.time()

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

# Resize reference image to improve performance, if needed
resize_factor = 0.05
reference_image = cv2.resize(reference_image, (0, 0), fx=resize_factor, fy=resize_factor)

def images_are_similar(frame, reference_image, threshold=0.9):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Resize frame to match the reference image size
    frame_resized = cv2.resize(frame_gray, (reference_image.shape[1], reference_image.shape[0]))
    
    # Perform template matching
    result = cv2.matchTemplate(frame_resized, reference_image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    return max_val >= threshold

def process_frame(frame):
    if images_are_similar(frame, reference_image):
        return None  # Indicate that the frame should be removed
    else:
        return frame  # Return the frame to be kept

# Set input and output videos
input_file = 'stream.webm'
output_video_file = os.path.join(script_dir, 'stream.mp4')  # Save output in the same directory as the script

cap = cv2.VideoCapture(input_file)
if not cap.isOpened():
    raise FileNotFoundError(f"Unable to open video file {input_file}")

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Prepare FFmpeg command for GPU encoding
ffmpeg_cmd = [
    'ffmpeg',
    '-y',  # Overwrite output file if exists
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{frame_width}x{frame_height}',  # Frame size
    '-r', str(fps),  # Frame rate
    '-i', '-',  # Input from stdin
    '-c:v', 'h264_nvenc',  # Use NVENC encoder
    '-preset', 'fast',
    '-b:v', '2M',  # Bitrate
    output_video_file
]

# Start the FFmpeg process
ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

processed_frames = 0
removed_frames = 0
batch_size = 16  # Adjust for performance
frames_to_write = []

print("Processing video...")

# Adjust thread workers to your own CPU limits.
with ThreadPoolExecutor(max_workers=20) as executor:
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
            # Write the processed frame directly to FFmpeg
            ffmpeg_proc.stdin.write(result.tobytes())

            progress = (processed_frames / total_frames) * 100
            sys.stdout.write(f"\rFrame {processed_frames}/{total_frames} ({progress:.2f}%): Frame kept. Total removed: {removed_frames}     ")
            sys.stdout.flush()

        processed_frames += 1

# Clean up
cap.release()
ffmpeg_proc.stdin.close()
ffmpeg_proc.wait()

print(f"\nVideo saved as {output_video_file}.")

# Record the end time
end_time = time.time()

# Calculate total process time
elapsed_time = end_time - start_time
hours, remainder = divmod(elapsed_time, 3600)
minutes, seconds = divmod(remainder, 60)
elapsed_time_formatted = f"{int(hours)} Hour(s) {int(minutes)} Minute(s) {int(seconds)} Second(s)"

print(f"Total time taken: {elapsed_time_formatted}")

# Clean up temporary files
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
