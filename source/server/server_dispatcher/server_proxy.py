import pdb
import os
import json
import time
import sys
import argparse
import asyncio
from subprocess import Popen, PIPE, DEVNULL
import websockets

from struct import Struct
from threading import Thread
import numpy as np
import cv2

BASE_DIR = ''

###########################################
# CONFIGURATION
WIDTH = 640
HEIGHT = 480
FRAMERATE = 30
JSMPEG_MAGIC = b'jsmp'
JSMPEG_HEADER = Struct('>4sHH')
VFLIP = False
HFLIP = False
CTRL_PORT = 6666
STREAM_PORT = 7777


###########################################

class BroadcastOutput(object):
    def __init__(self, camera):
        print('Spawning background conversion process')
        try:

            command = f'ffmpeg -f rawvideo -pix_fmt bgr24 -s {WIDTH}x{HEIGHT} -i - \
            -maxrate 1024k -bufsize 2048k -r 30 -f mpeg1video -'

            self.converter = Popen(command,
                stdin=PIPE, stdout=PIPE, stderr=DEVNULL, close_fds=False,
                shell=False)

        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)

    def write(self, b):
        self.converter.stdin.write(b)

    def flush(self):
        print('Waiting for background conversion process to exit')
        self.converter.stdin.close()
        self.converter.wait()


class BroadcastThread(Thread):
    def __init__(self, converter ):
        super(BroadcastThread, self).__init__()
        self.converter = converter
        self.connected = set()

    def stop(self):
        self.done = True

    async def greet(self, websocket, path):
        # Register.
        self.connected.add(websocket)
        try:
            await websocket.send(JSMPEG_HEADER.pack(JSMPEG_MAGIC, WIDTH, HEIGHT))
            while True:
                await asyncio.sleep(10)
        finally:
            # Unregister.
            print('Goodbye socket')
            self.connected.remove(websocket)

    async def broadcast(self):
        try:
            while True:
                await asyncio.sleep(1.0/30.0)
                buf = self.converter.stdout.read1(32768)
                if buf:
                    for ws in self.connected:
                        try:
                            await ws.send(buf)
                        except:
                            pass
                elif self.converter.poll() is not None:
                    break
        finally:
            self.converter.stdout.close()

    def run(self):
        # Create a new event loop for asyncio, start serving by creating a
        # new request handler for each new connection
        asyncio.set_event_loop(asyncio.new_event_loop())

        conn = websockets.serve(self.greet, '0.0.0.0', rover_shared_data.stream_port)

        asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().create_task(self.broadcast())
        asyncio.get_event_loop().run_forever()


async def video_decoder():
    cascade_path = './haarcascades/haarcascade_frontalface_alt.xml'
    faceCascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture('conf.sdp')

    while True:
        ret, frame = cap.read()

        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Display the resulting frame
            cv2.imshow('frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    print('Close the connection')


def main():
    global CTRL_PORT, STREAM_PORT, BASE_DIR

    # Standard argument parsing
    parser = argparse.ArgumentParser(description='Start the dispatcher')
    parser.add_argument('-c', '--control_port', default=6666, type=int, help='The port on which to open the server')
    parser.add_argument('-t', '--stream_port', default=7777, type=int, help='The port on which to open the websocket')
    parser.add_argument('-b', '--base_dir', default='.', help='The base directory of the server')
    args = parser.parse_args()

    BASE_DIR = args.base_dir
    CTRL_PORT = args.control_port
    STREAM_PORT = args.stream_port

    # Move script to http folder
    print(f'Base dir:{BASE_DIR}')
    os.chdir(BASE_DIR)
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'protocol_whitelist;file,rtp,udp'

    asyncio.run(video_decoder())


if __name__ == '__main__':
    main()
