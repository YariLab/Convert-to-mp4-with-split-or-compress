import os
import subprocess
import sys
import time
import platform


def get_gpu_info():
    system = platform.system()

    if system == "Linux":
        result = subprocess.run(["lspci", "-v"], capture_output=True, text=True)
        output = result.stdout.lower()
        if "nvidia" in output:
            return "nvidia"
        elif "amd" in output or "ati" in output:
            return "amd"
        elif "intel" in output:
            return "intel"
    elif system == "Windows":
        result = subprocess.run(["wmic", "path", "win32_videocontroller", "get", "name"], capture_output=True, text=True)
        output = result.stdout.lower()
        if "nvidia" in output:
            return "nvidia"
        elif "amd" in output or "radeon" in output:
            return "amd"
        elif "intel" in output:
            return "intel"
    elif system == "Darwin":  # macOS
        result = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True)
        output = result.stdout.lower()
        if "nvidia" in output:
            return "nvidia"
        elif "amd" in output or "ati" in output:
            return "amd"
        elif "intel" in output:
            return "intel"

    return None


def select_ffmpeg_codec():
    gpu_vendor = get_gpu_info()

    if gpu_vendor == "nvidia":
        return "hevc_nvenc"
    elif gpu_vendor == "amd":
        return "hevc_amf"
    elif gpu_vendor == "intel":
        return "hevc_qsv"
    else:
        return "libx265"


def get_video_duration(filename):
    result = subprocess.run(["ffmpeg", "-i", filename], stderr=subprocess.PIPE, text=True)
    for line in result.stderr.split('\n'):
        if "Duration" in line:
            duration_str = line.split("Duration:")[1].split(",")[0].strip()
            return duration_str
    return None


def split_video(input_file, split_size_mb):
    start_timer = time.time()

    duration_str = get_video_duration(input_file)
    if not duration_str:
        print("Unable to get video duration.")
        return

    hours, minutes, seconds = map(float, duration_str.split(":"))
    total_seconds = hours * 3600 + minutes * 60 + seconds
    estimated_duration_per_part = int(total_seconds / (os.path.getsize(input_file)/1024/1024 / split_size_mb/0.97))
    
    print("\nSplitting...")
    start_time = 0
    part_number = 1
    while start_time < total_seconds:
        end_time = start_time + estimated_duration_per_part
        if end_time > total_seconds:
            end_time = total_seconds

        split_time = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{int(start_time % 60):02}"
        duration = f"{int((end_time - start_time) // 3600):02}:{int(((end_time - start_time) % 3600) // 60):02}:{int((end_time - start_time) % 60):02}"

        name, ext = os.path.splitext(input_file)

        part_filename = f"{name}_part{part_number}.mp4"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", input_file, "-ss", split_time, "-t", duration, "-c", "copy", part_filename])

        size = os.path.getsize(part_filename) / (1024 * 1024)
        print(f"Part {part_number}: '{part_filename}' [{size:.2f} Mb]")

        start_time = end_time
        part_number += 1

    end_timer = time.time()
    conversion_time = end_timer - start_timer
    print(f"Splitting time: {conversion_time:.2f} sec\n")


def convert_to_mp4(input_file):
    if os.path.splitext(input_file)[1].lower() == '.mp4':
        return input_file
    
    name, ext = os.path.splitext(input_file)
    output_file = f"{name}.mp4"
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{name}_{counter}.mp4"
        counter += 1

    codec = select_ffmpeg_codec()
    print(f"Converting with codec: '{codec}'...")

    start_time = time.time()
    # TODO: "-global_quality", "35", "-preset", "veryslow" - not decrease size after compress! 
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", input_file, "-c:v", codec, "-global_quality", "33", "-preset", "medium", "-c:a", "copy", output_file]
    subprocess.run(command, check=True)
    end_time = time.time()
    conversion_time = end_time - start_time
    size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Converted to MP4: '{output_file}' [{size:.2f} Mb]\nConversion time: {conversion_time:.2f} sec")
    return output_file


def need_split(file, file_size_limit_mb):
    size = os.path.getsize(file) / (1024 * 1024)
    if os.path.splitext(file)[1].lower() == '.mp4':
        if file_size_limit_mb and size > file_size_limit_mb:
            split_video(file, file_size_limit_mb)
        else:
            print(f"\nGood file size!\n")


def main(file_size_limit_mb = None):
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpeg', '.mpg'}

    if len(sys.argv) > 1:
        for file in sys.argv[1:]:
            if os.path.isfile(file):
                size = os.path.getsize(file) / (1024 * 1024)
                if os.path.splitext(file)[1].lower() in video_extensions:
                    print(f"Found video file: '{file}' [{size:.2f} Mb]")
                    need_split(convert_to_mp4(file), file_size_limit_mb)
                else:
                    print(f"Skipped non-video file: '{file}'")
            else:
                print(f"File does not exist: '{file}'")
    else:
        print("No files provided")


if __name__ == '__main__':
    main(file_size_limit_mb = None)
    input()