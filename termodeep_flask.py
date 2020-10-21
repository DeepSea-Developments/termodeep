import sys
import os

# dir_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.abspath(dir_path + '/scripts/'))
# sys.path.append(os.path.abspath(dir_path + '/scripts/serverside/'))

import json
import scripts.hotspot_manager as hpm
import configparser
import threading
import time
import csv
import random

from base64 import b64encode
from datetime import datetime
from scripts.database import get_db, dictfetchone, init_db, dictfetchall, arrayfetchall, DATABASE
from scripts.helpers import get_mac, stop_camera_thread, load_config, conf_path
from scripts.record_completer import RecordCompleter
from scripts.camera_thermal import CameraThermal

from io import StringIO
from flask import Flask, render_template, Response, request, jsonify, g
from flask import make_response
from flask import send_file

from scripts.serverside.models import TableBuilder

# ---------------------------
# Auxilar functions/clases
# ---------------------------

MAC_ADDRESS = get_mac()

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)


# ---------------------------
# Routes
# ---------------------------

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/index')
@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


@app.route('/erase_db')
def erase_db():
    return html_text


@app.route('/download_db')
def downloadFile():
    # For windows you need to use drive name [ex: F:/Example.pdf]
    path = "/database_v2.db"
    return send_file(path, as_attachment=True)


delete_db_verification_code = random.randint(1000, 9999)


@app.route('/delete_db')
def delete_db():
    code = request.args.get('code')
    if code is None:
        print("Code is None")
        html_text = f"""
                <!DOCTYPE html>
                <html>
                {delete_db_verification_code} <br>
                Now go to /delete_db?code={delete_db_verification_code}
                </html>
                """
    elif int(code) == delete_db_verification_code:
        try:
            os.remove("/"+DATABASE)
        except Exception as e:
            print(f"Erase database error: {e}")
        html_text = """
                <!DOCTYPE html>
                <html>
                Database deleted. Restart the camera
                </html>
                """
    else:
        html_text = """
                <!DOCTYPE html>
                <html>
                Wrong Code
                </html>
                """
    return html_text


@app.route('/registros')
def registros():
    """Records page."""
    return render_template('records.html')


@app.route('/configuracion')
def configuracion():
    """Settings page."""
    return render_template('settings.html')


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
        p_gender, p_birth_date, p_blood_type, p_extra_json, p_extra_txt, p_alert) VALUES 
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (MAC_ADDRESS, content.get('barcode_type'), data.get('identification'), content.get('timestamp'),
         data.get('name'), data.get('last_name'), data.get('gender'), data.get('birth_date'), data.get('blood_type'),
         p_extra_json, data.get('extra_txt'), data.get('alert')))
    db.commit()

    RecordCompleter(cur.lastrowid)
    return jsonify(data)


@app.route('/latest_record')
def latest_record():
    now = datetime.now().isoformat()
    cur = get_db().cursor()
    query = """SELECT record_id, p_identification, p_timestamp, p_name, p_last_name, p_gender, p_birth_date, 
    p_blood_type, t_timestamp, t_temperature_p80, t_temperature_body, t_alert, p_alert
    FROM records WHERE(cast(JULIANDAY('{}') - JULIANDAY(p_timestamp)  as float ) *60 * 60 * 24) < {}
    ORDER BY record_id DESC LIMIT 1""".format(now, 15)
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
    if ip is not None and ip[:7] == "10.0.0.":
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


@app.route('/camera_parameters', methods=['POST'])
def set_camera_parameters():
    data = request.json

    # Use a config file
    config = configparser.ConfigParser()
    config.read(conf_path + 'termodeep.ini')

    if 'CUSTOM' in config:
        config.set('CUSTOM', 'REF_TEMP', str(data['REF_TEMP']))
        config.set('CUSTOM', 'CAM_SENSITIVITY', str(data['CAM_SENSITIVITY']))
        config.set('CUSTOM', 'THRESHOLD_HUMAN_TEMP', str(data['THRESHOLD_HUMAN_TEMP']))
        config.set('CUSTOM', 'ALERT_WARNING_TEMP', str(data['ALERT_WARNING_TEMP']))
        config.set('CUSTOM', 'ALERT_DANGER_TEMP', str(data['ALERT_DANGER_TEMP']))
        config.set('CUSTOM', 'CAPTURE_DELAY', str(data['CAPTURE_DELAY']))
    else:
        config.add_section('CUSTOM')
        config.set('CUSTOM', 'REF_TEMP', str(data['REF_TEMP']))
        config.set('CUSTOM', 'CAM_SENSITIVITY', str(data['CAM_SENSITIVITY']))
        config.set('CUSTOM', 'THRESHOLD_HUMAN_TEMP', str(data['THRESHOLD_HUMAN_TEMP']))
        config.set('CUSTOM', 'ALERT_WARNING_TEMP', str(data['ALERT_WARNING_TEMP']))
        config.set('CUSTOM', 'ALERT_DANGER_TEMP', str(data['ALERT_DANGER_TEMP']))
        config.set('CUSTOM', 'CAPTURE_DELAY', str(data['CAPTURE_DELAY']))

    with open(conf_path + 'termodeep.ini', 'w') as configfile:
        config.write(configfile)

    print('Camera thread restarting ...')
    stop_camera_thread.set()
    time.sleep(0.5)
    stop_camera_thread.clear()
    CameraThermal()

    return jsonify(data)


