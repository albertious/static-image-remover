Use a still image (e.g. reference.png) to visually compare to each frame of a video (e.g. input.mp4).
If the png matches the current frame the video frame is deleted. If they do not match, the video frame is kept.

# Video Frame Removal and Compression Script

This Python script is designed to process a video by removing frames that match a specified reference image. The script then compresses the output into manageable chunks, and finally concatenates these chunks into a single video file. This approach is particularly useful for handling large video files that need to be processed efficiently.

## How It Works

1. **Load Reference Image:**
   - The script loads a reference image (`reference.png`) in grayscale, which is used to identify and remove matching frames from the input video.
   - The reference image is resized to improve processing performance.

2. **Frame Processing:**
   - Each frame of the input video (`input.mp4`) is compared to the reference image using template matching.
   - Frames that match the reference image are removed, while others are retained.

3. **Chunked Video Writing:**
   - The video is processed in 1GB chunks to avoid excessive memory usage.
   - Once a chunk reaches 1GB, it is saved and compressed using `ffmpeg`.

4. **Video Compression:**
   - Each 1GB chunk is compressed using `ffmpeg` with a preset configuration (`ultrafast` preset and 3M bitrate) to reduce the file size.

5. **Concatenation:**
   - All compressed chunks are concatenated into a single output file (`input_trimmed.mp4`) using `ffmpeg`.

6. **Clean Up:**
   - Temporary and compressed files are deleted after the final video is created to free up disk space.

## Installation

1. **Install Required Libraries:**
   - Ensure you have Python 3.x installed.
   - Install the necessary Python packages using pip:
     ```bash
     pip install opencv-python-headless numpy
     ```
   - Make sure `ffmpeg` is installed and accessible from your system's PATH.

2. **Set Up the Directory:**
   - Place the reference image (`reference.png`) and the input video file (`input.mp4`) in the same directory as the script.

## Usage

1. **Run the Script:**
   - Execute the script using Python:
     ```bash
     python video_processing_script.py
     ```
   - Replace `video_processing_script.py` with the actual name of your script file.

2. **Output:**
   - The processed video will be saved as `input_trimmed.mp4` in the same directory.

## Customization

- **Resize Factor:**
  - Adjust the `resize_factor` to change the size of the reference image during template matching. A higher value increases accuracy but slows down processing.

- **Batch Size:**
  - The `batch_size` determines how many frames are buffered before writing them to the video file. Adjust this value for performance tuning.

- **Multithreading:**
  - The script uses a `ThreadPoolExecutor` with 8 threads by default. You can adjust the number of threads (`max_workers`) based on your system’s capabilities.

- **FFMPEG Compression Settings:**
  - Modify the `-b:v` and `-preset` options in the `ffmpeg_command` list to change the video compression quality and speed.

## License

This script is open-source. Use it freely, but at your own risk. 

## Other

I don't have time to do support. Sorry in advance.

