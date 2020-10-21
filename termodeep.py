import json
import os
import sys
import threading
from base64 import b64encode
import sentry_sdk
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, g

import scripts.hotspot_manager as hpm

from scripts.barcode_reader import BarcodeReader, BarcodeType
from scripts.camera_thermal import CameraThermal
from scripts.database import get_db, dictfetchone, init_db, dictfetchall
# from scripts.gui import GUI
from serial.tools.list_ports import comports

from scripts.helpers import get_mac, disable_logging
from scripts.record_completer import RecordCompleter
from scripts.stream_thermal_camera import StreamThermalCamera
import picamera

sentry_sdk.init("https://7069acf6d8794790a2f5bcc94397b1c1@o425810.ingest.sentry.io/5365893")

MAC_ADDRESS = get_mac()
disable_logging()

rgb_cam = picamera.PiCamera()

rgb_cam.rotation = 180
rgb_cam.hflip = True
# rgb_cam.resolution = (320, 240)
rgb_cam.resolution = (640, 480)

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        thermal_image = frame.get('thermal_image')
        # print(frame.get('alert'))
        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + thermal_image + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(CameraThermal()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/barcode_scan', methods=['POST'])
def barcode_scan():
    content = request.json
    data = content.get('data')

    p_extra_json = data.get('extra_json')
    if p_extra_json is not None:
        p_extra_json = json.dumps(p_extra_json)

    db = get_db()
    cur = db.cursor()
    cur.execute(
        """INSERT INTO records (mac_address, p_barcode_type, p_identification, p_timestamp, p_name, p_last_name, 
        p_gender, p_birth_date, p_expiration_date, p_blood_type, p_extra_json, p_extra_txt, p_alert) VALUES 
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (MAC_ADDRESS, content.get('barcode_type'), data.get('identification'), content.get('timestamp'),
         data.get('name'), data.get('last_name'), data.get('gender'), data.get('birth_date'),
         data.get('expiration_date'), data.get('blood_type'), p_extra_json, data.get('extra_txt'), data.get('alert')))
    db.commit()

    RecordCompleter(cur.lastrowid, rgb_cam)
    return jsonify(data)


@app.route('/latest_record')
def latest_record():
    now = datetime.now().isoformat()
    cur = get_db().cursor()
    query = """SELECT record_id, p_identification, p_timestamp, p_name, p_last_name, p_gender, p_birth_date,
    p_expiration_date, p_blood_type, t_timestamp, t_temperature_p80, t_temperature_body, t_alert, p_alert
    FROM records WHERE(cast(JULIANDAY('{}') - JULIANDAY(p_timestamp)  as float ) *60 * 60 * 24) < {}
    ORDER BY record_id DESC LIMIT 1""".format(now, 5)
    cur.execute(query)
    data = dictfetchone(cur)
    return jsonify(data)


@app.route('/record_thermal')
def record_thermal():
    record_id = request.args.get('record_id', type=int, default=None)
    if record_id is not None:

        cur = get_db().cursor()
        cur.execute("""SELECT record_id, t_image_thermal FROM records WHERE record_id=? LIMIT 1""", (record_id,))
        data = dictfetchone(cur)

        image_thermal = data.get('t_image_thermal')
        if image_thermal is not None:
            data['t_image_thermal'] = b64encode(image_thermal).decode("utf-8")

        return jsonify(data)
    else:
        return None


@app.route('/record_rgb')
def record_rgb():
    record_id = request.args.get('record_id', type=int, default=None)
    if record_id is not None:

        cur = get_db().cursor()
        cur.execute("""SELECT record_id, t_image_rgb FROM records WHERE record_id=? LIMIT 1""", (record_id,))
        data = dictfetchone(cur)

        image_rgb = data.get('t_image_rgb')
        if image_rgb is not None:
            data['t_image_rgb'] = b64encode(image_rgb).decode("utf-8")

        return jsonify(data)
    else:
        return None


@app.route('/records')
def records():
    page_size = request.args.get('page_size', type=int, default=6)
    page = request.args.get('page', type=int, default=1)
    offset = (page - 1) * page_size
    cur = get_db().cursor()

    cur.execute("SELECT COUNT(1) as total FROM records")
    total = dictfetchone(cur)['total']

    num_pages = -(-total // page_size)

    cur.execute("SELECT * FROM records ORDER BY record_id DESC LIMIT ? OFFSET ?", (page_size, offset))
    data = dictfetchall(cur)

    for record in data:
        image_rgb = record.get('t_image_rgb')
        if image_rgb is not None:
            record['t_image_rgb'] = b64encode(image_rgb).decode("utf-8")

    for record in data:
        image_thermal = record.get('t_image_thermal')
        if image_thermal is not None:
            record['t_image_thermal'] = b64encode(image_thermal).decode("utf-8")

    response = {
        'count': total,
        'next': page + 1 if page < num_pages else None,
        'previous': page - 1 if page > 0 else None,
        'results': data
    }

    return jsonify(response)


@app.route('/wifi_status')
def wifi_status():
    ip = hpm.get_wlan0_ip()
    # Conected to HotSpot
    if ip[:7] == "10.0.0.":
        ssid = hpm.get_hostapd_name()
    # Connected to wlan
    else:
        ssid = hpm.get_ssid_name()
    response = {
        'ssid': ssid,
        'ip': ip
    }
    return jsonify(response)


@app.route('/wifi_settings', methods=['POST'])
def wifi_settings():
    data = request.json
    print(data)

    print(hpm.get_networks())
    hpm.set_new_wifi(data['ssid'], data['password'])
    hpm.change_network()
    hpm.reset_autohotspot()

    return jsonify(data)


def flask_main():
    init_db(app)

    # app.run(host='0.0.0.0', port='80', threaded=True)
    app.run(host='0.0.0.0', port=8080, threaded=True)


# def tk_main():
#     # ports = [(port.device, port.description) for port in comports()]
#     port_device = []
#     port_description = []
#     port_vid = []
#     for port in comports():
#         port_device.append(port.device)
#         port_description.append(port.description)
#         port_vid.append(port.vid)
#
#     ports = (port_device, port_description, port_vid)
#     # print(ports)
#     # ports = [port.device for port in comports()]
#     GUI(ports, start_app)


# def start_app(root, cam_port, barcode_port):
#     thermal_camera_stream = StreamThermalCamera(cam_port)
#     thermal_camera_stream.start()
#
#     # from tests.stream_simulator import StreamSimulator
#     # simulator = StreamSimulator()
#     # simulator.start()
#
#     flask_thread = threading.Thread(target=flask_main)
#     flask_thread.start()
# S
#     # Start camera thread
#     CameraThermal()
#
#     if barcode_port is not None:
#         barcode_reader = BarcodeReader(barcode_port)
#         if barcode_reader.initiated:
#             barcode_reader.start()
#
#     GUI.show_running(root, cam_port, barcode_port)


barcode_allowlist = [44953]


def start_app():
    thermal_camera_stream = StreamThermalCamera("/dev/ttyS0")
    thermal_camera_stream.start()

    # from tests.stream_simulator import StreamSimulator
    # simulator = StreamSimulator()
    # simulator.start()

    flask_thread = threading.Thread(target=flask_main)
    flask_thread.start()

    # Start camera thread
    CameraThermal()

    # Barcode scanner
    port_device = []
    port_description = []
    port_vid = []
    for port in comports():
        port_device.append(port.device)
        port_description.append(port.description)
        port_vid.append(port.vid)

    ports = (port_device, port_description, port_vid)

    barcode_port = None
    barcode_ports = [[], [], []]
    for (com, desc, vid) in zip(ports[0], ports[1], ports[2]):
        # print(com, desc, vid)
        if vid in barcode_allowlist:
            barcode_ports[0].append(com)
            barcode_ports[1].append(desc)
            barcode_ports[2].append(vid)
            barcode_port = com

    if barcode_port is not None:
        barcode_reader = BarcodeReader(barcode_port)
        if barcode_reader.initiated:
            barcode_reader.start()


if __name__ == '__main__':
    # tk_main()
    start_app()

    # from tests.stream_simulator import StreamSimulator
    #
    # simulator = StreamSimulator()
    # simulator.start()
    #
    # # Start camera thread
    # CameraThermal()
    #
    # flask_thread = threading.Thread(target=flask_main)
    # flask_thread.start()
    #
    # barcode_reader = BarcodeReader('COM3')
    # if barcode_reader.initiated:
    #     barcode_reader.start()
