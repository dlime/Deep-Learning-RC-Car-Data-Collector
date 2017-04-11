#!/usr/bin/env python
import video_dir
import car_dir
import motor
from socket import *
import time
import threading
import cv2
import csv
import json
from keras.models import model_from_json
import numpy as np

recording_enabled_lock = threading.Lock()
recording_enabled = False

predicting_enabled_lock = threading.Lock()
predicting_enabled = False

ctrl_cmd = ['forward', 'backward', 'left', 'right', 'stop', 'read cpu_temp', 'home', 'distance', 'x+', 'x-', 'y+', 'y-',
            'xy_home', 'toggleRecordTrue', 'toggleRecordFalse', 'toggleAutonomousDriveTrue',
            'toggleAutonomousDriveFalse']

busnum = 1  # Edit busnum to 0, if you uses Raspberry Pi 1 or 0

HOST = ''  # The variable of HOST is null, so the function bind( ) can be bound to all valid addresses.
PORT = 21567
BUFSIZ = 1024  # Size of the buffer
ADDR = (HOST, PORT)
IMAGE_SIZE = [480, 640]

tcpSerSock = socket(AF_INET, SOCK_STREAM)  # Create a socket.
tcpSerSock.bind(ADDR)  # Bind the IP address and port number of the server.
tcpSerSock.listen(5)  # The parameter of listen() defines the number of connections permitted at one time. Once the
# connections are full, others will be rejected.

video_dir.setup(busnum=busnum)
car_dir.setup(busnum=busnum)
motor.setup(busnum=busnum)  # Initialize the Raspberry Pi GPIO connected to the DC motor.
video_dir.home_x_y()
car_dir.home()


def get_recording_enabled():
    global recording_enabled_lock

    recording_enabled_lock.acquire()
    value = recording_enabled
    recording_enabled_lock.release()

    return value


def get_predicting_enabled():
    global predicting_enabled_lock

    predicting_enabled_lock.acquire()
    value = predicting_enabled
    predicting_enabled_lock.release()

    return value


def predicting_setup():
    global predicting_run_event, steering_angle_predictor_thread, model
    predicting_run_event = threading.Event()
    predicting_run_event.set()
    steering_angle_predictor_thread = threading.Thread(target=predicting_loop)

    print 'Loading model'
    with open('CNN/model.json', 'r') as model_file:
        model = model_from_json(json.load(model_file))

    print 'Compiling model'
    model.compile("adam", "mse")
    model.load_weights('CNN/model.h5')

    # TODO: do an empty predict, it's an hack that make the model fully load and give real time prediction later
    temp_steering_angle = int(model.predict(np.zeros((3, IMAGE_SIZE[0], IMAGE_SIZE[1])), batch_size=1))


def predicting_loop():
    global video_capture, image_counter, writer, recording_enabled, csv_file, model
    while predicting_run_event.is_set():
        if not get_predicting_enabled():
            return

        ret, image = video_capture.read()
        if not ret:
            return

        image_normalized = image / 127.5 - 1.

        predicted_steering_angle = int(model.predict(image_normalized, batch_size=1))

        print 'predicted_steering_angle(int) = %d' % predicted_steering_angle
        car_dir.turn_by(predicted_steering_angle)
        time.sleep(0.2)


def recording_setup():
    global csv_file, image_counter, writer, recording_thread, recording_run_event
    image_counter = 0

    video_capture = cv2.VideoCapture(0)
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    if not video_capture.isOpened():
        print("Error: Camera didn't open for capture.")

    csv_file = open('IMG/driving_log.csv', 'w')
    writer = csv.writer(csv_file)

    recording_run_event = threading.Event()
    recording_run_event.set()
    recording_thread = threading.Thread(target=recording_loop)


def recording_loop():
    global video_capture, image_counter, writer, recording_enabled, csv_file
    while recording_run_event.is_set():
        if not get_recording_enabled():
            return

        ret, image = video_capture.read()
        if not ret:
            return
        image_path = "IMG/central-" + str(image_counter) + ".jpg"
        writer.writerow([image_path, car_dir.get_current_steering_value()])
        cv2.imwrite(image_path, image)
        image_counter += 1
        print 'image stored..'
        time.sleep(0.1)


def setup():
    global tcpCliSock, datacolletor, video_capture

    print 'Waiting for connection...'
    # Waiting for connection. Once receiving a connection, the function accept() returns a separate
    # client socket for the subsequent communication. By default, the function accept() is a blocking
    # one, which means it is suspended before the connection comes.
    tcpCliSock, addr = tcpSerSock.accept()
    print '...connected from :', addr  # Print the IP address of the client connected with the server.

    video_capture = cv2.VideoCapture(0)


