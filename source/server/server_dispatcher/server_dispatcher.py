import pdb
import os
import json
import time
import sys
import argparse
import asyncio
from subprocess import Popen, PIPE, DEVNULL

from threading import Thread
import numpy as np
import cv2

BASE_DIR = ''


async def read_from_stream(reader, output):
    print('Starting reading from socket')
    while True:
        data = await reader.read(128)
        output.write(data)


async def video_decoder():
    cascade_path = './haarcascades/haarcascade_frontalface_alt.xml'
    faceCascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture('udp://localhost:8888')

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
    global PORT, BASE_DIR

    # Standard argument parsing
    parser = argparse.ArgumentParser(description='Start the dispatcher')
    parser.add_argument('-p', '--port', default=80, type=int, help='The port on which to open the server')
    parser.add_argument('-b', '--base_dir', default='.', help='The base directory of the server')
    args = parser.parse_args()

    BASE_DIR = args.base_dir
    PORT = args.port

    # Move script to http folder
    print(f'Base dir:{BASE_DIR}')
    os.chdir(BASE_DIR)

    asyncio.run(video_decoder())


if __name__ == '__main__':
    main()
