#!/usr/bin/env python
import PCA9685 as servo
import time  # Import necessary modules

leftPWM = 400
homePWM = 450
rightPWM = 500
offset = 0
current_steering_angle = homePWM  # stores the current steering angle PWM (without offset)
pwm = servo.PWM()  # Initialize the servo controller.


def map_angle(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def setup(busnum=None):
    global leftPWM, rightPWM, homePWM, pwm, offset
    try:
        for line in open('config'):
            if line[0:8] == 'offset =':
                offset = int(line[9:-1])
    except:
        print 'config error'
    leftPWM += offset
    homePWM += offset
    rightPWM += offset
    if busnum is not None:
        pwm = servo.PWM(bus_number=busnum)  # Initialize the servo controller.
    pwm.frequency = 60


# ==========================================================================================
# Control the servo connected to channel 0 of the servo control board, so as to make the 
# car turn left.
# ==========================================================================================
def turn_left():
    global leftPWM, pwm, current_steering_angle
    current_steering_angle = leftPWM - offset
    pwm.write(0, 0, leftPWM)  # CH0


# ==========================================================================================
# Make the car turn right.
# ==========================================================================================
def turn_right():
    global rightPWM, pwm, current_steering_angle
    current_steering_angle = rightPWM - offset
    pwm.write(0, 0, rightPWM)


# ==========================================================================================
# Make the car turn back.
# ==========================================================================================

def turn(angle):
    global leftPWM, rightPWM, pwm, current_steering_angle
    angle = map_angle(angle, 0, 255, leftPWM, rightPWM)
    current_steering_angle = angle - offset
    pwm.write(0, 0, angle)


def turn_by(steering_angle):
    global leftPWM, rightPWM, offset, pwm, current_steering_angle
    current_steering_angle = steering_angle
    steering_angle += offset
    if steering_angle < leftPWM:
        steering_angle = leftPWM
    if steering_angle > rightPWM:
        steering_angle = rightPWM
    pwm.write(0, 0, steering_angle)


def home():
    global homePWM, pwm, current_steering_angle
    current_steering_angle = homePWM - offset
    pwm.write(0, 0, homePWM)


def calibrate(x):
    global pwm
    pwm.write(0, 0, 450 + x)


def test():
    while True:
        turn_left()
        time.sleep(1)
        home()
        time.sleep(1)
        turn_right()
        time.sleep(1)
        home()


if __name__ == '__main__':
    setup()
    home()
