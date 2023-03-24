#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO
import serial
import time
import sys
import os
import git

ser = serial.Serial('/dev/ttyS0',115200)
ser.flushInput()

power_key = 6
buffer = ''
buffer_data = ''
time_count = 0
file_name = 'd4113b3c-f400-4efb-bf55-9e46dca43589.csv'

class GPSInfo:
    def __init__(self, longitude, latitude, date, time):
        self.longitude = longitude
        self.latitude = latitude
        self.date = date
        self.time = time

def send_at(command,back,timeout):
    buffer = ''
    ser.write((command+'\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.01)
        buffer = ser.readline(ser.inWaiting())
        #buffer = ser.read(ser.inWaiting())
    if buffer != '':
        if isinstance(buffer, bytes):
            if back not in buffer.decode():
                print(command + ' ERROR')
                if isinstance(buffer, bytes):
                    buffer = buffer.decode()
                print(command + ' back:\t' + buffer)
                return 0
            else:
                #print(buffer.decode())
                return 1
    else:
        print('GPS is not ready')
        return 0

def get_gps_position():
    rec_null = True
    answer = 0
    print('Start GPS session...')
    buffer = ''
    send_at('AT+CGPS=1,1','OK',1)
    time.sleep(2)
    while rec_null:
        answer = send_at('AT+CGPSINFO','+CGPSINFO: ',1)
        if 1 == answer:
            answer = 0
            if ',,,,,,' in buffer:
                print('GPS is not ready')
                rec_null = False
                time.sleep(1)
            else:
                if buffer is not None:
                    if isinstance(buffer, bytes):
                        gps_info = parse_gps_info(buffer.decode())
                        print(gps_info.longitude, gps_info.latitude, gps_info.date, gps_info.time)
                        print('writing to file')
                        write_to_file(gps_info)
        else:
            print('error %d'%answer)
            buffer = ''
            send_at('AT+CGPS=0','OK',1)
            return False
        time.sleep(30)

def parse_gps_info(gps_string):
    gps_info_list = gps_string.split(',')
    longitude = gps_info_list[1]
    latitude = gps_info_list[2]
    date = gps_info_list[3]
    time = gps_info_list[4]
    return GPSInfo(longitude, latitude, date, time)

def connect_to_internet():
    APN = 'hologram'
    send_at('AT+CSQ','OK',1)
    send_at('AT+CREG?','+CREG: 0,1',1)
    send_at('AT+CPSI?','OK',1)
    send_at('AT+CGREG?','+CGREG: 0,1',0.5)
    send_at('AT+CGSOCKCONT=1,\"IP\",\"'+APN+'\"','OK',1)
    send_at('AT+CSOCKSETPN=1', 'OK', 1)
    send_at('AT+CIPMODE=0', 'OK', 1)
    send_at('AT+NETOPEN', '+NETOPEN: 0',5)
    send_at('AT+IPADDR', '+IPADDR:', 1)
    
def disconnect_from_internet():
    send_at('AT+CIPCLOSE=0','+CIPCLOSE: 0,0',15)
    send_at('AT+NETCLOSE', '+NETCLOSE: 0', 1)

def write_to_file(gps_info):
    with open(file_name, 'w') as f:
        output_string = f"{gps_info.longitude}, {gps_info.latitude}, {gps_info.date}, {gps_info.time}\n"
        print(output_string)
        f.write(output_string)
        f.flush()

def power_on(power_key):
    print('SIM7600X is starting:')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(power_key,GPIO.OUT)
    time.sleep(0.1)
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(2)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(20)
    ser.flushInput()
    print('SIM7600X is ready')

def power_down(power_key):
    print('SIM7600X is logging off:')
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(3)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(18)
    print('Good bye')

def commit_and_push():
    try:
        repo = git.Repo(os.getcwd())
        repo.git.add(file_name)
        repo.git.commit('-m', 'Updated by Asset Tracker')
        origin = repo.remote(name='origin')
        origin.push()
        print('File committed and pushed to Github')
    except git.exc.GitCommandError as e:
        print(f"Error occurred while committing and pushing to Github: {e}")

try:
    power_on(power_key)
    get_gps_position()
    connect_to_internet()
    commit_and_push()
    disconnect_from_internet()
    power_down(power_key)
except Exception as e:
    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

