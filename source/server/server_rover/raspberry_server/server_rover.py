import pdb
import os
import json
import time
import sys
import argparse
import asyncio
import websockets
import logging
import serial
import cv2
import io
import numpy as np
import socket

from subprocess import Popen, PIPE, DEVNULL
from string import Template
from struct import Struct
from threading import Thread
from time import sleep, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from enum import Flag

###########################################
# CONFIGURATION
WIDTH = 640
HEIGHT = 480
FRAMERATE = 30
VFLIP = False
HFLIP = True
STREAM_HEADER = Struct('>4sHH')

###########################################


# The enum of the possible directions the rover can move
class ROVER_DIRECTION(Flag):
    STOP = 0
    FORWARD = 1
    BACK = 2
    LEFT = 4
    RIGHT = 8
    CW = 16
    CCW = 32


# The enum of the possible directions the camera can move
class CAM_DIRECTION(Flag):
    STOP = 0
    UP = 1
    DOWN = 2


# The enum of the possible motors on the rover
class ROVER_MOTORS(Flag):
    WHEELS = 1
    CAMERA = 2


# The enum of the possible statuses for the laser
class LASER_ACTION(Flag):
    ON = 1
    OFF = 2
    BLINK = 4


# The enum of the possible status of the camera after a move command
class ROVER_STATUS(Flag):
    OK = 0
    BLOCKED = 1
    CAM_TOP_LIMIT = 2
    CAM_BOTTOM_LIMIT = 4


# The rover Hardware Abastraction Layer handles all requests that must be handled
# by the hardware. Although not enforced, this is a singleton.
class rover_HAL():

    def __init__(self):
        self.ser = None
        pass

    def open_serial(self):
        self.ser = serial.Serial(rover_shared_data.serial_port)

    def send_serial_command(self, command):
        print('sending {command}')
        self.ser.write(command)

    def is_blocked(self):
        pass

    def move(self, direction):
        serial_command = 'move '

        if (direction & ROVER_DIRECTION.FORWARD):
            serial_command += 'w'
        if (direction & ROVER_DIRECTION.BACK):
            serial_command += 's'
        if (direction & ROVER_DIRECTION.LEFT):
            serial_command += 'a'
        if (direction & ROVER_DIRECTION.RIGHT):
            serial_command += 'd'
        if (direction & ROVER_DIRECTION.CW):
            serial_command += 'e'
        if (direction & ROVER_DIRECTION.CCW):
            serial_command += 'q'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))

        return ROVER_STATUS.OK

    def move_cam(self, direction):
        serial_command = 'move_cam '

        if (direction & CAM_DIRECTION.UP):
            serial_command += 'r'
        if (direction & CAM_DIRECTION.DOWN):
            serial_command += 'f'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def stop_motors(self, motors):

        serial_command = 'move_stop '

        if (motors & ROVER_MOTORS.WHEELS):
            serial_command += 'w'
        if (motors & ROVER_MOTORS.CAMERA):
            serial_command += 'c'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def laser_ctrl(self, action):

        serial_command = 'laser_ctrl '

        if (action & LASER_ACTION.ON):
            serial_command += 'i'
        if (action & LASER_ACTION.OFF):
            serial_command += 'o'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK


# A class holding all data that is common to the rover and can be accessed by any other
# class. Although not enforced, this is a singleton.
class rover_data():
    def __init__(self):
        self.cmd_port = 8888
        self.stream_port = 1935
        self.server_address = ''
        self.serial_port = ''
        self.camera_no = 0


