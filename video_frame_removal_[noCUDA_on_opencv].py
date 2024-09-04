import cv2
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
import shutil  # For removing the temp directory

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

# Resize reference image to improve performance, if needed.
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
input_file = 'Live_High-Definition_Views_from_the_International_Space_Station_Official_NASA_Stream-[O9mYwRlucZY].f302.mkv'
temp_video_file = os.path.join(temp_dir, 'temp_video.mp4')
output_video_file = os.path.join(script_dir, 'Live_High-Definition_Views_from_the_International_Space_Station_Official_NASA_Stream-[O9mYwRlucZY].f302.mp4')  # Save output in the same directory as the script

cap = cv2.VideoCapture(input_file)
if not cap.isOpened():
    raise FileNotFoundError(f"Unable to open video file {input_file}")

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Calculate total number of frames
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(temp_video_file, fourcc, fps, (frame_width, frame_height))

processed_frames = 0
removed_frames = 0
batch_size = 16  # Depending on your hardware, adjusting this can impact performance
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

# Record the end time
end_time = time.time()

# Calculate total process time
elapsed_time = end_time - start_time
hours, remainder = divmod(elapsed_time, 3600)
minutes, seconds = divmod(remainder, 60)
elapsed_time_formatted = f"{int(hours)} Hour(s) {int(minutes)} Minute(s) {int(seconds)} Second(s)"

# Use FFmpeg for encoding with GPU support
ffmpeg_cmd = f'ffmpeg -i "{temp_video_file}" -r 30 -c:v h264_nvenc -b:v 2M -preset fast "{output_video_file}"'
os.system(ffmpeg_cmd)

# Clean up temporary files
if os.path.exists(temp_video_file):
    os.remove(temp_video_file)
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)

# Print completion message with total time
print(f"Video frames trimmed! Total time taken: {elapsed_time_formatted}")
