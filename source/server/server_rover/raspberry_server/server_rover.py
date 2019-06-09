import json
import argparse
import asyncio
import serial
import cv2
import atexit
import uuid
import numpy as np
from enum import Flag


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
    CW = 4
    CCW = 8


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


# A class holding all data that is common to the rover and can be accessed by any other
# class. Although not enforced, this is a singleton.
class RoverData:
    def __init__(self):
        self.rover_data_file = 'rover_data.json'
        self.conf_file_name = 'conf.sdp'
        self.cmd_port = 6666
        self.stream_port = 7777
        self.server_address = ''
        self.serial_port = ''
        self.camera_no = 0
        self.data = None


# The rover Hardware Abstraction Layer handles all requests that must be handled
# by the hardware. Although not enforced, this is a singleton.
class rover_HAL:

    def __init__(self):
        self.ser = None
        pass

    def open_serial(self):
        self.ser = serial.Serial(rover_shared_data.serial_port)

    def send_serial_command(self, command):
        print(f'sending {command}')
        self.ser.write(command)
        # line = self.ser.readline()
        # print(f'Received {line}')

    def is_blocked(self):
        pass

    def move(self, direction):
        serial_command = 'move '

        if direction & ROVER_DIRECTION.FORWARD:
            serial_command += 'w'
        if direction & ROVER_DIRECTION.BACK:
            serial_command += 's'
        if direction & ROVER_DIRECTION.LEFT:
            serial_command += 'a'
        if direction & ROVER_DIRECTION.RIGHT:
            serial_command += 'd'
        if direction & ROVER_DIRECTION.CW:
            serial_command += 'e'
        if direction & ROVER_DIRECTION.CCW:
            serial_command += 'q'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))

        return ROVER_STATUS.OK

    def move_cam(self, direction):
        serial_command = 'move_cam '

        if direction & CAM_DIRECTION.UP:
            serial_command += 'r'
        if direction & CAM_DIRECTION.DOWN:
            serial_command += 'f'
        if direction & CAM_DIRECTION.CW:
            serial_command += 'y'
        if direction & CAM_DIRECTION.CCW:
            serial_command += 't'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def set_cam(self, angles):
        serial_command = f'set_cam {angles[0]} {angles[1]}'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def stop_motors(self, motors):

        serial_command = 'move_stop '

        if motors & ROVER_MOTORS.WHEELS:
            serial_command += 'w'
        if motors & ROVER_MOTORS.CAMERA:
            serial_command += 'c'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def laser_ctrl(self, action):

        serial_command = 'laser_ctrl '

        if action & LASER_ACTION.ON:
            serial_command += 'i'
        if action & LASER_ACTION.OFF:
            serial_command += 'o'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def set_speed(self, speed):
        serial_command = f'speed {speed}'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK

    def set_cam_speed(self, speed):
        serial_command = f'cam_speed {speed[0]} {speed[1]}'

        serial_command += '\n'

        self.send_serial_command(bytes(serial_command, 'ascii'))
        return ROVER_STATUS.OK


# >>>>>>>>>> GLOBAL VARIABLES <<<<<<<<<<#

rover_hal = rover_HAL()
rover_shared_data = RoverData()