class rover_request_handler():
    def __init__(self, reader, writer, cleanup_fun=None):
        self.reader = reader
        self.writer = writer
        self.cleanup_fun = cleanup_fun

    async def serve(self):
        try:
            while True:
                line = await self.reader.readline()
                if not line:
                    break

                line = line.decode('latin1').rstrip()
                if line:
                    print('{line}')
                    await self.process(line)

            print('Bye Bye JoJo')
            self.cleanup_fun(self)

        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)

            print('Connection lost')

    async def process(self, message):
        try:
            msg = json.loads(message)
            cmd = msg['cmd']

            if (cmd == 'move'):
                await self.cmd_move(msg)
            elif (cmd == 'move_cam'):
                await self.cmd_move_camera(msg)
            elif (cmd == 'move_stop'):
                await self.cmd_move_stop(msg)
            elif (cmd == 'track'):
                await self.cmd_track_person(msg)
            elif (cmd == 'untrack'):
                await self.cmd_untrack_person(msg)
            elif (cmd == 'attack'):
                await self.cmd_attack_person(msg)
            elif (cmd == 'stop_attack'):
                await self.cmd_stop_attack_person(msg)
            elif (cmd == 'laser_ctrl'):
                await self.cmd_laser_ctrl(msg)
            elif (cmd == 'list_faces'):
                await self.cmd_list_faces(msg)
            else:
                await self.error_response("unknown_cmd")
        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
            await self.error_response("parsing_error")

    # Send the message, given as dictionary, to the socket, encoded as json
    async def send_message(self, message):
        try:
            encoded_msg = json.dumps(message)
            await self.writer.write(encoded_msg.encode())
        except:
            print('Connection lost')

    # Creates a standard error response, where the info field is set as failure reason
    # it then sends the message to the socket
    async def error_response(self, failure_reason):
        error = {"msg": "failed",
                 "info": f"{failure_reason}"}
        await self.send_message(error)

    async def success_response(self):
        ok = {"msg": "ok"}
        await self.send_message(ok)

    # Attempts to move the rover in the desired directions, failing if the rover
    # encounters an obstacle.
    async def cmd_move(self, message):

        print('Processing move command')

        # Define the set of sets of allowed directions and combinations
        allowed_directions = {frozenset(['forward']),
                              frozenset(['back']),
                              frozenset(['left']),
                              frozenset(['right']),
                              frozenset(['forward', 'left']),
                              frozenset(['forward', 'right']),
                              frozenset(['back', 'left']),
                              frozenset(['back', 'right']),
                              frozenset(['cw']),
                              frozenset(['ccw'])}

        try:
            params = message['params']

            direction = frozenset(params['direction'])

            if (direction in allowed_directions):

                rover_dir = None

                if (direction == frozenset(['forward'])):
                    rover_dir = ROVER_DIRECTION.FORWARD
                elif (direction == frozenset(['back'])):
                    rover_dir = ROVER_DIRECTION.BACK
                elif (direction == frozenset(['left'])):
                    rover_dir = ROVER_DIRECTION.LEFT
                elif (direction == frozenset(['right'])):
                    rover_dir = ROVER_DIRECTION.RIGHT
                elif (direction == frozenset(['cw'])):
                    rover_dir = ROVER_DIRECTION.CW
                elif (direction == frozenset(['ccw'])):
                    rover_dir = ROVER_DIRECTION.CCW
                elif (direction == frozenset(['forward', 'left'])):
                    rover_dir = ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.LEFT
                elif (direction == frozenset(['forward', 'right'])):
                    rover_dir = ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.RIGHT
                elif (direction == frozenset(['back', 'left'])):
                    rover_dir = ROVER_DIRECTION.BACK | ROVER_DIRECTION.LEFT
                elif (direction == frozenset(['back', 'right'])):
                    rover_dir = ROVER_DIRECTION.BACK | ROVER_DIRECTION.RIGHT

                r = rover_hal.move(rover_dir)
                if (r == ROVER_STATUS.OK):
                    await self.success_response()
                else:
                    await self.error_response("blocked")

            else:
                await self.error_response("bad_direction")

        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
            await self.error_response("bad_params")

    # Attempts to move the camera in the desired direction, failing if the camera
    # has reached the top or bottom limit.
    async def cmd_move_camera(self, message):

        print('Processing move camera command')

        try:
            params = message['params']

            direction = params['direction']
            cam_dir = None

            if (direction == 'up'):
                cam_dir = CAM_DIRECTION.UP
            elif (direction == 'down'):
                cam_dir = CAM_DIRECTION.DOWN
            else:
                await self.error_response("bad_direction")

            r = rover_hal.move_cam(cam_dir)
            if (r == ROVER_STATUS.OK):
                await self.success_response()
            elif (r == ROVER_STATUS.CAM_TOP_LIMIT):
                await self.error_response("top_limit")
            elif (r == ROVER_STATUS.CAM_BOTTOM_LIMIT):
                await self.error_response("bottom_limit")
        except:
            await self.error_response("bad_params")

    # Stops the desired movements
    async def cmd_move_stop(self, message):

        print('Processing move stop command')

        # Define the set of sets of allowed motors and combinations
        allowed_motors = {frozenset(['wheels']), frozenset(['camera']), frozenset(['camera', 'wheels'])}

        try:
            params = message['params']

            motors = frozenset(params['motors'])

            if (motors in allowed_motors):

                stopped_motors = None

                if (motors == frozenset(['wheels'])):
                    stopped_motors = ROVER_MOTORS.WHEELS
                elif (motors == frozenset(['camera'])):
                    stopped_motors = ROVER_MOTORS.CAMERA
                elif (motors == frozenset(['wheels', 'camera'])):
                    stopped_motors = ROVER_MOTORS.WHEELS | ROVER_MOTORS.CAMERA

                r = rover_hal.stop_motors(stopped_motors)

                if (r == ROVER_STATUS.OK):
                    await self.success_response()
            else:
                await self.error_response("bad_motors")
        except:
            await self.error_response("bad_params")

    async def cmd_track_person(self, message):
        pass

    async def cmd_untrack_person(self, message):
        pass

    async def cmd_attack_person(self, message):
        await self.success_response()

    async def cmd_stop_attack_person(self, message):
        pass

    # Puts the laser in the desired state
    async def cmd_laser_ctrl(self, message):

        print('Processing laser control command')

        try:
            params = message['params']

            action = params['action']
            laser_action = None

            if (action == 'on'):
                laser_action = LASER_ACTION.ON
            elif (action == 'off'):
                laser_action = LASER_ACTION.OFF
            elif (action == 'blink'):
                laser_action = LASER_ACTION.BLINK
            else:
                await self.error_response("bad_action")

            r = rover_hal.laser_ctrl(laser_action)
            if (r == ROVER_STATUS.OK):
                await self.success_response()

        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
            await self.error_response("bad_params")

    async def cmd_list_faces(self, message):
        pass


