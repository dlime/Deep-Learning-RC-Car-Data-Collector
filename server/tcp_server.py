#!/usr/bin/env python
import RPi.GPIO as GPIO
import video_dir
import car_dir
import motor
from socket import *
from time import ctime  # Import necessary modules
import cv2
import csv

video_capture = cv2.VideoCapture(0)
csv_file = open('IMG/driving_log.csv', 'w', newline='')
writer = csv.writer(csv_file)
image_counter = 0
loop_counter = 0
recording_enabled = False
current_steering_angle = 0

ctrl_cmd = ['forward', 'backward', 'left', 'right', 'stop', 'read cpu_temp', 'home', 'distance', 'x+', 'x-', 'y+', 'y-',
            'xy_home', 'toggleRecordTrue', 'toggleRecordFalse']

busnum = 1  # Edit busnum to 0, if you uses Raspberry Pi 1 or 0

HOST = ''  # The variable of HOST is null, so the function bind( ) can be bound to all valid addresses.
PORT = 21567
BUFSIZ = 1024  # Size of the buffer
ADDR = (HOST, PORT)

tcpSerSock = socket(AF_INET, SOCK_STREAM)  # Create a socket.
tcpSerSock.bind(ADDR)  # Bind the IP address and port number of the server.
tcpSerSock.listen(5)  # The parameter of listen() defines the number of connections permitted at one time. Once the
# connections are full, others will be rejected.

video_dir.setup(busnum=busnum)
car_dir.setup(busnum=busnum)
motor.setup(busnum=busnum)  # Initialize the Raspberry Pi GPIO connected to the DC motor.
video_dir.home_x_y()
car_dir.home()


def record_data():
    global image_counter
    if recording_enabled and loop_counter % 200 == 0:
        success, image = video_capture.read()
        if success:
            image_path = "IMG/central-" + str(image_counter) + ".jpg"
            writer.writerow([image_path, current_steering_angle])
            cv2.imwrite(image_path, image)
            image_counter += 1


def setup():
    global tcpCliSock
    print 'Waiting for connection...'
    # Waiting for connection. Once receiving a connection, the function accept() returns a separate
    # client socket for the subsequent communication. By default, the function accept() is a blocking
    # one, which means it is suspended before the connection comes.
    tcpCliSock, addr = tcpSerSock.accept()
    print '...connected from :', addr  # Print the IP address of the client connected with the server.


def process_command(data):
    global recording_enabled, current_steering_angle
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
        recording_enabled = True
    elif data == ctrl_cmd[14]:
        print 'toggleRecordFalse'
        recording_enabled = False
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
            received_angle = data[-num_len:]
            steering_angle = int(received_angle)
            print 'steering_angle(int) = %d' % steering_angle
            current_steering_angle = steering_angle
            car_dir.turn_by(steering_angle)
    elif data[0:5] == 'turn=':  # Turning Angle
        print 'data =', data
        angle = data.split('=')[1]
        try:
            angle = int(angle)
            car_dir.turn(angle)
        except:
            print 'Error: angle =', angle
    elif data[0:8] == 'forward=':
        print 'data =', data
        spd = data[8:]
        try:
            spd = int(spd)
            motor.forward(spd)
        except:
            print 'Error speed =', spd
    elif data[0:9] == 'backward=':
        print 'data =', data
        spd = data.split('=')[1]
        try:
            spd = int(spd)
            motor.backward(spd)
        except:
            print 'ERROR, speed =', spd
    else:
        print 'Command Error! Cannot recognize command: ' + data


def loop():
    global loop_counter
    while True:
        # Receive data sent from the client.
        data = tcpCliSock.recv(BUFSIZ)

        # Analyze the command received and control the car accordingly.
        if data:
            process_command(data)

        if recording_enabled:
            record_data()

        # This is required so that we store an image every 200 loops and avoid data spam
        # TODO with a separate recorder thread this could have been done with time.sleep
        loop_counter += 1


if __name__ == "__main__":
    try:
        setup()
        loop()
    except KeyboardInterrupt:
        tcpSerSock.close()
        csv_file.close()
        video_capture.release()
