from picamera.array import PiRGBArray
from picamera import PiCamera
from threading import Thread
import cv2
import time


class Camera:
    WIDTH = 160
    HEIGHT = 120
    FPS = 60

    def __init__(self, resolution=(WIDTH, HEIGHT), framerate=FPS):
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture,
                                                     format="bgr", use_video_port=True)

        self.image = None
        self.stopped = False

        print '\nCamera opened successfully'
        print '\tFrame width:  %d' % self.WIDTH
        print '\tFrame height: %d' % self.HEIGHT
        print '\tFPS:          %d' % self.FPS
        print 'Warming up camera sensors. Wait 2 seconds..\n\n'
        time.sleep(2)

    def start(self):
        thread = Thread(target=self.update)
        thread.daemon = True
        thread.start()
        return self

    def update(self):
        for frame in self.stream:
            self.image = frame.array
            self.rawCapture.truncate(0)

            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        return self.image

    def stop(self):
        self.stopped = True
