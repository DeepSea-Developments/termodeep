from scripts.helpers import get_args
from scripts.base_camera import BaseCamera
import socket
import pickle

from scripts.opencv_processing import OpenCVProcessor
import cv2

class CameraThermal(BaseCamera):

    @staticmethod
    def frames():
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.bind(("127.0.0.1", 5001))

        args = get_args()

        # print('Creating OpenCV Processor...')
        processor = OpenCVProcessor(args.calibrating)
        if args.sensitivity is not None:
            processor.CAM_SENSITIVITY = args.sensitivity
        if args.ref_temp is not None:
            processor.REF_TEMP = args.ref_temp
        if args.ref_height is not None:
            processor.REF_HEIGHT = args.ref_height

        if args.ref_measure_height is not None:
            processor.REF_MEASURE_HEIGHT = args.ref_measure_height
        if args.ref_measure_weight is not None:
            processor.REF_MEASURE_WEIGHT = args.ref_measure_weight
        if args.ref_x is not None:
            processor.REF_TOPLEFT_X = args.ref_x
        if args.ref_y is not None:
            processor.REF_TOPLEFT_Y = args.ref_y

        if args.threshold is not None:
            processor.THRESHOLD_HUMAN_TEMP = args.threshold
        if args.floor is not None:
            processor.TEMP_FLOOR = args.floor
        if args.ceil is not None:
            processor.TEMP_CEIL = args.ceil

        while True:
            data, addr = sock.recvfrom(1024 * 64)  # buffer size is 1024 bytes

            frame_raw = pickle.loads(data)

            img_large, temperatures = processor.process_frame(frame_raw)

            frame = {
                'thermal_image': cv2.imencode('.png', img_large)[1].tobytes(),
                'temperatures': temperatures
            }

            yield frame

