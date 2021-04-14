#!/usr/bin/python3

from Camera import Camera as Cam
import cv2
import json
import os
import datetime
import subprocess
import requests
import json

test_json_file = "config.json"

# DICTIONARY CONSTANT STRINGS
LABELS = "labels"
FOLDERS = "folders"
INPUT_IMAGE_FOLDER = "input_image_directory"
EXPOSURE_TIME = "exposure_time"
ROOT_FOLDER = "path_to_output_data_root_folder"
CAMERA_SERIAL = "camera_serial_number"
MAX_HEIGHT = "max_display_window_height"
MAX_WIDTH = "max_display_window_width"
EXTENSION = "file_extension"
CAMERA_INFERENCE = "do_camera_inference"
CAMERA_MODE = "camera_mode"
INFERENCE_LABELS = "camera_inference_labels"


def unique_name_date_time_now():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def read_json_to_dict(json_file):
    with open(json_file) as json_file:
        the_dict = json.load(json_file)
        return the_dict


def prepare_folders_and_options(configuration):
    if not os.path.exists(configuration[ROOT_FOLDER]):
        os.makedirs(configuration[ROOT_FOLDER])
    folders = {}
    for each in configuration[LABELS]:
        folder_name = fr"{configuration[ROOT_FOLDER]}/{configuration[LABELS][each]}"
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
            camera.setup_inference_camera_defaults()
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
        if True:
            displayed_image = add_keybindings(displayed_image, configuration)
        # Display the resulting frame
        cv2.imshow("Camera Stream", displayed_image)

        # https://stackoverflow.com/questions/51143458/difference-in-output-with-waitkey0-and-waitkey1/51143586
        # displays the frame for 1 ms, returns the key (or -1 if nothing was pressed
        lame = cv2.waitKey(1)
        # print('lame', lame)
        if not lame == -1:
            print('#########', lame, ord('1'), ord('!'), '1'.upper())

        # https://www.w3schools.com/python/ref_func_ord.asp
        # The ord() function returns the number representing the unicode code of a specified character.
        if lame == ord('\x1b'):
            # Escape char (hex1b, dec 27)
            break
        elif (lame == ord('\xbe')) or (lame == ord('\xbf')):
            url = 'http://192.168.1.75:8080/rest/items/TestSwitch001'
            headers1 = {
                'Content-Type': 'text/plain'
            }
            auth1 = ('avner', 'avner4')

            data1 = 'na'
            if lame == ord('\xbe'):
                # trigger BowlEmpty (F1 - hex: xBE, dec: 190)
                print('Trigger bowlEmpty', lame)
                data1 = 'ON'
            else:
                # trigger BowlFull (F2 - hex: xBF, dec: 191)
                print('Trigger bowlFull', lame)
                data1 = 'OFF'
                
            # map curl command e.g.
            #   /usr/bin/curl  -q --user  'avner:avner4' --header "Content-Type: text/plain" --request POST --data "ON" http://192.168.1.75:8080/rest/items/TestSwitch001
            # to python requests
            r = requests.post(url, data=data1, auth=auth1, headers=headers1)
            continue
        
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


config = read_json_to_dict(test_json_file)
prepare_folders_and_options(config)
if config[CAMERA_MODE]:
    do_camera_stuff(config)
else:
    do_folder_stuff(config)
