#!/usr/bin/env python
import threading
import time

import PCA9685 as servo

LEFT_STEERING_VALUE = -10
HOME_STEERING_VALUE = 0
RIGHT_STEERING_VALUE = 10
LEFT_PWM = 400
HOME_PWM = 450
RIGHT_PWM = 500
OFFSET = 0
CURRENT_STEERING_VALUE = HOME_STEERING_VALUE
current_steering_value_lock = threading.Lock()
pwm = servo.PWM()  # Initialize the servo controller.


def get_current_steering_value():
    global current_steering_value_lock

    current_steering_value_lock.acquire()
    return_value = CURRENT_STEERING_VALUE
    current_steering_value_lock.release()

    return return_value


def set_current_steering_value(new_value):
    global current_steering_value_lock, CURRENT_STEERING_VALUE

    current_steering_value_lock.acquire()
    CURRENT_STEERING_VALUE = new_value
    current_steering_value_lock.release()


def get_steering_pwm_from_value(value):
    global LEFT_STEERING_VALUE, RIGHT_STEERING_VALUE, LEFT_PWM, RIGHT_PWM
    if value > RIGHT_STEERING_VALUE:
        return RIGHT_PWM
    if value < LEFT_STEERING_VALUE:
        return LEFT_PWM

    return int((RIGHT_PWM - LEFT_PWM) * (
        (float(value - LEFT_STEERING_VALUE) / (RIGHT_STEERING_VALUE - LEFT_STEERING_VALUE))) + LEFT_PWM)


# ==========================================================================================
# Control the servo connected to channel 0 of the servo control board, so as to make the 
# car turn left.
# ==========================================================================================
def turn_left():
    global pwm
    set_current_steering_value(LEFT_STEERING_VALUE)
    pwm.write(0, 0, LEFT_PWM)  # CH0


# ==========================================================================================
# Make the car turn right.
# ==========================================================================================
def turn_right():
    global pwm
    set_current_steering_value(RIGHT_STEERING_VALUE)
    pwm.write(0, 0, RIGHT_PWM)


def turn_by(value):
    """
    Turn the car by giving any value between range [-10, +10]
    """
    set_current_steering_value(value)
    steering_pwm = get_steering_pwm_from_value(value) + OFFSET

    if steering_pwm < LEFT_PWM:
        steering_pwm = LEFT_PWM
    if steering_pwm > RIGHT_PWM:
        steering_pwm = RIGHT_PWM

    pwm.write(0, 0, steering_pwm)


def home():
    global HOME_PWM, pwm
    set_current_steering_value(HOME_STEERING_VALUE)
    pwm.write(0, 0, HOME_PWM)


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


def setup(busnum=None):
    global LEFT_PWM, RIGHT_PWM, HOME_PWM, pwm, OFFSET
    try:
        for line in open('config'):
            if line[0:8] == 'offset =':
                OFFSET = int(line[9:-1])
    except:
        print 'config error'
    LEFT_PWM += OFFSET
    HOME_PWM += OFFSET
    RIGHT_PWM += OFFSET
    if busnum is not None:
        pwm = servo.PWM(bus_number=busnum)  # Initialize the servo controller.
    pwm.frequency = 60


if __name__ == '__main__':
    setup()
    home()
