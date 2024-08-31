# Video Frame Removal and Compression Script

This Python script processes a video by removing frames that match a specified reference image and then compresses the resulting video. The script supports GPU acceleration for compression if an NVIDIA or AMD GPU is available, falling back to CPU-based compression otherwise.

## Features

- **Frame Removal:** Removes frames from the video that match a reference image using template matching.
- **GPU Acceleration:** Utilizes GPU acceleration for compression if an appropriate GPU is detected.
- **Batch Processing:** Handles video frames in batches to optimize performance.

## Installation

1. **Install Required Python Libraries:**
   Ensure you have Python 3.x installed and then install the required libraries using `pip`:
   ```bash
   pip3 install opencv-python numpy

2. **Install FFMPEG:**

Make sure ffmpeg is installed on your system. You can download it from FFMPEG's official website or install it using a package manager.

3. **Place Your Files:**

    Save the reference image as reference.png in the same directory as the script.
    Place your input video file as input.mp4 in the same directory.


## Usage

1. **Run the Script:**

    Execute the script using Python:

   ```bash
   python3 video_frame_removal.py

2. **Output Files:**

    Intermediate video: temp_video.mp4 (saved in the temp_files directory)
    Final processed video: input_trimmed.mp4

## How It Works

**Setup and Reference Image Loading:**
Creates a directory for temporary files if it doesn't exist.
Loads and resizes the reference image to speed up processing.

**Frame Processing:**
Each frame of the video is compared to the reference image.
Frames that match the reference image are removed.
Non-matching frames are written to a temporary video file in batches.

**Video Compression:**
Detects available GPU hardware (NVIDIA or AMD) to use hardware-accelerated video encoding.
Uses ffmpeg to compress the temporary video file into the final output video.
If no GPU is available, falls back to CPU-based compression.
        
**Resource Cleanup:**
Intermediate files and resources are cleaned up after processing.

## Customization

**Reference Image Resize Factor:**
Adjust resize_factor to change the size of the reference image for template matching. A lower factor speeds up processing but may reduce accuracy.

**Compression Settings:**
Modify the -b:v option in the ffmpeg_command to change the video bitrate. Adjust -r to set the desired frame rate.

**GPU Detection:**
The detect_gpu function identifies the available GPU and selects the appropriate codec. You can modify this function to add support for other GPUs or codecs.

## Troubleshooting

**Reference Image Not Found:**
Ensure reference.png is in the same directory as the script and is a valid image file.

**FFMPEG Errors:**
Verify that ffmpeg is installed and accessible from your system's PATH.

## License
This script is provided "as-is" without any warranties. Use at your own risk.
