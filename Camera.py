#!/usr/bin/python3

import os
import PySpin
import numpy as np
from time import sleep


class FileAccessError(Exception):
    pass


class FileAccess:
    @staticmethod
    def open_file_to_write(cam):
        """
        This function opens the camera file for writing.

        :param cam: Camera used to perform file operation.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            cam.FileOperationSelector.SetValue(PySpin.FileOperationSelector_Open)
            cam.FileOpenMode.SetValue(PySpin.FileOpenMode_Write)
            cam.FileOperationExecute.Execute()

            if cam.FileOperationStatus.GetValue() != PySpin.FileOperationStatus_Success:
                print('Failed to open file for writing!')
                return False
        except PySpin.SpinnakerException as ex:
            print('Unexpected exception: %s' % ex)
            return False
        return True

    @staticmethod
    def open_file_to_read(cam):
        """
        This function opens the file to read.

        :param cam: Camera used to perform file operation.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            cam.FileOperationSelector.SetValue(PySpin.FileOperationSelector_Open)
            cam.FileOpenMode.SetValue(PySpin.FileOpenMode_Read)
            cam.FileOperationExecute.Execute()

            if cam.FileOperationStatus.GetValue() != PySpin.FileOperationStatus_Success:
                print('Failed to open file for reading!')
                return False
        except PySpin.SpinnakerException as ex:
            print('Unexpected exception: %s' % ex)
            return False
        return True

    @staticmethod
    def close_file(cam):
        """
        This function closes the file.

        :param cam: Camera used to perform file operation.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            cam.FileOperationSelector.SetValue(PySpin.FileOperationSelector_Close)
            cam.FileOperationExecute.Execute()

            if cam.FileOperationStatus.GetValue() != PySpin.FileOperationStatus_Success:
                print('Failed to close file!')
                return False
        except PySpin.SpinnakerException as ex:
            print('Unexpected exception: %s' % ex)
            return False
        return True

    @staticmethod
    def execute_delete_command(cam):
        """
        This function executes delete operation on the camera.

        :param cam: Camera used to perform file operation.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            cam.FileOperationSelector.SetValue(PySpin.FileOperationSelector_Delete)
            cam.FileOperationExecute.Execute()

            if cam.FileOperationStatus.GetValue() != PySpin.FileOperationStatus_Success:
                print('Failed to delete file!')
                return False
        except PySpin.SpinnakerException as ex:
            print('Unexpected exception: %s' % ex)
            return False
        return True

    @staticmethod
    def execute_write_command(cam):
        """
        This function executes write command on the camera.

        :param cam: Camera used to perform file operation.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            cam.FileOperationSelector.SetValue(PySpin.FileOperationSelector_Write)
            cam.FileOperationExecute.Execute()

            if cam.FileOperationStatus.GetValue() != PySpin.FileOperationStatus_Success:
                print('Failed to write to file!')
                return False
        except PySpin.SpinnakerException as ex:
            print('Unexpected exception : %s' % ex)
            return False
        return True

    @staticmethod
    def file_access_upload(cam, file_selector, file_path, debug=False):
        """
        This function writes file to the specified file selector.

        :param cam: Camera to which a file is uploaded via File Access
        :param file_selector: camera file access name
        :param file_path: path of the file to be written to the camera
        :param debug: enable or disable printing debug messages
        :type cam: CameraPtr
        :type file_selector: string
        :type file_path: string
        :type debug: boolean
        :return: true if successful; false if unsuccessful
        """

        try:
            result = True

            # cam.Init()
            nodemap = cam.GetNodeMap()

            # Check file selector support
            if cam.FileSelector.GetAccessMode() == PySpin.NA or cam.FileSelector.GetAccessMode() == PySpin.NI:
                raise FileAccessError('File selector not supported on device!')

            # need to find the node for the file selector name
            node_file_selector = PySpin.CEnumerationPtr(nodemap.GetNode('FileSelector'))
            if not PySpin.IsAvailable(node_file_selector) or not PySpin.IsWritable(node_file_selector):
                raise FileAccessError('Unable to set File Selector (node retrieval). Aborting...')

            node_file_selector_entry = node_file_selector.GetEntryByName(file_selector)
            if not PySpin.IsAvailable(node_file_selector_entry) or not PySpin.IsReadable(node_file_selector_entry):
                raise FileAccessError('Unable to set File Selector (entry retrieval). Aborting...')

            file_selector_entry = node_file_selector_entry.GetValue()
            node_file_selector.SetIntValue(file_selector_entry)

            # SDK-1195: Delete file on camera before writing in case camera runs out of space
            file_size = cam.FileSize.GetValue()
            if file_size > 0:
                if not FileAccess.execute_delete_command(cam):
                    raise FileAccessError('Failed to delete file!')

            # Open file on camera for write
            if not FileAccess.open_file_to_write(cam):
                raise FileAccessError('Failed to open file!')

            # Attempt to set FileAccessLength to FileAccessBufferNode length to speed up the write
            if cam.FileAccessLength.GetValue() < cam.FileAccessBuffer.GetLength():
                try:
                    cam.FileAccessLength.SetValue(cam.FileAccessBuffer.GetLength())
                except PySpin.SpinnakerException as ex:
                    raise FileAccessError('Unable to set FileAccessLength to FileAccessBuffer length: %s' % ex)

            # Set file access offset to zero if it's not
            cam.FileAccessOffset.SetValue(0)

            with open(file_path, 'rb') as fd:
                fd.seek(0, os.SEEK_END)
                num_bytes = fd.tell()  # find out the file size
                fd.seek(0, 0)
                file_data = np.fromfile(fd, dtype=np.ubyte, count=num_bytes)

                # Compute number of write operations required
                total_bytes_to_write = num_bytes
                intermediate_buffer_size = cam.FileAccessLength.GetValue()
                write_iterations = (total_bytes_to_write // intermediate_buffer_size) + \
                                   (0 if ((total_bytes_to_write % intermediate_buffer_size) == 0) else 1)

                if debug:
                    print('')
                    print('Total bytes to write: {}'.format(total_bytes_to_write))
                    print('FileAccessLength: {}'.format(intermediate_buffer_size))
                    print('Write iterations: {}'.format(write_iterations))

                bytes_left_to_write = total_bytes_to_write
                total_bytes_written = 0

                if debug:
                    print("Writing data to device")

                # Splitting the file into equal chunks (except the last chunk)
                sections = []
                for index in range(write_iterations):
                    num = index * intermediate_buffer_size
                    if num == 0:
                        continue
                    sections.append(num)
                split_data = np.array_split(file_data, sections)

                # Writing split data to camera
                for i in range(write_iterations):
                    # Setup data to write
                    tmp_buffer = split_data[i]

                    # Write to AccessBufferNode
                    if debug:
                        print('Setting buffer iteration {}'.format(i))
                    cam.FileAccessBuffer.Set(tmp_buffer)  # tmpBufferSize

                    if intermediate_buffer_size > bytes_left_to_write:
                        # Update FileAccessLength, otherwise garbage data outside the range would be written to device
                        cam.FileAccessLength.SetValue(bytes_left_to_write)

                    # Do write command
                    if not FileAccess.execute_write_command(cam):
                        raise FileAccessError('Write stream failed!')
                    # Verify size of bytes written
                    size_written = cam.FileOperationResult.GetValue()

                    # Keep track of total bytes written
                    total_bytes_written += size_written

                    # Keep track of bytes left to write
                    bytes_left_to_write = total_bytes_to_write - total_bytes_written

                    if debug:
                        print('File Access Offset: {}'.format(cam.FileAccessOffset.GetValue()))
                        print('Bytes written: {} of {}'.format(total_bytes_written, total_bytes_to_write))
                        print('Progress: ({} out of {})'.format(i + 1, write_iterations))

                if debug:
                    print('Writing complete')

                if not FileAccess.close_file(cam):
                    raise FileAccessError('Failed to close file!')

        except FileAccessError as ex:
            print('File Access Upload exception occurred. {}'.format(ex))
            result = False

        except Exception as ex:
            print('File Access Upload unexpected error.  {}'.format(ex))
            result = False
        finally:
            pass
            # cam.DeInit()

        return result


class ConfigureCameraError(Exception):
    def __init__(self, value):
        print("ConfigureCameraError(Exception): __init__", value)
        self.value = value

    def __str__(self):
        print("ConfigureCameraError(Exception) __str__:" + str(Exception))
        return repr(self.value)


class CameraStartupError(Exception):
    def __init__(self, value):
        print("CameraStartupError(Exception): __init__", value)
        self.value = value

    def __str__(self):
        print("CameraStartupError(Exception) __str__:" + str(Exception))
        return repr(self.value)


class Camera(object):
    ISP_NODES = ['DenoiseEnable', 'SharpeningEnable', 'GammaEnable', 'BlackLevelClampingEnable'] #'LUTEnable',
    STREAM_BUFFER_HANDLING = "StreamBufferHandlingMode"

    CAMERA_STREAMING = False
    SOFTWARE_TRIGGER = False

    FRAME_RATE = 5
    EXPOSURE_TIME = 9000

    TESTING_IMAGES_TO_CAPTURE = 10

    BOUNDING_BOX_THRESHOLD = 0.25

    def __init__(self, serial):
        super(Camera, self).__init__()

        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        print(f"Cameras connected: {len(self.cam_list)}")
        try:
            self.camera = self.cam_list.GetBySerial(serial)
            self.serial = serial
            self.camera.Init()
            self.camera.DeInit()
        except:
            # print(f"Camera with serial number {serial} not found {len(self.cam_list)}")
            try:
                if serial == "" and len(self.cam_list) == 1:
                    self.camera = self.cam_list[0]
                    self.serial = self.camera.TLDevice.DeviceSerialNumber.ToString()
                elif len(self.cam_list) == 1:
                    self.camera = self.cam_list[0]
                    self.serial = self.camera.TLDevice.DeviceSerialNumber.ToString()
                else:
                    raise CameraStartupError(f"Too many cameras")
            except:
                raise CameraStartupError(f"Failed to start cameras")

        self.camera.Init()
        self.nodemap = self.camera.GetNodeMap()
        self.nodemapTL = self.camera.GetTLStreamNodeMap()

        self.set_selector_to_value(self.nodemapTL, self.STREAM_BUFFER_HANDLING, "NewestOnly")

    def disable_camera_image_injection(self):
        """
        This function disables injected image and sets the camera to stream live images.
        :return: true if successful; false if unsuccessful
        """
        try:
            self.camera.Init()

            # Set Test Pattern Generator Selector to Pipeline Start
            nodemap = self.camera.GetNodeMap()

            # Set Test Pattern Generator Selector to 'Pipeline Start'
            node_test_pattern_generator_selector = PySpin.CEnumerationPtr(nodemap.GetNode('TestPatternGeneratorSelector'))
            if not PySpin.IsAvailable(node_test_pattern_generator_selector) \
                    or not PySpin.IsWritable(node_test_pattern_generator_selector):
                print('Unable to set TestPatternGeneratorSelector (node retrieval). Aborting...')
                return False

            node_test_pattern_generator_sensor_start = node_test_pattern_generator_selector.GetEntryByName('PipelineStart')
            if not PySpin.IsAvailable(node_test_pattern_generator_sensor_start) \
                    or not PySpin.IsReadable(node_test_pattern_generator_sensor_start):
                print('Unable to set Test Pattern Generator to Sensor (entry retrieval). Aborting...')
                return False

            test_pattern_generator_sensor_start = node_test_pattern_generator_sensor_start.GetValue()
            node_test_pattern_generator_selector.SetIntValue(test_pattern_generator_sensor_start)

            # Set Test Pattern to 'Off'
            node_test_pattern_selector = PySpin.CEnumerationPtr(nodemap.GetNode('TestPattern'))
            if not PySpin.IsAvailable(node_test_pattern_selector) \
                    or not PySpin.IsWritable(node_test_pattern_selector):
                print('Unable to set Test Pattern (node retrieval). Aborting...')
                return False

            node_test_pattern_injected_image = node_test_pattern_selector.GetEntryByName('Off')
            if not PySpin.IsAvailable(node_test_pattern_injected_image) \
                    or not PySpin.IsReadable(node_test_pattern_injected_image):
                print('Unable to set Test Pattern (entry retrieval). Aborting...')
                return False

            test_pattern_off = node_test_pattern_injected_image.GetValue()
            node_test_pattern_selector.SetIntValue(test_pattern_off)

            # Set width and height
            node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
            node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))

            if not PySpin.IsAvailable(node_width) \
                    or not PySpin.IsWritable(node_width):
                print('Unable to set image width (node retrieval). Aborting...')
                return False
            width_to_set = node_width.GetMax()
            node_width.SetValue(width_to_set)

            if not PySpin.IsAvailable(node_height) \
                    or not PySpin.IsWritable(node_height):
                print('Unable to set injected image height (node retrieval). Aborting...')
                return False
            height_to_set = node_height.GetMax()
            node_height.SetValue(height_to_set)

        except Exception as e:
            print(e)
            return False
        finally:
            self.camera.DeInit()
            return True

    def max_width_and_height(self):
        offset_X = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetX'))
        offset_X.SetValue(0)
        offset_y = PySpin.CIntegerPtr(self.nodemap.GetNode('OffsetY'))
        offset_y.SetValue(0)

        node_width = PySpin.CIntegerPtr(self.nodemap.GetNode('Width'))
        width_to_set = node_width.GetMax()
        node_width.SetValue(width_to_set)

        node_height = PySpin.CIntegerPtr(self.nodemap.GetNode('Height'))
        height_to_set = node_height.GetMax()
        node_height.SetValue(height_to_set)

    def configure_camera_for_image_injection(self, width=1440, height=1080):
        """
        This function configures the camera to use injected images.

        :param cam: Camera pointer
        :type cam: CameraPtr
        :return: true if successful; false if unsuccessful
        """
        try:
            # self.camera.Init()

            # Set Test Pattern Generator Selector to Pipeline Start
            nodemap = self.camera.GetNodeMap()

            # Set Test Pattern Generator Selector to 'Pipeline Start'
            node_test_pattern_generator_selector = PySpin.CEnumerationPtr(nodemap.GetNode('TestPatternGeneratorSelector'))
            if not PySpin.IsAvailable(node_test_pattern_generator_selector) \
                    or not PySpin.IsWritable(node_test_pattern_generator_selector):
                print('Unable to set Test Pattern Generator (node retrieval). Aborting...')
                return False

            node_test_pattern_generator_pipeline_start = node_test_pattern_generator_selector.GetEntryByName('PipelineStart')
            if not PySpin.IsAvailable(node_test_pattern_generator_pipeline_start) \
                    or not PySpin.IsReadable(node_test_pattern_generator_pipeline_start):
                print('Unable to set Test Pattern Generator (entry retrieval). Aborting...')
                return False

            test_pattern_generator_pipeline_start = node_test_pattern_generator_pipeline_start.GetValue()
            node_test_pattern_generator_selector.SetIntValue(test_pattern_generator_pipeline_start)

            # Set Test Pattern to 'Injected Image'
            node_test_pattern_selector = PySpin.CEnumerationPtr(nodemap.GetNode('TestPattern'))
            if not PySpin.IsAvailable(node_test_pattern_selector) \
                    or not PySpin.IsWritable(node_test_pattern_selector):
                print('Unable to set Test Pattern (node retrieval). Aborting...')
                return False

            node_test_pattern_injected_image = node_test_pattern_selector.GetEntryByName('InjectedImage')
            if not PySpin.IsAvailable(node_test_pattern_injected_image) \
                    or not PySpin.IsReadable(node_test_pattern_injected_image):
                print('Unable to set Test Pattern (entry retrieval). Aborting...')
                return False

            # Test Pattern to "Injected Image"
            test_pattern_injected_image = node_test_pattern_injected_image.GetValue()
            node_test_pattern_selector.SetIntValue(test_pattern_injected_image)

            # Set injected image width and height
            node_injected_width = PySpin.CIntegerPtr(nodemap.GetNode('InjectedWidth'))
            if not PySpin.IsAvailable(node_injected_width) \
                    or not PySpin.IsWritable(node_injected_width):
                print('Unable to set injected image width (node retrieval). Aborting...')
                return False
            node_injected_width.SetValue(width)
            node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
            if not PySpin.IsAvailable(node_width) \
                    or not PySpin.IsWritable(node_width):
                print('Unable to set image width (node retrieval). Aborting...')
                return False
            node_width.SetValue(width)

            node_injected_height = PySpin.CIntegerPtr(nodemap.GetNode('InjectedHeight'))
            if not PySpin.IsAvailable(node_injected_height) \
                    or not PySpin.IsWritable(node_injected_height):
                print('Unable to set injected image height (node retrieval). Aborting...')
                return False
            node_injected_height.SetValue(height)
            node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
            if not PySpin.IsAvailable(node_height) \
                    or not PySpin.IsWritable(node_height):
                print('Unable to set injected image height (node retrieval). Aborting...')
                return False
            node_height.SetValue(height)
        except Exception as e:
            print(e)
            return False
        finally:
            pass
            # self.camera.DeInit()

    def set_training_mean_and_scalar(self):
        neuralla_mean = 127.5
        neuralla_scalar = 255.0
        "InferencePreprocessBppSelector"

        self.set_selector_to_value(self.nodemap, "InferencePreprocessBppSelector", "Mono8")
        # "InferencePreprocessChannelMean"
        self.set_float_value_to_node(self.nodemap, "InferencePreprocessChannelMean", neuralla_mean)
        # "InferencePreprocessChannelScalar"
        self.set_float_value_to_node(self.nodemap, "InferencePreprocessChannelScalar", neuralla_scalar)

    def start_one_camera(self):
        super(Camera, self).__init__()

        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        try:
            self.camera = self.cam_list[0]
            self.serial = self.camera.TLDevice.DeviceSerialNumber.ToString()

        except:
            raise CameraStartupError(f"Camera with serial number {self.serial} not found")
        self.camera.Init()
        self.nodemap = self.camera.GetNodeMap()
        self.nodemapTL = self.camera.GetTLStreamNodeMap()

    @staticmethod
    def convert_raw_image_8bit_to_10bit(input_np_arr_data, output_file):
        """
        This function converts the raw MONO 8 image to 10 bit image for image injection

        :param input_np_arr_data: input numpy array data (8 bit image)
        :param output_file: output file path (10 bit image)
        :return: true if successful, false if unsuccessful
        """
        output_data = input_np_arr_data.astype('uint16')  # convert to the 16 bit container
        output_data = output_data << 2  # bit shift by 2 bits
        output_data.tofile(output_file)

        return True

    def inject_10bit_image(self, input_path):
        """
        This function injects an image to the camera

        :param cam: Camera pointer
        :param input_path: file path of the image to be uploaded
        :type cam: CameraPtr
        :type input_path: string
        :return: true if successful; false if unsuccessful
        """
        return FileAccess.file_access_upload(self.camera, 'InjectedImage', input_path)

    def inject_bayer8_image(self, input_8_bit_img, out_width=1440, out_height=1080, input_10_bit_path="temp.raw"):
        assert (out_width * out_height == int(input_8_bit_img.size / 3))
        # assuming interleaved RGB input
        red = 0
        green = 1
        blue = 2
        # assuming RGGB output
        rg_row = 1

        # input_file = input_10_bit_path
        # Do the work: simple naive way of doing it
        try:
            input_data = input_8_bit_img.astype('uint16')  # convert to the 16 bit container
        except FileNotFoundError:
            assert False, "File Not Found"

        output_data = np.zeros((out_width * out_height), dtype=int)

        for y in range(0, out_height-1):
            for x in range(0, out_width-1):
                idx = y * out_width + x
                if (rg_row):
                    if (idx % 2 == 0):
                        # print(input_data.shape)
                        # print(output_data.shape)
                        output_data[idx] = (input_data[y][x][red] + input_data[y][x+1][red])/2
                    else:
                        output_data[idx] = (input_data[y][x][green] + input_data[y][x-1][green])/2
                else:
                    if (idx % 2 == 0):
                        output_data[idx] = (input_data[y][x][green] + input_data[y][x+1][green])/2
                    else:
                        output_data[idx] = (input_data[y][x][blue] + input_data[y][x-1][blue])/2
            rg_row = rg_row ^ 1

        # write output
        output = output_data.astype('uint16')  # convert to the 16 bit container
        output = output << 2  # bit shift by 2 bits

        output.tofile(input_10_bit_path)
        result = self.inject_10bit_image(input_10_bit_path)
        if not result:
            print('.', end="")
            # print('Unable to inject image {} to camera.'.format(input_10_bit_path))
        os.remove(input_10_bit_path)

        height = input_8_bit_img.shape[0]
        width = input_8_bit_img.shape[1]
        result = self.configure_camera_for_image_injection(width=width, height=height)

        return result

    def inject_mono8_image(self, input_8_bit_img, input_10_bit_path="temp.raw"):
        """
        Injects a mono8 image into the camera and configures the camera to use it.

        :param cam: Camera pointer
        :param input_8_bit_img: the 8bit image as a numpy array of type np.uint8
        :param input_10_bit_path: file path of the 10 bit image (will be created)
        :return: true if successful; false if unsuccessful
        """

        result = self.convert_raw_image_8bit_to_10bit(input_8_bit_img, input_10_bit_path)
        if not result:
            print(',', end="")
            # print('Unable to convert image to 10 bit format')
            return False

        result = self.inject_10bit_image(input_10_bit_path)
        if not result:
            print('.', end="")
            # print('Unable to inject image {} to camera.'.format(input_10_bit_path))
        os.remove(input_10_bit_path)

        height = input_8_bit_img.shape[0]
        width = input_8_bit_img.shape[1]
        result = self.configure_camera_for_image_injection(width=width, height=height)

        return result

    def end_acquisition(self):
        self.camera.EndAcquisition()
        self.CAMERA_STREAMING = False

    @staticmethod
    def upload_inference_network(cam, input_path):
        """
        This function uploads the inference network file to the camera

        :param cam: Camera pointer
        :param input_path: file path of the inference network file to be uploaded
        :type cam: CameraPtr
        :type input_path: string
        :return: true if successful; false if unsuccessful
        """
        return FileAccess.file_access_upload(cam, 'InferenceNetwork', input_path)

    @staticmethod
    def set_int_value_to_node(nodemap, node_name, int_value):
        # sets the float value for a specific node ideal for exposure/gain/etc
        the_node = PySpin.CIntegerPtr(nodemap.GetNode(node_name))
        the_node.SetValue(int_value)

    @staticmethod
    def set_float_value_to_node(nodemap, node_name, float_value):
        # sets the float value for a specific node ideal for exposure/gain/etc
        the_node = PySpin.CFloatPtr(nodemap.GetNode(node_name))
        the_node.SetValue(float_value)

    @staticmethod
    def get_float_value_from_node(nodemap, node_name):
        # sets the float value for a specific node ideal for exposure/gain/etc
        the_node = PySpin.CFloatPtr(nodemap.GetNode(node_name))
        return the_node.GetValue()

    @staticmethod
    def disable_node_checkbox(nodemap, node_name):
        # disables a checkbox/node in spinview
        the_node = PySpin.CBooleanPtr(nodemap.GetNode(node_name))
        if not the_node.GetValue():
            return True
        elif PySpin.IsWritable(the_node):
            the_node.SetValue(False)
            return True
        else:
            return False

    def set_camera_passthrough(self):
        node_to_set_to_special_number = "Test0001"
        special_number = 2429937002
        self.set_int_value_to_node(self.nodemap, node_to_set_to_special_number, special_number)
        self.camera.DeInit()
        self.camera.Init()

    @staticmethod
    def enable_node_checkbox(nodemap, node_name):
        # enables a checkbox/node in spinview
        the_node = PySpin.CBooleanPtr(nodemap.GetNode(node_name))
        if the_node.GetValue():
            return True
        elif PySpin.IsWritable(the_node):
            the_node.SetValue(True)
            return True
        else:
            return False

    @staticmethod
    def set_selector_to_value(nodemap, selector, value):
        # selects an value in a node drop down selector
        try:
            selector_node = PySpin.CEnumerationPtr(nodemap.GetNode(selector))
            selector_entry = selector_node.GetEntryByName(value)
            selector_value = selector_entry.GetValue()
            selector_node.SetIntValue(selector_value)
        except PySpin.SpinnakerException:
            print("Failed to set {} selector to {} value".format(selector, value))

    def set_settings_on_camera_unet_demo(self):
        # user set 0
        # self.set_selector_to_value(self.nodemap, "UserSetSelector", "UserSet0")
        # camera.UserSetLoad.Execute()
        inputline1 = "Line1"
        self.set_selector_to_value(self.nodemap, "AcquisitionMode", "Continuous")

        # acquisition
        self.set_selector_to_value(self.nodemap, "TriggerSelector", "FrameStart")
        # self.set_selector_to_value(self.nodemap, "TriggerMode", "On")
        # self.set_selector_to_value(self.nodemap, "TriggerSource", "Line1")

        # turn off Gain Auto
        self.set_selector_to_value(self.nodemap, "GainAuto", "Continuous")

        # turn off Exposure Auto
        self.set_selector_to_value(self.nodemap, "ExposureAuto", "Continuous")

        # setting exposure time
        # self.camera.ExposureTime.SetValue(self.EXPOSURE_TIME)

        # handle stream buffer
        self.set_selector_to_value(self.nodemapTL, self.STREAM_BUFFER_HANDLING, "NewestOnly")

        botCamBalanceRatioRedValue = 1
        botCamBalanceRatioBlueValue = 1

        # turn off Auto white balance
        self.set_selector_to_value(self.nodemap, "BalanceWhiteAuto", "Off")

        # set red value
        self.set_selector_to_value(self.nodemap, "BalanceRatioSelector", "Red")
        self.set_float_value_to_node(self.nodemap, "BalanceRatio", botCamBalanceRatioRedValue)

        # set blue value
        self.set_selector_to_value(self.nodemap, "BalanceRatioSelector", "Blue")
        self.set_float_value_to_node(self.nodemap, "BalanceRatio", botCamBalanceRatioBlueValue)

    def set_trigger_on_inference_ready(self):
        self.set_selector_to_value(self.nodemap, "TriggerSelector", "FrameStart")
        self.set_selector_to_value(self.nodemap, "TriggerMode", "On")
        self.set_selector_to_value(self.nodemap, "TriggerSource", "InferenceReady")

    def disable_isp_processing(self):
        # Filters that are involved in image processing. Disable these to match host inference more accurately.
        for each_node in self.ISP_NODES:
            try:
                self.disable_node_checkbox(self.nodemap, each_node)
            except Exception:
                raise ConfigureCameraError("Failed to disable ISP Node:{}".format(each_node))

    def enable_isp_processing(self):
        for each_node in self.ISP_NODES:
            try:
                self.enable_node_checkbox(self.nodemap, each_node)
            except Exception:
                raise ConfigureCameraError("Failed to enable ISP Node:{}".format(each_node))

    def setup_inference_detection(self):
        self.set_selector_to_value(self.nodemap, "InferenceNetworkTypeSelector", "Detection")
        self.enable_node_checkbox(self.nodemap, "InferenceEnable")

    def setup_inference_classification(self):
        self.set_selector_to_value(self.nodemap, "InferenceNetworkTypeSelector", "Classification")
        self.enable_node_checkbox(self.nodemap, "InferenceEnable")

    def enable_chunk_data_for_detection(self):
        self.enable_node_checkbox(self.nodemap, "ChunkModeActive")

        self.set_selector_to_value(self.nodemap, "ChunkSelector", "InferenceBoundingBoxResult")
        self.enable_node_checkbox(self.nodemap, "ChunkEnable")

        self.set_selector_to_value(self.nodemap, "ChunkSelector", "InferenceFrameId")
        self.enable_node_checkbox(self.nodemap, "ChunkEnable")

    def enable_chunk_data_for_classification(self):
        self.enable_node_checkbox(self.nodemap, "ChunkModeActive")

        self.set_selector_to_value(self.nodemap, "ChunkSelector", "InferenceResult")
        self.enable_node_checkbox(self.nodemap, "ChunkEnable")

        self.set_selector_to_value(self.nodemap, "ChunkSelector", "InferenceConfidence")
        self.enable_node_checkbox(self.nodemap, "ChunkEnable")

        self.set_selector_to_value(self.nodemap, "ChunkSelector", "InferenceFrameId")
        self.enable_node_checkbox(self.nodemap, "ChunkEnable")

    def setup_inference_camera_defaults(self):

        # self.set_selector_to_value(self.nodemap, "UserSetSelector", "Default")
        # camera.UserSetLoad.Execute()

        self.set_selector_to_value(self.nodemap, "AcquisitionMode", "Continuous")

        # acquisition
        self.set_selector_to_value(self.nodemap, "TriggerSelector", "FrameStart")

        if self.SOFTWARE_TRIGGER:
            # set MASTER_INPUT_LINE to Line1 to enable the button
            self.set_selector_to_value(self.nodemap, "TriggerSource", "Software")
            self.set_selector_to_value(self.nodemap, "TriggerMode", "On")
        else:
            # trigger mode off
            self.set_selector_to_value(self.nodemap, "TriggerMode", "Off")

        # turn off Exposure Auto
        self.set_selector_to_value(self.nodemap, "ExposureAuto", "Continuous")
        # turn off Auto white balance
        self.set_selector_to_value(self.nodemap, "BalanceWhiteAuto", "Continuous")

        # digital IO line selector 0
        # self.set_selector_to_value(self.nodemap, "LineSelector", self.MASTER_OUTPUT_LINE)

        # digital IO line mode output
        # self.set_selector_to_value(self.nodemap, "LineMode", "Output")

        # digital IO line source exposure active
        # self.set_selector_to_value(self.nodemap, "LineSource", "ExposureActive")

        self.set_selector_to_value(self.nodemapTL, self.STREAM_BUFFER_HANDLING, "NewestOnly")
        # setting master framerate to a lower framerate
        # self.enable_node_checkbox(self.nodemap, "AcquisitionFrameRateEnable")
        # self.set_trigger_on_inference_ready(camera)
        # self.camera.AcquisitionFrameRate.SetValue(self.FRAME_RATE)

        # self.set_float_value_to_node(self.nodemap, "InferenceBoundingBoxThreshold", self.BOUNDING_BOX_THRESHOLD)
        self.disable_isp_processing()
        self.setup_inference_classification()
        self.enable_chunk_data_for_classification()

    def get_next_image(self):
        if not self.CAMERA_STREAMING:
            self.CAMERA_STREAMING = True
            self.camera.BeginAcquisition()
        if self.SOFTWARE_TRIGGER:
            self.camera.TriggerSoftware.Execute()
            sleep(0.1)
            try:
                # flushing images
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            sleep(0.1)
            self.camera.TriggerSoftware.Execute()
            try:
                image = self.camera.GetNextImage(2000)
            except PySpin.SpinnakerException:
                self.camera.TriggerSoftware.Execute()
                image = self.camera.GetNextImage()
        else:
            image = self.camera.GetNextImage()

        image_converted = image.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)
        image.Release()

        return image_converted

    def get_next_image_and_inference_result(self):
        if not self.CAMERA_STREAMING:
            self.CAMERA_STREAMING = True
            self.camera.BeginAcquisition()
        if self.SOFTWARE_TRIGGER:
            self.camera.TriggerSoftware.Execute()
            sleep(0.1)
            try:
                # flushing images
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(100).Release()
            except:
                pass
            sleep(0.1)
            self.camera.TriggerSoftware.Execute()
            try:
                image = self.camera.GetNextImage(2000)
            except PySpin.SpinnakerException:
                self.camera.TriggerSoftware.Execute()
                image = self.camera.GetNextImage()
        else:
            image = self.camera.GetNextImage()

        c_data = image.GetChunkData()

        inference_confidence = c_data.GetInferenceConfidence()
        inference_result = c_data.GetInferenceResult()
        inference_time = self.get_float_value_from_node(self.nodemap, "InferenceTime")

        image_converted = image.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)
        image.Release()

        return image_converted, (inference_result, inference_confidence, inference_time)

    def get_inference_result_and_confidence(self):
        if not self.CAMERA_STREAMING:
            self.CAMERA_STREAMING = True
            self.camera.BeginAcquisition()
        if self.SOFTWARE_TRIGGER:
            self.camera.TriggerSoftware.Execute()
            sleep(0.1)
            try:
                self.camera.GetNextImage(1).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(1).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(1).Release()
            except:
                pass
            try:
                self.camera.GetNextImage(1).Release()
            except:
                pass
            sleep(0.1)
            self.camera.TriggerSoftware.Execute()
            try:
                image = self.camera.GetNextImage()
            except PySpin.SpinnakerException:
                self.camera.TriggerSoftware.Execute()
                image = self.camera.GetNextImage()
        else:
            image = self.camera.GetNextImage()

        c_data = image.GetChunkData()

        inference_confidence = c_data.GetInferenceConfidence()
        inference_result = c_data.GetInferenceResult()
        inference_time = self.get_float_value_from_node(self.nodemap, "InferenceTime")

        image.Release()

        return inference_result, inference_confidence, inference_time

    @staticmethod
    def get_bounding_box_results_from_image(spinnaker_image):
        ndarr = spinnaker_image.GetNDArray()
        (r,c) = ndarr.shape
        chunk_data = spinnaker_image.GetChunkData()
        result = []
        inference_bounding_box_result = chunk_data.GetInferenceBoundingBoxResult()
        bounding_box_count = inference_bounding_box_result.GetBoxCount()
        for i in range(bounding_box_count):
            bounding_box = inference_bounding_box_result.GetBoxAt(i)
            if bounding_box.boxType != PySpin.INFERENCE_BOX_TYPE_RECTANGLE:
                continue
            entry = (bounding_box.classId,
                     bounding_box.confidence,
                     np.clip(bounding_box.rect.topLeftXCoord/c,0,1),
                     np.clip(bounding_box.rect.topLeftYCoord/r,0,1),
                     np.clip(bounding_box.rect.bottomRightXCoord/c,0,1),
                     np.clip(bounding_box.rect.bottomRightYCoord/r,0,1))
            result.append(entry)

        return result

    @staticmethod
    def get_frame_ids_from_image(spinnaker_image):
        chunk_data = spinnaker_image.GetChunkData()
        return chunk_data.GetFrameID()

    def __del__(self):
        try:
            if self.CAMERA_STREAMING:
                self.camera.EndAcquisition()
            self.camera.DeInit()
            del self.camera
            self.cam_list.Clear()
            self.system.ReleaseInstance()
        except:
            pass


if __name__ == '__main__':
    print(__name__)
    import cv2

    test_camera = Camera("19175370")

    img = test_camera.get_next_image().GetNDArray()
    height, width, channels = img.shape

    max_window_height = 780
    max_window_width = 1620

    resize_please = False

    if width > max_window_width or height > max_window_height:
        resize_please = True
    scale_ratio = 0
    if resize_please:
        width_ratio = max_window_width/width
        height_ratio = max_window_height/height
        scale_ratio = height_ratio
        if width_ratio > height_ratio:
            scale_ratio = width_ratio

    while(True):
        # Capture frame-by-frame
        img = test_camera.get_next_image().GetNDArray()
        width = int(img.shape[1] * scale_ratio)
        height = int(img.shape[0] * scale_ratio)
        dim = (width, height)
        resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

        # Display the resulting frame
        cv2.imshow("lol", resized)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("end")
