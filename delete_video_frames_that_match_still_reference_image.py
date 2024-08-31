import cv2
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import subprocess
import os
import sys

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

# Resize reference images as they are compared to each other to improve performance, if needed.
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
input_file = 'input.mp4'
final_output_file = 'output_trimmed.mp4'
temp_files = []
temp_file_prefix = 'temp_output_'
temp_file_suffix = '.mp4'
max_temp_file_size = 6 * 1024 * 1024 * 1024  # 6GB chunk size
file_counter = 1  # Counter for sequential filenames

cap = cv2.VideoCapture(input_file)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

def create_temp_file():
    # Create a named temporary file with sequential numbering
    temp_file_name = os.path.join(temp_dir, f'{file_counter:05d}{temp_file_suffix}')
    temp_files.append(temp_file_name)
    return temp_file_name

current_temp_file = create_temp_file()
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = 30  # Frames per second
video_writer = cv2.VideoWriter(current_temp_file, fourcc, fps, (frame_width, frame_height))

processed_frames = 0
removed_frames = 0
batch_size = 30
frames_to_write = []

print("Processing video...")

# Adjust thread workers to your own cpu limits.
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
            sys.stdout.write(f"\rFrame {processed_frames}: Removed matching frame. Total removed: {removed_frames}")
            sys.stdout.flush()
        else:
            frames_to_write.append(result)
            if len(frames_to_write) >= batch_size:
                for buffered_frame in frames_to_write:
                    video_writer.write(buffered_frame)
                frames_to_write = []
                
                # Check the size of the current temporary file
                if os.path.getsize(current_temp_file) >= max_temp_file_size:
                    # Close and compress the current temporary file
                    video_writer.release()

                    # Compress the temporary file using FFMPEG
                    compressed_temp_file = os.path.join(temp_dir, f'{file_counter:05d}_compressed.mp4')
                    ffmpeg_command = [
                        'ffmpeg', '-i', current_temp_file,
                        '-b:v', '7M',  # Set video bitrate
                        '-r', '30',    # Set frame rate to 30 fps
                        '-preset', 'ultrafast',  # Faster preset for encoding speed
                        '-c:v', 'libx264',
                        '-threads', '8',  # Number of threads for encoding
                        '-an',  # Remove audio tracks
                        compressed_temp_file
                    ]
                    subprocess.run(ffmpeg_command, check=True)
                    print(f"\rCompressed {current_temp_file} to {compressed_temp_file}.")

                    # Remove the old temporary file
                    os.remove(current_temp_file)
                    
                    # Increment the file counter for the next temp file
                    file_counter += 1
                    
                    # Prepare a new temporary file
                    current_temp_file = create_temp_file()
                    video_writer = cv2.VideoWriter(current_temp_file, fourcc, fps, (frame_width, frame_height))

            # Update the same line in terminal
            sys.stdout.write(f"\rFrame {processed_frames}: Frame kept. Total removed: {removed_frames}")
            sys.stdout.flush()

        processed_frames += 1

# Write any remaining frames in buffer
if frames_to_write:
    for buffered_frame in frames_to_write:
        video_writer.write(buffered_frame)

# Release resources
cap.release()
video_writer.release()

# Concatenate all compressed files into the final output using FFMPEG
concatenate_file = os.path.join(temp_dir, 'files_to_concatenate.txt')
with open(concatenate_file, 'w') as file_list:
    for temp_file in temp_files:
        compressed_file = temp_file.replace(temp_file_suffix, '_compressed.mp4')
        if os.path.exists(compressed_file):
            file_list.write(f"file '{compressed_file}'\n")

ffmpeg_concat_command = [
    'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concatenate_file,
    '-c', 'copy', final_output_file
]
subprocess.run(ffmpeg_concat_command, check=True)
print(f"Final video saved as {final_output_file}.")

# Clean up
os.remove(concatenate_file)
for temp_file in temp_files:
    if os.path.exists(temp_file):
        os.remove(temp_file)

print(f"Temporary and compressed files removed.")
