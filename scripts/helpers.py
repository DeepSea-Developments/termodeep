import sys
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(dir_path))

import argparse
import logging
import sys
import uuid
import configparser
import threading 

from serial.tools.list_ports import comports

#Set stop signal - camera thread
global stop_camera_thread
stop_camera_thread = threading.Event()

#Set path 
global conf_path
conf_path = dir_path[0:-8] + '/conf/'


def get_args():
    parser = argparse.ArgumentParser(description='Start Flask Server.')
    parser.add_argument("-c", "--calibrating", help="Set when calibrating", action="store_true")
    parser.add_argument("-z", "--cloud", help="Upload data to cloud", action="store_true")
    parser.add_argument("-u", "--simulator", help="Simulate the RPI", action="store_true")
    parser.add_argument("-r", "--ref-temp", help="Reference temperature", type=float)
    parser.add_argument("-i", "--ref-height", help="Reference height in pixels", type=int)

    # Reference measurement parsers
    parser.add_argument("-x", "--ref-x", help="top left x coordinate of reference", type=int)
    parser.add_argument("-y", "--ref-y", help="top left y coordinate of reference", type=int)
    parser.add_argument("-a", "--ref-measure-weight", help="Reference measure weight in pixels", type=int)
    parser.add_argument("-m", "--ref-measure-height", help="Reference measure height in pixels", type=int)

    parser.add_argument("-s", "--sensitivity", help="Camera sensitivity", type=float)
    parser.add_argument("-t", "--threshold", help="Human temperature threshold", type=float)
    parser.add_argument("-f", "--floor", help="Image temperature floor", type=float)
    parser.add_argument("-e", "--ceil", help="Image temperature ceiling", type=float)
    parser.add_argument("-w", "--warning-temp", help="Temperature threshold for a warning", type=float)
    parser.add_argument("-d", "--danger-temp", help="Temperature threshold for danger", type=float)
    parser.add_argument("-l", "--capture-wait-time",
                        help="Time to wait for capture after a person is identified in miliseconds", type=int)

    parser.add_argument("-q", "--qrexternal", help="Enable external QR", type=float)

    return parser.parse_args()


def get_mac():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
    return mac


def disable_logging():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    log.disabled = True

    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None


def get_ports():
    port_device = []
    port_description = []
    port_vid = []

    for port in comports():
        port_device.append(port.device)
        port_description.append(port.description)
        port_vid.append(port.vid)

    ports = (port_device, port_description, port_vid)
    return ports


def load_config():
    config = configparser.ConfigParser()
    config.read(conf_path + 'termodeep.ini')

    if 'CUSTOM' in config:
        conf = config['CUSTOM']
    else:
        conf = config['DEFAULT']

    return conf
