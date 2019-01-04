import cv2
import sys

class USBCamera(object):
    def __init__(self, camera_no):
        self.cam_no = int(camera_no)
        self.cap = cv2.VideoCapture( self.cam_no )
        self.resolution = ( 640, 480)
        self.framerate = 30

    def __enter__(self):
        pass
    
    def __exit__(self, a, b, c):
        pass

    def start_recording( self ):

        while True:
            # Capture frame-by-frame
            ret, frame = self.cap.read()

            # Our operations on the frame come here
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Display the resulting frame
            cv2.imshow('frame',gray)   

            if cv2.waitKey(1) == 27: 
                break  # esc to quit
        cv2.destroyAllWindows()



def main():
    print('Initializing camera')
    camera = USBCamera( sys.argv[1] )
    camera.start_recording()


if __name__ == '__main__':
    main()