class rover_server_thread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.done = False
        self.active_connections = set()

    def stop(self):
        self.done = True

    async def greet(self, reader, writer):
        print('Client connected')
        request_handler = rover_request_handler(reader, writer, cleanup_fun=self.cleanup)
        self.active_connections.add(request_handler)
        await request_handler.serve()

    def cleanup(self, request_handler):
        self.active_connections.remove(request_handler)

    def run(self):
        print('Rover Server started')

        # Create a new event loop for asyncio, start serving by creating a 
        # new request handler for each new connection
        asyncio.set_event_loop(asyncio.new_event_loop())

        conn = asyncio.start_server(self.greet, '0.0.0.0', rover_shared_data.cmd_port)

        asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().run_forever()


class BroadcastOutput(object):
    def __init__(self, camera):
        print('Spawning background conversion process')
        try:
            bitrate = 6000
            command = f'ffmpeg \
-f v4l2 -input_format mjpeg -re -i /dev/video0 \
-vcodec libx265 -preset ultrafast \
-map 0:0 -threads 8 -an \
-muxdelay 0.001 -b:v 500k \
-sdp_file conf.sdp \
-f rtp rtp://{rover_shared_data.server_address}:{rover_shared_data.stream_port}'

            print(command)

            self.converter = Popen(command, stdin=PIPE, close_fds=False, shell=True)

        except Exception as inst:
            print('Error opening the converter')
            print(type(inst))  # the exception instance
            print(inst.args)  # arguments stored in .args
            print(inst)

    def write(self, b):
        self.converter.stdin.write(b)

    def flush(self):
        print('Waiting for background conversion process to exit')
        self.converter.stdin.close()
        self.converter.wait()

class USBCamera():
    def __init__(self, camera_no):
        self.cam_no = camera_no
        self.cap = cv2.VideoCapture(self.cam_no)
        self.resolution = (self.cap.get(cv2.CAP_PROP_FRAME_WIDTH), self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.framerate = self.cap.get(cv2.CAP_PROP_FPS)
        self.vflip = VFLIP
        self.hflip = HFLIP
        self.cap.release()

# >>>>>>>>>> GLOBAL VARIABLES <<<<<<<<<<#

rover_hal = rover_HAL()
rover_shared_data = rover_data()


def main():
    global rover_shared_data

    # Standard argument parsing
    parser = argparse.ArgumentParser(description='Start the dispatcher')
    parser.add_argument('-c', '--command_port', default=8888, type=int, help='The port on which to open the server')
    parser.add_argument('-t', '--stream_port', default=1935, type=int, help='The port on which to open the websocket')
    parser.add_argument('-s', '--serial', default='/dev/ttyUSB0',
                        help='The serial port to communicate with the arduino')
    parser.add_argument('-a', '--server_address', required=True,
                        help='The address of the dispatcher server')
    parser.add_argument('-n', '--camera_no', default=0, type=int,
                        help='The camera number from which to take the stream')
    args = parser.parse_args()

    rover_shared_data.cmd_port = args.command_port
    rover_shared_data.stream_port = args.stream_port
    rover_shared_data.serial_port = args.serial
    rover_shared_data.camera_no = args.camera_no
    rover_shared_data.server_address = args.server_address

    # rover_hal.open_serial()

    # logger = logging.getLogger('websockets')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    print('Initializing camera')
    camera = USBCamera(rover_shared_data.camera_no)

    print('Initializing broadcast thread')
    output = BroadcastOutput(camera)

    print('Initializing command thread')
    server_thread = rover_server_thread()

    camera.output = output
    print('Starting recording')

    try:
        print('Starting command server')
        server_thread.start()

    except KeyboardInterrupt:
        pass
    finally:
        print('Waiting for command thread to finish')
        server_thread.join()


if __name__ == '__main__':
    main()
