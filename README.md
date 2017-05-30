## Deep learning data collector for Sunfounder Raspberry Pi Car Kit

### Summary:
 * [About this project](#about_this_project)
 * [Prerequisites](#prerequisites)
 * [How to run car calibration](#how_to_run_calibration)
 * [How to run data collection](#how_to_run)
 * [About this Sunfounder Car Kit](#about_this_kit)
 * [Contact](#contact)

<a id="about_this_project"></a>
### About this project:

Simple client/server application for deep learning data collection. The purpose of this project is to collect images from the front camera together with the steering wheel angle. These data can be then used to train a Deep Neural Network and achieve autonomous driving.

This code has been written for the [Berlin Autonomous Robo-Race](https://www.meetup.com/Berlin-Self-Driving-Cars-Autonomous-Mobility/) meetup

Forked from: [Sunfounder Smart Video Car Kit for Raspberry Pi](https://github.com/sunfounder/Sunfounder_Smart_Video_Car_Kit_for_RaspberryPi)

<a id="prerequisites"></a>
### Prerequisites:
This project is written for `Python 2.7`

On both PC and car clone the project:

                https://github.com/dlime/Deep-Learning-RC-Car-Data-Collector.git

Install the necessary libraries:

#### On PC:

                sudo apt-get install python-tk

#### On car:

                sudo apt-get install python-dev python-smbus

Install `opencv2` (follow this [guide](http://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/))

<a id="how_to_run_calibration"></a>
### How to run car calibration:

* Set HOST with your car IP in `client/car_calibration_client.py`
* From your car run `cd server; sudo python2 car_calibration_server.py`
* From your car PC `cd client; python2 car_calibration_client.py`
* Tune the parameters and press `Confirm`

<a id="how_to_run"></a>
### How to run data collection:

Before proceeding:
* Check that you installed all the [required libraries](#prerequisites)
* You have [calibrated](#how_to_run_calibration) your car
* Your PC can ping the car: `ping pi@<rasperry-pi-IP>`
* You have set `HOST` with your car IP in `client/client_app.py`


From Rasperry PI run the server routing:

                cd server
                sudo python2 tcp_server.py

From user computer run the client + GUI application:

                cd client
                python2 client_app.py

Once the GUI is shown, click on `RECORD` or press `Space` to start recording webcam images. Press `Space` again to stop recording.

Recorded data will be stored in this way:

                server/IMG/central-N.jpg
                server/IMG/driving_log.csv

`driving_log.csv` file format:

                image_path,steering_angle


You'll find it very handy to make the car go at a constant speed while recording data. To do so, just press `Enter` or click on button `AUTO RUN`. The auto run will use the current speed set, beware of high values! 


<a id="about_this_kit"></a>
### About Sunfounder Car Kit:
The SunFounder Smart Video Car Kit for Raspberry Pi is composed of Raspberry Pi, DC-DC Step-down Voltage Module, USB camera, DC motor driver, and PCA9685-based Servo Controller.
From the perspective of software, the smart car is of client/server (C/S) structure.
The TCP server program is run on Raspberry Pi for direct control of the car.  
The TCP client program is run on PC to send the control command. Both the client and server programs are developed in Python language.
The smart car is developed based on the open-source hardware Raspberry Pi and integrates the knowledge of mechanics, electronics, and computer, thus having profound educational significance. 

#### Notice:
This project is meant to be used with `Sunfounder Rasperry Pi Car Kit`

Before you run any client routine, you must first run the server routine.

----------------------------------------------
<a id="contact"></a>
### Contact:

**E-mail:** dario.limongi **_at_** gmail **_dot_** com
