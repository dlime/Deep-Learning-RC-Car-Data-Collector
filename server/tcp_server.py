#!/usr/bin/env python
import csv
import json
import threading
import time
import cv2  # TODO: should be dropped since PiCamera is now used
import numpy as np
import sys
from socket import *
from keras.models import model_from_json
from car import steering_wheels, motor, camera_direction
from car.camera import Camera

recording_enabled_lock = threading.Lock()
recording_enabled = False

predicting_enabled_lock = threading.Lock()
predicting_enabled = False

BUSNUM = 1  # Edit busnum to 0, if you uses Raspberry Pi 1 or 0

HOST = ''  # The variable of HOST is null, so the function bind( ) can be bound to all valid addresses.
PORT = 21567
BUFSIZ = 1024  # Size of the buffer
ADDR = (HOST, PORT)

tcpSerSock = socket(AF_INET, SOCK_STREAM)  # Create a socket.
tcpSerSock.bind(ADDR)  # Bind the IP address and port number of the server.
tcpSerSock.listen(5)  # The parameter of listen() defines the number of connections permitted at one time. Once the
# connections are full, others will be rejected.

camera_direction.setup(busnum=BUSNUM)
steering_wheels.setup(busnum=BUSNUM)
motor.setup(busnum=BUSNUM)  # Initialize the Raspberry Pi GPIO connected to the DC motor.
camera_direction.home_x_y()
steering_wheels.home()


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

    # Do an empty predict, it's an hack that make the model fully load and give real time prediction later
    empty_image = np.zeros((Camera.HEIGHT, Camera.WIDTH, 3))
    empty_image = empty_image[None, :, :, :]

    start_time = time.time()
    temp_steering_angle = int(model.predict(empty_image, batch_size=1))
    end_time = time.time() - start_time
    print '\tModel prediction test 1 took %f seconds' % end_time

    start_time = time.time()
    temp_steering_angle = int(model.predict(empty_image, batch_size=1))
    end_time = time.time() - start_time
    print '\tModel prediction test 2 took %f seconds' % end_time


def predicting_loop():
    global image_counter, writer, recording_enabled, csv_file, model
    while predicting_run_event.is_set():
        if not get_predicting_enabled():
            continue

        start_time = time.time()
        print 'Predicting loop'
        print '\tReading image...'
        image = camera_stream.read()

        print '\tPredicting...'
        image_normalized = image / 127.5 - 1.
        predicted_steering_angle = int(model.predict(image_normalized[None, :, :, :], batch_size=1))

        steering_wheels.turn_by(predicted_steering_angle)
        end_time = time.time() - start_time
        print '\tpredicted angle = %d execution time %f' % (predicted_steering_angle, end_time)


def recording_setup():
    global csv_file, image_counter, writer, recording_thread, recording_run_event, camera_stream
    image_counter = 0
    camera_stream = Camera().start()
    print 'Warming up camera sensors. Wait 2 seconds..\n\n'
    time.sleep(2)

    csv_file = open('CNN/data/driving_log.csv', 'w')
    writer = csv.writer(csv_file)

    recording_run_event = threading.Event()
    recording_run_event.set()
    recording_thread = threading.Thread(target=recording_loop)


def recording_loop():
    global image_counter, writer, recording_enabled, csv_file
    while recording_run_event.is_set():
        if not get_recording_enabled():
            continue

        image_path = "CNN/data/image-" + str(image_counter) + ".jpg"
        writer.writerow([image_path, steering_wheels.get_current_steering_value()])
        cv2.imwrite(image_path, camera_stream.read())

        print 'image %d stored..' % image_counter

        image_counter += 1
        time.sleep(0.05)


def setup():
    global tcpCliSock, datacolletor

    print '\nWaiting for connection...'
    # Waiting for connection. Once receiving a connection, the function accept() returns a separate
    # client socket for the subsequent communication. By default, the function accept() is a blocking
    # one, which means it is suspended before the connection comes.
    tcpCliSock, ip_address = tcpSerSock.accept()
    print '...connected from :', ip_address  # Print the IP address of the client connected with the server.