def process_command(data):
    global recording_enabled

    # Ignore any command if we are in autonomous driving mode
    if get_predicting_enabled() and data != 'toggleAutonomousDriveFalse':
        return

    if data == ctrl_cmd[0]:
        print 'motor moving forward'
        motor.forward()
    elif data == ctrl_cmd[1]:
        print 'recv backward cmd'
        motor.backward()
    elif data == ctrl_cmd[2]:
        print 'recv left cmd'
        car_dir.turn_left()
    elif data == ctrl_cmd[3]:
        print 'recv right cmd'
        car_dir.turn_right()
    elif data == ctrl_cmd[6]:
        print 'recv home cmd'
        car_dir.home()
    elif data == ctrl_cmd[4]:
        print 'recv stop cmd'
        motor.ctrl(0)
    elif data == ctrl_cmd[5]:
        print 'read cpu temp...'
        temp = cpu_temp.read()
        tcpCliSock.send('[%s] %0.2f' % (ctime(), temp))
    elif data == ctrl_cmd[8]:
        print 'recv x+ cmd'
        video_dir.move_increase_x()
    elif data == ctrl_cmd[9]:
        print 'recv x- cmd'
        video_dir.move_decrease_x()
    elif data == ctrl_cmd[10]:
        print 'recv y+ cmd'
        video_dir.move_increase_y()
    elif data == ctrl_cmd[11]:
        print 'recv y- cmd'
        video_dir.move_decrease_y()
    elif data == ctrl_cmd[12]:
        print 'home_x_y'
        video_dir.home_x_y()
    elif data == ctrl_cmd[13]:
        print 'toggleRecordTrue'
        recording_enabled_lock.acquire()
        recording_enabled = True
        recording_enabled_lock.release()
    elif data == ctrl_cmd[14]:
        print 'toggleRecordFalse'
        recording_enabled_lock.acquire()
        recording_enabled = False
        recording_enabled_lock.release()
    elif data == ctrl_cmd[15]:
        print 'toggleAutonomousDriveTrue'
        # set home steering angle and autorun ON
        car_dir.home()
        motor.forward()

        predicting_enabled_lock.acquire()
        predicting_enabled = True
        predicting_enabled_lock.release()
    elif data == ctrl_cmd[16]:
        print 'toggleAutonomousDriveFalse'
        motor.stop()
        predicting_enabled_lock.acquire()
        predicting_enabled = False
        predicting_enabled_lock.release()
        car_dir.home()

    elif data[0:5] == 'speed':  # Change the speed
        print data
        num_len = len(data) - len('speed')
        if num_len == 1 or num_len == 2 or num_len == 3:
            tmp = data[-num_len:]
            print 'tmp(str) = %s' % tmp
            spd = int(tmp)
            print 'spd(int) = %d' % spd
            if spd < 24:
                spd = 24
            motor.setSpeed(spd)
    elif data[0:6] == 'turnBy':
        print data
        num_len = len(data) - len('turnBy')
        if num_len == 1 or num_len == 2 or num_len == 3:
            received_value = data[-num_len:]
            steering_value = int(received_value)
            print 'steering_value(int) = %d' % steering_value
            car_dir.turn_by(steering_value)
    elif data[0:8] == 'forward=':
        print 'data =', data
        spd = data[8:]
        try:
            spd = int(spd)
            motor.forwardWithSpeed(spd)
        except:
            print 'Error speed =', spd
    elif data[0:9] == 'backward=':
        print 'data =', data
        spd = data.split('=')[1]
        try:
            spd = int(spd)
            motor.backwardWithSpeed(spd)
        except:
            print 'ERROR, speed =', spd
    else:
        print 'Command Error! Cannot recognize command: ' + data


def server_routine_loop():
    while True:
        # Receive data sent from the client.
        data = tcpCliSock.recv(BUFSIZ)

        # Analyze the command received and control the car accordingly.
        if data:
            process_command(data)


if __name__ == "__main__":
    try:
        recording_setup()
        predicting_setup()
        setup()

        recording_thread.start()
        steering_angle_predictor_thread.start()
        server_routine_loop()

        recording_thread.join()
        steering_angle_predictor_thread.join()

    except KeyboardInterrupt:
        predicting_run_event.clear()
        recording_run_event.clear()
        csv_file.close()
        video_capture.release()
        tcpSerSock.close()