@app.route('/get_parameters_default')
def get_parameters_default():
    # Use a config file
    config = configparser.ConfigParser()
    config.read(conf_path + 'termodeep.ini')
    conf = config['DEFAULT']

    # Default parameters
    REF_TEMP = conf.get('REF_TEMP')
    CAM_SENSITIVITY = conf.get('CAM_SENSITIVITY')
    THRESHOLD_HUMAN_TEMP = conf.get('THRESHOLD_HUMAN_TEMP')
    ALERT_WARNING_TEMP = conf.get('ALERT_WARNING_TEMP')
    ALERT_DANGER_TEMP = conf.get('ALERT_DANGER_TEMP')
    CAPTURE_DELAY = conf.get('CAPTURE_DELAY')

    data = {
        "REF_TEMP": REF_TEMP,
        "CAM_SENSITIVITY": CAM_SENSITIVITY,
        "THRESHOLD_HUMAN_TEMP": THRESHOLD_HUMAN_TEMP,
        "ALERT_WARNING_TEMP": ALERT_WARNING_TEMP,
        "ALERT_DANGER_TEMP": ALERT_DANGER_TEMP,
        "CAPTURE_DELAY": CAPTURE_DELAY
    }

    return jsonify(data)


# cfernandez - 01/10/2020
@app.route('/get_parameters_last')
def get_parameters_last():
    # Use a config file
    conf = load_config()

    # Default parameters
    REF_TEMP = conf.get('REF_TEMP')
    CAM_SENSITIVITY = conf.get('CAM_SENSITIVITY')
    THRESHOLD_HUMAN_TEMP = conf.get('THRESHOLD_HUMAN_TEMP')
    ALERT_WARNING_TEMP = conf.get('ALERT_WARNING_TEMP')
    ALERT_DANGER_TEMP = conf.get('ALERT_DANGER_TEMP')
    CAPTURE_DELAY = conf.get('CAPTURE_DELAY')

    data = {
        "REF_TEMP": REF_TEMP,
        "CAM_SENSITIVITY": CAM_SENSITIVITY,
        "THRESHOLD_HUMAN_TEMP": THRESHOLD_HUMAN_TEMP,
        "ALERT_WARNING_TEMP": ALERT_WARNING_TEMP,
        "ALERT_DANGER_TEMP": ALERT_DANGER_TEMP,
        "CAPTURE_DELAY": CAPTURE_DELAY
    }

    return jsonify(data)


# cfernandez - 08/10/2020
@app.route('/serverside_table')
def serverside_table():
    sql = """SELECT p_timestamp,
                p_identification,
                p_name,
                p_last_name,
                t_temperature_body,
                t_alert,
                t_image_rgb,
                t_image_thermal,
                CASE
                    WHEN t_alert=0 THEN 'Permitido'
                    WHEN t_alert=1 THEN 'Advertencia'
                    WHEN t_alert=2 THEN 'Peligro'
                    ELSE 'None'
                END as t_alert_2
                FROM records
                ORDER BY record_id DESC"""

    cur = get_db().cursor()
    cur.execute(sql)
    data = dictfetchall(cur)

    for record in data:
        image_rgb = record.get('t_image_rgb')
        if image_rgb is not None:
            record['t_image_rgb'] = b64encode(image_rgb).decode("utf-8")

    for record in data:
        image_thermal = record.get('t_image_thermal')
        if image_thermal is not None:
            record['t_image_thermal'] = b64encode(image_thermal).decode("utf-8")

    table_builder = TableBuilder()
    data = table_builder.collect_data_serverside(request, data)

    return jsonify(data)


# cfernandez - 08/10/2020
@app.route('/records_search')
def records2():
    f_ingreso = str(request.args.get('f_ingreso'))

    sql = """SELECT p_timestamp,
            p_identification,
            p_name,
            p_last_name,
            t_temperature_body,
            t_alert,
            t_image_rgb,
            t_image_thermal
            FROM records 
            WHERE t_alert={}
            ORDER BY record_id DESC""".format(f_ingreso)

    cur = get_db().cursor()
    cur.execute(sql)
    data = dictfetchall(cur)

    for record in data:
        image_rgb = record.get('t_image_rgb')
        if image_rgb is not None:
            record['t_image_rgb'] = b64encode(image_rgb).decode("utf-8")

    for record in data:
        image_thermal = record.get('t_image_thermal')
        if image_thermal is not None:
            record['t_image_thermal'] = b64encode(image_thermal).decode("utf-8")

    table_builder = TableBuilder()
    data = table_builder.collect_data_serverside(request, data)

    return jsonify(data)


# cfernandez - 12/10/2020
@app.route('/records_csv')
def records_csv():
    f_ingreso = str(request.args.get('f_ingreso'))

    sql = """SELECT p_timestamp, 
            p_identification, 
            p_name, 
            p_last_name, 
            t_temperature_body,
            CASE
                WHEN t_alert=0 THEN 'Permitido'
                WHEN t_alert=1 THEN 'Advertencia'
                WHEN t_alert=2 THEN 'Peligro'
                ELSE 'None'
            END as t_alert
            FROM records 
            WHERE t_alert={}
            ORDER BY record_id DESC""".format(f_ingreso)

    cur = get_db().cursor()
    cur.execute(sql)
    data = arrayfetchall(cur)

    data_cols = ['FECHA Y HORA', 'IDENTIFICACION', 'NOMBRES', 'APELLIDOS', 'TEMPERATURA', 'INGRESO']
    data.insert(0, data_cols)

    si = StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerows(data)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=records_termodeep.csv"
    output.headers["Content-type"] = "text/csv"

    return output


# ---------------------------
# Main app
# ---------------------------
def flask_main():
    init_db(app)

    # App.run(host='0.0.0.0', port='80', threaded=True)
    app.run(host='0.0.0.0', port=8080, threaded=True)

    # Start camera thread
    CameraThermal()
