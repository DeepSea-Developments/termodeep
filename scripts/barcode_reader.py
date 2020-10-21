import json
import re
import threading
from datetime import datetime

import requests
import serial
from enum import Enum
from time import sleep


class Person:
    def __init__(self, identification, name, last_name, gender, birth_date, expiration_date=None,
                 blood_type=None):
        self.identification = identification
        self.name = name
        self.last_name = last_name
        self.gender = gender
        self.birth_date = birth_date
        self.expiration_date = expiration_date
        self.blood_type = blood_type

    @staticmethod
    def append_names(name1, name2):
        names = [name1, name2]
        return ' '.join(filter(None, names))


class BarcodeType(Enum):
    QR = 0
    CEDULA_COLOMBIA = 1
    CEDULA_COSTA_RICA = 2


class BarcodeReader:
    KEYS_ARRAY_CR = [0x27, 0x30, 0x04, 0xA0, 0x00, 0x0F, 0x93, 0x12, 0xA0, 0xD1, 0x33, 0xE0, 0x03, 0xD0, 0x00, 0xDf,
                     0x00]
    thread = None
    initiated = False

    def __init__(self, port, baudrate=115200):
        try:
            self.serial = serial.Serial(port=port, baudrate=baudrate)
            self.initiated = True
        except Exception as e:
            print(e)

    def __del__(self):
        self.serial.close()

    @staticmethod
    def _decode_string(values):
        string_data = ''
        for data in values:
            if data != b'\x00':
                string_data = string_data + data.decode('utf-8')
        return string_data

    def get_reading(self):
        msg = []
        if self.serial.in_waiting > 0:
            data_size = self.serial.in_waiting
            for i in range(data_size):
                value = self.serial.read()
                msg.append(value)

            try:

                if len(msg) == 531:
                    code_type = BarcodeType.CEDULA_COLOMBIA
                    person = Person(
                        identification=self._decode_string(msg[48:58]).lstrip('0'),
                        name=Person.append_names(self._decode_string(msg[104:127]),
                                                 self._decode_string(msg[127:150])),
                        last_name=Person.append_names(self._decode_string(msg[58:81]),
                                                      self._decode_string(msg[81:104])),
                        gender=self._decode_string(msg[151:152]),
                        birth_date=self._decode_string(msg[152:156]) + '-' + self._decode_string(
                            msg[156:158]) + '-' + self._decode_string(msg[158:160]),
                        blood_type=self._decode_string(msg[166:169])
                    )

                elif len(msg) == 700:
                    d = ""
                    j = 0
                    count = 0
                    for _value in msg:
                        if j == 17:
                            j = 0
                        # __value = int(_value)
                        c = self.KEYS_ARRAY_CR[j] ^ _value[0]
                        if re.match("^[a-zA-Z0-9]*$", chr(c)):
                            d = d + chr(c)
                            count = count + 1
                        else:
                            d += ' '
                        j = j + 1

                    code_type = BarcodeType.CEDULA_COSTA_RICA
                    person = Person(
                        identification=d[0:9].strip(),
                        name=d[61:91].strip(),
                        last_name=Person.append_names(d[9:35].strip(), d[35:61].strip()),
                        gender=d[91].strip(),
                        birth_date=d[92:96].strip() + '-' + d[96:98].strip() + '-' + d[98:100].strip(),
                        expiration_date=d[100:104].strip() + '-' + d[104:106].strip() + '-' + d[106:108].strip(),
                    )
                else:
                    return
                return {
                    'barcode_type': code_type.value,
                    'data': person.__dict__,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                print(e)
                return
        else:
            sleep(0.1)

    def _thread(self):
        while True:
            reading = self.get_reading()
            if reading:
                requests.post('http://127.0.0.1:8080/barcode_scan', json=reading)

    def start(self):
        """Start the background simulator thread if it isn't running yet."""
        if self.thread is None:
            # start background frame thread
            self.thread = threading.Thread(target=self._thread)
            self.thread.start()
