#!/usr/bin/python3

from Camera import Camera as Cam
import cv2
import json
import os
import datetime
import sys
from parameters import *
dirsep = ""

if sys.platform == 'linux' or sys.platform == 'darwin':
    dirsep = '/'
elif sys.platform == 'win32':
    dirsep = '\\'


# test_json_file = "config.json"
#
# # DICTIONARY CONSTANT STRINGS
# LABELS = "labels"
# FOLDERS = "folders"
# INPUT_IMAGE_FOLDER = "input_image_directory"
# EXPOSURE_TIME = "exposure_time"
# ROOT_FOLDER = "path_to_output_data_root_folder"
# CAMERA_SERIAL = "camera_serial_number"
# MAX_HEIGHT = "max_display_window_height"
# MAX_WIDTH = "max_display_window_width"
# EXTENSION = "file_extension"
# CAMERA_INFERENCE = "do_camera_inference"
# CAMERA_MODE = "camera_mode"
# INFERENCE_LABELS = "camera_inference_labels"
# CONFIDENCE= "confidence"
# DELAY_INTERVAL = "delay_interval_in_frames"


def unique_name_date_time_now():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json_to_dict(json_file):
    with open(json_file) as json_file:
        the_dict = json.load(json_file)
        return the_dict


def prepare_folders_and_options(configuration):
    folders = {}
    for each in configuration[LABELS]:
        folder_name = fr"{configuration[ROOT_FOLDER]}{dirsep}{configuration[LABELS][each]}"
        folders[each] = folder_name

        if os.path.exists(folder_name):
            print(f"{folder_name} Exists")
        else:
            print(f"{folder_name} DNE!")
            print(f"Creating {folder_name}")
            os.mkdir(folder_name)

    configuration[FOLDERS] = folders


def do_camera_stuff(configuration):

    camera = Cam(configuration[CAMERA_SERIAL])
    enable_camera_inference = configuration[CAMERA_INFERENCE]
    if enable_camera_inference:
        # try set the camera up for inference
        try:
            camera.setup_inference_camera_defaults(OFFSETX=configuration[OFFSETX], OFFSETY=configuration[OFFSETY], WIDTH=configuration[WIDTH], HEIGHT=configuration[HEIGHT])
            camera.EXPOSURE_TIME = configuration[EXPOSURE_TIME]
        except:
            print("Error setting up camera to do inference running in default camera mode.")
            enable_camera_inference = False


    img = camera.get_next_image().GetNDArray()

    if enable_camera_inference:
        rofl, inference_info = camera.get_next_image_and_inference_result()
        img = rofl.GetNDArray()
        print(inference_info)

    height, width, channels = img.shape

    max_window_height = configuration[MAX_HEIGHT]
    max_window_width = configuration[MAX_WIDTH]

    resize_please = False

    if width > max_window_width or height > max_window_height:
        resize_please = True
    scale_ratio = 1
    if resize_please:
        width_ratio = max_window_width / width
        height_ratio = max_window_height / height
        scale_ratio = height_ratio
        if width_ratio < height_ratio:
            scale_ratio = width_ratio
    width = int(img.shape[1] * scale_ratio)
    height = int(img.shape[0] * scale_ratio)
    dim = (width, height)
    previous_food_status = 10
    counter = 0
    while True:
        # Capture frame-by-frame
        inference_info = ()
        if enable_camera_inference:
            rofl, inference_info = camera.get_next_image_and_inference_result()
            img = rofl.GetNDArray()
            # print(inference_info)
        else:
            img = camera.get_next_image().GetNDArray()

        displayed_image = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

        if enable_camera_inference:
            origin = (30, 30)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            color = (255, 0, 0)
            thickness = 1
            cls, conf, time = inference_info
            displayed_image = cv2.putText(
                displayed_image,
                f"Class:{configuration[INFERENCE_LABELS][f'{cls}']} | Confidence:{conf*100.0:.2f}",
                origin, font, font_scale, color, thickness, cv2.LINE_AA)

        # basic filter function
        if cls != previous_food_status and conf > config[CONFIDENCE]:
            counter += 1

        # change food status
        if cls != previous_food_status and conf > config[CONFIDENCE] and counter > config[DELAY_INTERVAL]:
            # print(counter)
            print(configuration[INFERENCE_LABELS][f'{cls}'])
            previous_food_status = cls
            # save image
            cv2.imwrite(f"{configuration[ROOT_FOLDER]}/food_status.png",img)
            print(f"image saved to {configuration[ROOT_FOLDER]}/food_status.png")
            counter = 0


        cv2.imshow("Camera Stream", displayed_image)
        lame = cv2.waitKey(1)
        if not lame == -1:
            print('#########', lame, ord('1'), ord('!'), '1'.upper())
        if lame == ord('\x1b'):
            break
        elif lame == -1:
            continue
        else:
            for a_val in configuration[LABELS]:
                if lame == ord(a_val):
                    save_image_name = f"{unique_name_date_time_now()}.{configuration[EXTENSION]}"
                    cv2.imwrite(f"{configuration[FOLDERS][a_val]}/{save_image_name}",img)
                    print(f"image saved to {configuration[FOLDERS][a_val]}/{save_image_name}")
                # elif lame == ord(upper(a_val)):
                #     for 1 in range(100):
                #         save_image_name = f"{unique_name_date_time_now()}.{configuration[EXTENSION]}"
                #         cv2.imwrite(f"{configuration[FOLDERS][a_val]}/{save_image_name}",img)
                #         print(f"image saved to {configuration[FOLDERS][a_val]}/{save_image_name}")


def add_keybindings(displayed_image, configuration):
    image_width = int(displayed_image.shape[1])
    image_height = int(displayed_image.shape[0])
    labels = configuration[LABELS]
    origin_w = image_width-100
    start_h = image_height- 10
    origin = (origin_w, start_h)
    start_h = start_h-20
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = .6
    color = (225, 255, 225)
    thickness = 1
    displayed_image = cv2.putText(
        displayed_image,
        f"Esc:Exit",
        origin, font, font_scale, color, thickness, cv2.LINE_AA)
    for each_key in labels:
        origin = (origin_w, start_h)
        start_h = start_h - 20
        displayed_image = cv2.putText(
            displayed_image,
            f"{each_key}:{labels[f'{each_key}']}",
            origin, font, font_scale, color, thickness, cv2.LINE_AA)
    return displayed_image

if __name__=='__main__':
    # read configuration file
    config = read_json_to_dict(test_json_file)

    if sys.platform == 'linux' or sys.platform == 'darwin':
        config[ROOT_FOLDER] = '/'.join(config[ROOT_FOLDER].split('\\'))
    elif sys.platform == 'win32':
        print(config[ROOT_FOLDER])
        config[ROOT_FOLDER] = '\\'.join(config[ROOT_FOLDER].split('/'))
    # print(config[ROOT_FOLDER])
    prepare_folders_and_options(config)
    # print(config[OFFSETX])
    if config[CAMERA_MODE]:
        do_camera_stuff(config)
    else:
        do_folder_stuff(config)