def process_command(data):
    global recording_enabled, predicting_enabled

    # Ignore any command if we are in autonomous driving mode
    if get_predicting_enabled() and data != 'toggleAutonomousDriveFalse':
        print 'Autonomous driving mode, ignoring command - stop autonomous drive first'
        return

    if data == 'forward':
        print 'Received forward'
        motor.forward()
    elif data == 'backward':
        print 'Received backward'
        motor.backward()
    elif data == 'left':
        print 'Received left'
        steering_wheels.turn_left()
    elif data == 'right':
        print 'Received right'
        steering_wheels.turn_right()
    elif data == 'home':
        print 'Received home'
        steering_wheels.home()
    elif data == 'stop':
        print 'Received stop'
        motor.ctrl(0)
    elif data == 'x+':
        print 'Received x+'
        camera_direction.move_increase_x()
    elif data == 'x-':
        print 'Received x-'
        camera_direction.move_decrease_x()
    elif data == 'y+':
        print 'Received y+'
        camera_direction.move_increase_y()
    elif data == 'y-':
        print 'Received y-'
        camera_direction.move_decrease_y()
    elif data == 'xy_home':
        print 'Received home_x_y'
        camera_direction.home_x_y()
    elif data == 'toggleRecordTrue':
        print 'Received toggleRecordTrue'
        recording_enabled_lock.acquire()
        recording_enabled = True
        recording_enabled_lock.release()
    elif data == 'toggleRecordFalse':
        print 'Received toggleRecordFalse'
        recording_enabled_lock.acquire()
        recording_enabled = False
        recording_enabled_lock.release()
    elif data == 'toggleAutonomousDriveTrue':
        print 'Received toggleAutonomousDriveTrue'
        # set home steering angle and autorun ON
        steering_wheels.home()
        motor.forward()

        predicting_enabled_lock.acquire()
        predicting_enabled = True
        predicting_enabled_lock.release()
    elif data == 'toggleAutonomousDriveFalse':
        print 'Received toggleAutonomousDriveFalse'
        motor.stop()
        predicting_enabled_lock.acquire()
        predicting_enabled = False
        predicting_enabled_lock.release()
        steering_wheels.home()

    elif data[0:5] == 'speed':  # Change the speed
        print data
        num_len = len(data) - len('speed')
        if num_len == 1 or num_len == 2 or num_len == 3:
            tmp = data[-num_len:]
            print 'tmp(str) = %s' % tmp
            speed = int(tmp)
            print 'spd(int) = %d' % speed
            if speed < 24:
                speed = 24
            motor.set_speed(speed)
    elif data[0:6] == 'turnBy':
        print data
        num_len = len(data) - len('turnBy')
        if num_len == 1 or num_len == 2 or num_len == 3:
            received_value = data[-num_len:]
            steering_value = int(received_value)
            print 'steering_value(int) = %d' % steering_value
            steering_wheels.turn_by(steering_value)
    elif data[0:8] == 'forward=':
        print 'data =', data
        speed = data[8:]
        try:
            speed = int(speed)
            motor.forward_with_speed(speed)
        except:
            print 'Error speed =', speed
    elif data[0:9] == 'backward=':
        print 'data =', data
        speed = data.split('=')[1]
        try:
            speed = int(speed)
            motor.backward_with_speed(speed)
        except:
            print 'ERROR, speed =', speed
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

    except:
        print '\nQuitting because of:', sys.exc_info()[0]
        print '\tCleaning up...'
        motor.ctrl(0)
        predicting_run_event.clear()
        recording_run_event.clear()

        csv_file.close()
        camera_stream.stop()
        tcpSerSock.close()
        print '\tBye!'
