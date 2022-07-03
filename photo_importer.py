'''
A simple script to import files and handle raw photos
Also handles a bit of photo processing
'''

import os
import sys
import shutil
import argparse
import pickle
import subprocess
import configparser
from datetime import datetime
from pathlib import Path
import exifread


# Handle arguments
parser = argparse.ArgumentParser()
parser.add_argument("--dryrun", action="store_true",
                    help="Do not move files around or increment counter")
parser.add_argument("--debug", action="store_true",
                    help="Get some extra info for troubleshooting")
args = parser.parse_args()

# Variables that might change
valid_extensions = ['.tif', '.cr2', '.jpg', '.jpeg', '.png']
video_extensions = ['.mp4', '.mkv']

# Variables that should not normally be changed
script_dir = os.path.dirname(__file__)
config_file = Path(f'{script_dir}/importer.ini')
allpics = []
reject_count = 0

# For handling the serial number, read a pickle file
serial_file = Path(f'{script_dir}/serial.pk')
try:
    with open(serial_file, 'rb') as f:
        serial = pickle.load(f)
    if args.debug:
        print("pickle file found")
except:
    serial = 0

# Handle config file
if not os.path.exists(config_file):
    print(f'Missing {config_file}. Please add {config_file}')
    sys.exit(1)
config = configparser.ConfigParser()
config.read(config_file)
p_inbox = Path(config['PATH']['p_inbox'])
pre_process = Path(config['PATH']['pre_process'])
raw_path = Path(config['PATH']['raw_path'])
reject_path = Path(config['PATH']['reject_path'])
video_path = Path(config['PATH']['video_path'])

def get_date_taken(path):
    f = open(path, 'rb')
    exif_tags = exifread.process_file(f, stop_tag='DateTimeOriginal')
    exif_datetag = exif_tags['EXIF DateTimeOriginal']
    return str(exif_datetag)

def reject(file):
    '''Moves a file that is rejected to the rejected path'''
    global reject_count
    reject_count += 1
    if not os.path.exists(reject_path):
        os.makedirs(reject_path)
    file_name = os.path.basename(file)
    if args.dryrun:
        print("ACTION: Move file to reject path")
    else:
        shutil.move(file, f'{reject_path}/{file_name}')

def reject_video(video):
    '''Moves a video that is rejected to the video path'''
    global reject_count
    reject_count += 1
    if not os.path.exists(video_path):
        os.makedirs(video_path)
    file_name = os.path.basename(video)
    if args.dryrun:
        print(f"ACTION: Move {video} to {video_path}")
    else:
        shutil.move(video, f'{video_path}/{file_name}')

def process():
    '''Main run of the program'''
    global serial
    for subdir, dirs, files in os.walk(p_inbox):
        for file in files:
            allpics.append(os.path.join(subdir, file))
    for pic in allpics:
        serial += 1
        original_name, extension = os.path.splitext(pic)
        extension = extension.lower()
        if extension not in valid_extensions:
            if extension in video_extensions:
                print(f"{pic} appears to be a video: moving to {video_path}")
                reject_video(pic)
                continue
            else:
                print(f"{pic} does not have a valid photo extension:rejecting")
                reject(pic)
                continue
        if extension == ".cr2":
            storage_path = raw_path
        else:
            storage_path = pre_process

        try:
            date_taken = datetime.strptime(get_date_taken(pic),
                                           '%Y:%m:%d %H:%M:%S')
            new_filepath = os.path.join(storage_path,
                                        datetime.strftime(date_taken, '%Y'),
                                        datetime.strftime(date_taken, '%m'))
        except Exception:
            print(f"Error raised on import of EXIF tag for {pic}")
            date_taken = None
            new_filepath = os.path.join(storage_path, 'nodate')
        if date_taken != None:
            new_name = (f'{date_taken.strftime("%Y%m%d_%H%M%S")}_{serial}'
                        f'{extension}')
            new_jname = (f'{date_taken.strftime("%Y%m%d_%H%M%S")}_{serial}'
                        f'.jpg')
        else:
            new_name = f'{serial}{extension}'
            new_jname = f'{serial}.jpg'

        # Let's move this file to the correct destination
        if not os.path.exists(new_filepath):
            if not args.dryrun:
                os.makedirs(new_filepath)
            else:
                print(f'ACTION: create folder: {new_filepath}')
        if not args.dryrun:
            shutil.move(pic, os.path.join(new_filepath, new_name))
        else:
            print(f'ACTION: move {pic} to '
                  f'{os.path.join(new_filepath, new_name)}')

        # Make a jpg for this if it is cr2
        if extension == ".cr2":
            # Create a jpg version
            if args.dryrun:
                print("ACTION: call dark-table and make jpeg")
            else:
                if not os.path.exists(raw_path):
                    os.makedirs(raw_path)
                subprocess.run(args=['darktable-cli',
                    os.path.join(new_filepath, new_name),
                    os.path.join(pre_process,
                    datetime.strftime(date_taken, '%Y'), new_jname)])


if __name__ == '__main__':
    print('Welcome to image_importer')
    process()
    if not args.dryrun:
        with open(serial_file, 'wb') as f:
            pickle.dump(serial, f)
    else:
        print('ACTION: Dumping pickle')