class RoverRequestHandler:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.id = uuid.uuid1()

        # Define the set of sets of allowed directions and combinations
        self.allowed_directions = {frozenset(['forward']): ROVER_DIRECTION.FORWARD,
                                   frozenset(['back']): ROVER_DIRECTION.BACK,
                                   frozenset(['left']): ROVER_DIRECTION.LEFT,
                                   frozenset(['right']): ROVER_DIRECTION.RIGHT,
                                   frozenset(['forward', 'left']): ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.LEFT,
                                   frozenset(['forward', 'right']): ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.RIGHT,
                                   frozenset(['back', 'left']): ROVER_DIRECTION.BACK | ROVER_DIRECTION.LEFT,
                                   frozenset(['back', 'right']): ROVER_DIRECTION.BACK | ROVER_DIRECTION.RIGHT,
                                   frozenset(['cw']): ROVER_DIRECTION.CW,
                                   frozenset(['ccw']): ROVER_DIRECTION.CCW}

        # Define the set of sets of allowed directions and combinations
        self.allowed_cam_directions = {frozenset(['up']): CAM_DIRECTION.UP,
                                       frozenset(['down']): CAM_DIRECTION.DOWN,
                                       frozenset(['up', 'cw']): CAM_DIRECTION.UP | CAM_DIRECTION.CW,
                                       frozenset(['up', 'ccw']): CAM_DIRECTION.UP | CAM_DIRECTION.CCW,
                                       frozenset(['down', 'cw']): CAM_DIRECTION.DOWN | CAM_DIRECTION.CW,
                                       frozenset(['down', 'ccw']): CAM_DIRECTION.DOWN | CAM_DIRECTION.CCW,
                                       frozenset(['cw']): CAM_DIRECTION.CW,
                                       frozenset(['ccw']): CAM_DIRECTION.CCW}

        # Define the set of sets of allowed motors and combinations
        self.allowed_motors = {frozenset(['wheels']): ROVER_MOTORS.WHEELS,
                               frozenset(['camera']): ROVER_MOTORS.CAMERA,
                               frozenset(['camera', 'wheels']): ROVER_MOTORS.WHEELS | ROVER_MOTORS.CAMERA}

        # Define the set of sets of allowed commands and their response functions
        self.allowed_commands = {'move': self.cmd_move,
                                 'set_speed': self.cmd_set_speed,
                                 'set_cam_speed': self.cmd_set_cam_speed,
                                 'move_cam': self.cmd_move_camera,
                                 'set_cam': self.cmd_set_camera,
                                 'move_stop': self.cmd_move_stop,
                                 'track': self.cmd_track_person,
                                 'untrack': self.cmd_untrack_person,
                                 'attack': self.cmd_attack_person,
                                 'stop_attack': self.cmd_stop_attack_person,
                                 'laser_ctrl': self.cmd_laser_ctrl,
                                 'list_faces': self.cmd_list_faces}

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(rover_shared_data.server_address,
                                                                 rover_shared_data.cmd_port)

        hello_cmd = {'rover_id': str(self.id), 'cmd': 'hello',
                     'rover_data': rover_shared_data.data}

        await self.send_message(hello_cmd)

    async def send_stream_info(self):
        with open(rover_shared_data.rover_data_file) as f:
            conf_string = f.read()
            set_stream_cmd = {'rover_id': str(self.id), 'cmd': 'set_stream', 'conf': conf_string}
            await self.send_message(set_stream_cmd)

    async def serve(self):
        await self.send_stream_info()

        try:
            while True:
                line = await self.reader.readline()
                line = line.decode()
                if line:
                    print(f'{line}')
                    await self.process(line)

        except Exception as e:
            print('Error processing command')
            # print(type(e))  # the exception instance
            # print(e.args)  # arguments stored in .args
            # print(e)

    async def process(self, message):
        try:
            msg = json.loads(message)
            cmd = msg['cmd']

            if cmd in self.allowed_commands.keys():
                await self.allowed_commands[cmd](msg)
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
            encoded_msg = json.dumps(message) + '\n'
            self.writer.write(encoded_msg.encode())
            await self.writer.drain()
        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
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

        try:
            params = message['params']

            direction = frozenset(params['direction'])

            if direction in self.allowed_directions.keys():

                rover_dir = self.allowed_directions[direction]

                r = rover_hal.move(rover_dir)
                if r == ROVER_STATUS.OK:
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

    async def cmd_set_speed(self, message):
        print('Processing speed command')

        try:
            params = message['params']

            speed = np.clip(float(params['speed']), 0.0, 1.0)

            r = rover_hal.set_speed(speed)
            if r == ROVER_STATUS.OK:
                await self.success_response()
            else:
                await self.error_response("blocked")


        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
            await self.error_response("bad_params")

    async def cmd_set_cam_speed(self, message):
        print('Processing cam speed command')

        try:
            params = message['params']

            speed = np.clip(params['speed'], 0.0, 90.0)

            r = rover_hal.set_cam_speed(speed)
            if r == ROVER_STATUS.OK:
                await self.success_response()
            else:
                await self.error_response("blocked")


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
            direction = frozenset(params['direction'])

            if direction in self.allowed_cam_directions.keys():
                cam_dir = self.allowed_cam_directions[direction]

                r = rover_hal.move_cam(cam_dir)
                if r == ROVER_STATUS.OK:
                    await self.success_response()
                elif r == ROVER_STATUS.CAM_TOP_LIMIT:
                    await self.error_response("top_limit")
                elif r == ROVER_STATUS.CAM_BOTTOM_LIMIT:
                    await self.error_response("bottom_limit")

            else:
                await self.error_response("bad_direction")

        except:
            await self.error_response("bad_params")

    # Set the camera to the desired angle
    async def cmd_set_camera(self, message):
        print('Processing set camera command')

        try:
            params = message['params']
            angles = params['angles']

            r = rover_hal.set_cam(angles)
            if r == ROVER_STATUS.OK:
                await self.success_response()
            elif r == ROVER_STATUS.CAM_TOP_LIMIT:
                await self.error_response("top_limit")
            elif r == ROVER_STATUS.CAM_BOTTOM_LIMIT:
                await self.error_response("bottom_limit")

        except:
            await self.error_response("bad_params")

    # Stops the desired movements
    async def cmd_move_stop(self, message):

        print('Processing move stop command')

        try:
            params = message['params']

            motors = frozenset(params['motors'])

            if motors in self.allowed_motors.keys():

                stopped_motors = self.allowed_motors[motors]

                r = rover_hal.stop_motors(stopped_motors)

                if r == ROVER_STATUS.OK:
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

            if action == 'on':
                laser_action = LASER_ACTION.ON
            elif action == 'off':
                laser_action = LASER_ACTION.OFF
            elif action == 'blink':
                laser_action = LASER_ACTION.BLINK
            else:
                await self.error_response("bad_action")

            r = rover_hal.laser_ctrl(laser_action)
            if r == ROVER_STATUS.OK:
                await self.success_response()

        except Exception as e:
            print(type(e))  # the exception instance
            print(e.args)  # arguments stored in .args
            print(e)
            await self.error_response("bad_params")

    async def cmd_list_faces(self, message):
        pass


