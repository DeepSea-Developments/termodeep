import sqlite3
import threading
from datetime import datetime, timedelta
from io import BytesIO

from scripts.cloud_synchronizer import upload_record_by_id
from scripts.helpers import get_args
from scripts.camera_thermal import CameraThermal
from scripts.database import DATABASE


class RecordCompleter:
    thread = None
    record_id = None
    db = None

    DELAY = 1
    ALERT_WARNING_TEMP = 37.5
    ALERT_DANGER_TEMP = 38

    ALERT_SAFE = 0
    ALERT_WARNING = 1
    ALERT_DANGER = 2

    JPEG_QUALITY = 85

    def __init__(self, record_id, rgb_camera, delay=2000):
        # print('init record_completer')
        self.record_id = record_id
        self.DELAY = delay
        self.rgb_camera = rgb_camera

        args = get_args()
        if args.warning_temp is not None:
            self.ALERT_WARNING_TEMP = args.warning_temp
        if args.danger_temp is not None:
            self.ALERT_DANGER_TEMP = args.danger_temp
        if args.capture_wait_time is not None:
            self.DELAY = args.capture_wait_time

        #RecordCompleter.thread = threading.Thread(target=self._thread)
        #RecordCompleter.thread.start()
        self._thread()

    def calculate_alert(self, temperature_body):
        alert = self.ALERT_SAFE
        if temperature_body > self.ALERT_DANGER_TEMP:
            alert = self.ALERT_DANGER
        elif temperature_body > self.ALERT_WARNING_TEMP:
            alert = self.ALERT_WARNING
        return alert

    def _thread(self):
    
    # Take picture

        camera = CameraThermal()

        end_time = datetime.now() + timedelta(milliseconds=self.DELAY)

        while True:
            frame = camera.get_frame()
            temperatures = frame.get('temperatures')
            if temperatures is None:
                # Restart timer
                end_time = datetime.now() + timedelta(milliseconds=self.DELAY)
            elif datetime.now() > end_time:
                # Take picture
                image_stream = BytesIO()
                self.rgb_camera.capture(image_stream, format='jpeg', quality=self.JPEG_QUALITY)
                image_rgb = image_stream.getvalue()

                db = sqlite3.connect(DATABASE)
                cur = db.cursor()

                cur.execute(
                    """UPDATE records SET t_timestamp = ?, t_temperature_mean = ?, t_temperature_median = ?, 
                    t_temperature_min = ?, t_temperature_max = ?, t_temperature_p10 = ?, t_temperature_p20 = ?, 
                    t_temperature_p30 = ?, t_temperature_p40 = ?, t_temperature_p50 = ?, t_temperature_p60 = ?, 
                    t_temperature_p70 = ?, t_temperature_p80 = ?, t_temperature_p90 = ?, t_temperature_body = ?,
                    t_image_thermal = ?, t_image_rgb = ?, t_alert = ? 
                    WHERE record_id = ?""",
                    (datetime.now().isoformat(), temperatures.get('temperature_mean'),
                     temperatures.get('temperature_median'), temperatures.get('temperature_min'),
                     temperatures.get('temperature_max'), temperatures.get('temperature_p10'),
                     temperatures.get('temperature_p20'), temperatures.get('temperature_p30'),
                     temperatures.get('temperature_p40'), temperatures.get('temperature_p50'),
                     temperatures.get('temperature_p60'), temperatures.get('temperature_p70'),
                     temperatures.get('temperature_p80'), temperatures.get('temperature_p90'),
                     temperatures.get('temperature_body'), frame.get('thermal_image'), image_rgb,
                     self.calculate_alert(temperatures.get('temperature_body')), self.record_id))
                db.commit()

                args = get_args()
                if args.cloud:
                    upload_record_by_id(self.record_id)
                # print('Stored')
                break
