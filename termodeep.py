import sys
import os
# dir_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.abspath(dir_path + '/scripts/'))

import threading
import sentry_sdk

from termodeep_flask import flask_main
from scripts.barcode_reader import BarcodeReader
from scripts.camera_thermal import CameraThermal
from scripts.cloud_synchronizer import CloudSynchronizer
from scripts.helpers import get_args, disable_logging


def start_stream():
    from scripts.stream_thermal_camera import StreamThermalCamera
    thermal_camera_stream = StreamThermalCamera("/dev/ttyS0")
    thermal_camera_stream.start()


if __name__ == '__main__':
    args = get_args()
    disable_logging()

    if not args.simulator:  # Use in RPI
        sentry_sdk.init("https://7069acf6d8794790a2f5bcc94397b1c1@o425810.ingest.sentry.io/5365893")
        start_stream()
        barcode_reader = BarcodeReader()
    else:  # Use in Computer
        barcode_reader = BarcodeReader()

    flask_thread = threading.Thread(target=flask_main)
    flask_thread.start()

    # Cloud synchronizer
    if args.cloud:
        cloud = CloudSynchronizer()
        cloud.start()

    if barcode_reader.initiated:
        barcode_reader.start()
