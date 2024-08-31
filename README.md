Use a still image (e.g. reference.png) to visually compare to each frame of a video (e.g. input.mp4).
If the png matches the current frame the video frame is deleted. If they do not match, the video frame is kept.

# Load the reference image in grayscale and resize it
reference_image_path = 'reference.png'

# Dealing with the process in 1GB chunks to avoid massive temp files building up. For 15GB chunks change the '1' to '15' here:
max_temp_file_size = 1 * 1024 * 1024 * 1024  

# Resize reference images as they are compared to each other to improve performance, if needed. 
# 0.075 is very low and processes fast but increase up to 1.0 this if you want more accuracy.
resize_factor = 0.075

# Set input and output videos
input_file = 'input.mp4'
final_output_file = 'input_trimmed.mp4

# Adjust thread workers to your own cpu limits.
with ThreadPoolExecutor(max_workers=8) as executor:
 

# Compress the temporary file using FFMPEG.
compressed_temp_file = os.path.join(temp_dir, f'{file_counter:05d}_compressed.mp4')
ffmpeg_command = [
                'ffmpeg', '-i', current_temp_file,
                '-b:v', '3M',  # Set video bitrate
                '-preset', 'ultrafast',  # Faster preset for encoding speed
                '-threads', '8',  # Number of threads for encoding
                compressed_temp_file
           
