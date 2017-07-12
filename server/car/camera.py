import cv2
import threading
import sys


class Camera(object):
    SOURCE = 0
    WIDTH = 160
    HEIGHT = 120
    FPS = 60

    def __init__(self):
        self.video_capture = cv2.VideoCapture(self.SOURCE)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.WIDTH)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.HEIGHT)
        self.video_capture.set(cv2.CAP_PROP_FPS, self.FPS)

        if not self.video_capture.isOpened():
            sys.exit("Error: Camera didn't open for capture.")

        print 'Camera opened successfully'
        print '\tFrame width:  %d' % self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        print '\tFrame height: %d' % self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print '\tFPS:          %d' % self.video_capture.get(cv2.CAP_PROP_FPS)

        self.image_lock = threading.Lock()
        self.success, self.image = self.video_capture.read()

        self.is_capturing_lock = threading.Lock()
        self.is_capturing = False

    def get_is_capturing(self):
        self.is_capturing_lock.acquire()
        is_capturing = self.is_capturing
        self.is_capturing_lock.release()
        return is_capturing

    def get_image(self):
        self.image_lock.acquire()
        success = self.success
        image = self.image
        self.image_lock.release()
        return success, image

    def start(self):
        if self.get_is_capturing():
            print '\tCamera is already capturing'
            return

        self.is_capturing = True
        camera_thread = threading.Thread(target=self.capture_loop)
        camera_thread.daemon = True
        camera_thread.start()
        return self

    def stop(self):
        self.is_capturing_lock.acquire()
        self.is_capturing = False
        self.is_capturing_lock.release()

    def close(self):
        self.stop()
        self.video_capture.release()

    def capture_loop(self):
        while self.get_is_capturing():
            self.image_lock.acquire()
            self.success, self.image = self.video_capture.read()
            self.image_lock.release()

            if not self.success:
                print '\tFailed to read image from camera'