class BroadcastOutput(object):
    def __init__(self):
        print('Spawning background conversion process')
        self.command = f'ffmpeg \
-f v4l2 -input_format yuyv422 -s {rover_shared_data.data["stream_size"][0]}x{rover_shared_data.data["stream_size"][1]} \
 -r 30 -i /dev/video0 -an \
-vcodec mpeg2video -q:v 7  \
-map 0:0 -threads 4 -an \
-sdp_file {rover_shared_data.conf_file_name} \
-f rtp rtp://{rover_shared_data.server_address}:{rover_shared_data.stream_port}'

        print(self.command)
        self.converter = None

    async def start(self):
        atexit.register(self.cleanup)
        self.converter = await asyncio.create_subprocess_shell(self.command, stdin=asyncio.subprocess.PIPE,
                                                               close_fds=False,
                                                               shell=True)

    def cleanup(self):
        self.converter.kill()

    def write(self, b):
        self.converter.stdin.write(b)


async def main():
    global rover_shared_data

    # Standard argument parsing
    parser = argparse.ArgumentParser(description='Start the dispatcher')
    parser.add_argument('-c', '--command_port', default=6666, type=int, help='The port on which to open the server')
    parser.add_argument('-t', '--stream_port', default=7777, type=int, help='The port on which to open the websocket')
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

    with open(rover_shared_data.rover_data_file) as f:
        rover_shared_data.data = json.load(f)

    # rover_hal.open_serial()

    # logger = logging.getLogger('websockets')
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(logging.StreamHandler())

    print('Initializing broadcast thread')
    output = BroadcastOutput()

    print('Initializing command thread')
    rover_handler = RoverRequestHandler()

    print('Starting recording')

    # await output.start()
    #
    # while True:
    #     asyncio.sleep(10)

    await asyncio.gather(rover_handler.connect(), output.start())
    await rover_handler.serve()


if __name__ == '__main__':
    asyncio.run(main())
    asyncio.get_event_loop().run_forever()
