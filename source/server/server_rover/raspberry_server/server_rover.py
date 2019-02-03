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

from enum import Flag
from threading import Thread

# The enum of the possible directions the rover can move
class ROVER_DIRECTION( Flag ):
    STOP = 0
    FORWARD = 1
    BACK = 2
    LEFT = 4
    RIGHT = 8
    CW = 16
    CCW = 32

# The enum of the possible directions the camera can move
class CAM_DIRECTION( Flag ):
    STOP = 0
    UP = 1
    DOWN = 2

# The enum of the possible motors on the rover
class ROVER_MOTORS( Flag ):
    WHEELS = 1
    CAMERA = 2

# The enum of the possible statuses for the laser
class LASER_ACTION( Flag ):
    ON = 1
    OFF = 2
    BLINK = 4

# The enum of the possible status of the camera after a move command
class ROVER_STATUS( Flag ):
    OK = 0
    BLOCKED = 1
    CAM_TOP_LIMIT = 2
    CAM_BOTTOM_LIMIT = 4



# The rover Hardware Abastraction Layer handles all requests that must be handled 
# by the hardware. Although not enforced, this is a singleton.
class rover_HAL():

    def __init__(self):
        pass

    def open_serial(self):
        self.ser = serial.Serial( rover_shared_data.serial_port )

    def send_serial_command(self, command):
        self.ser.write(command)

    def is_blocked( self ):
        pass

    def move( self, direction ):
        serial_command = 'move '

        if( direction & ROVER_DIRECTION.FORWARD ):
            serial_command += 'w'
        if( direction & ROVER_DIRECTION.BACK ):
            serial_command += 's'
        if( direction & ROVER_DIRECTION.LEFT ):
            serial_command += 'a'
        if( direction & ROVER_DIRECTION.RIGHT ):
            serial_command += 'd'
        if( direction & ROVER_DIRECTION.CW ):
            serial_command += 'cw'
        if( direction & ROVER_DIRECTION.CCW ):
            serial_command += 'ccw'

        serial_command += '\n'

        self.send_serial_command( bytes(serial_command, 'ascii') )
       
        return ROVER_STATUS.OK

    def move_cam( self, direction ):
        serial_command = 'move_cam '

        if( direction & CAM_DIRECTION.UP ):
            serial_command += 'r'
        if( direction & CAM_DIRECTION.DOWN ):
            serial_command += 'f'

        serial_command += '\n'

        self.send_serial_command( bytes(serial_command, 'ascii') )
        return ROVER_STATUS.OK


    def stop_motors( self, motors ):

        serial_command = 'move_stop '

        if( motors & ROVER_MOTORS.WHEELS ):
            serial_command += 'w'
        if( motors & ROVER_MOTORS.CAMERA ):
            serial_command += 'c'

        serial_command += '\n'

        self.send_serial_command( bytes(serial_command, 'ascii') )
        return ROVER_STATUS.OK


    def laser_ctrl( self, action ):

        serial_command = 'laser_ctrl '

        if( direction & LASER_ACTION.ON ):
            serial_command += 'i'
        if( direction & LASER_ACTION.OFF ):
            serial_command += 'o'

        serial_command += '\n'

        self.send_serial_command( bytes(serial_command, 'ascii') )
        return ROVER_STATUS.OK

# A class holding all data that is common to the rover and can be accessed by any other
# class. Although not enforced, this is a singleton.
class rover_data():
    def __init__(self):
        self.PORT = 8888
        self.serial_port = ''

class rover_request_handler():
    def __init__(self, websocket, path, cleanup_fun = None):
        self.socket = websocket
        self.path = path
        self.cleanup_fun = cleanup_fun

    async def serve(self):
        print(self.socket)
        try:
            async for message in self.socket:
                print(f'{message}')
                await self.process(message)

            print('Bye Bye JoJo')
            self.cleanup_fun(self)

        except Exception as e:
            print(type(e))    # the exception instance
            print(e.args)     # arguments stored in .args
            print(e)

            print('Connection lost')


    async def process(self, message):
        try:
            msg = json.loads(message)
            cmd = msg['cmd']

            if( cmd == 'move' ):
                await self.cmd_move(msg)
            elif( cmd == 'move_cam' ):
                await self.cmd_move_camera(msg)
            elif( cmd == 'move_stop' ):
                await self.cmd_move_stop(msg)
            elif( cmd == 'track' ):
                await self.cmd_track_person(msg)
            elif( cmd == 'untrack' ):
                await self.cmd_untrack_person(msg)
            elif( cmd == 'attack' ):
                await self.cmd_attack_person(msg)
            elif( cmd == 'stop_attack' ):
                await self.cmd_stop_attack_person(msg)
            elif( cmd == 'laser_ctrl' ):
                await self.cmd_laser_ctrl(msg)
            elif( cmd == 'list_faces' ):
                await self.cmd_list_faces(msg)
            else:
                await self.error_response("unknown_cmd")    
        except Exception as e:
            print(type(e))    # the exception instance
            print(e.args)     # arguments stored in .args
            print(e)
            await self.error_response("parsing_error")


    # Send the message, given as dictionary, to the socket, encoded as json
    async def send_message(self, message):
        try:
            encoded_msg = json.dumps(message)
            await self.socket.send(encoded_msg)
        except:
            print('Connection lost')

    # Creates a standard error response, where the info field is set as failure reason
    # it then sends the message to the socket
    async def error_response( self, failure_reason ):
        error = { "msg" : "failed",
                  "info" : f"{failure_reason}" }
        await self.send_message(error)

    async def success_response( self  ):
        ok = { "msg" : "ok" }
        await self.send_message(ok)

    # Attempts to move the rover in the desired directions, failing if the rover
    # encounters an obstacle.
    async def cmd_move(self, message):

        print(f'Processing move command')

        # Define the set of sets of allowed directions and combinations
        allowed_directions = set( [ frozenset( ['forward'] ),
                                    frozenset( ['back']),
                                    frozenset( ['left']),
                                    frozenset( ['right']),
                                    frozenset( ['forward', 'left']),
                                    frozenset( ['forward', 'right']),
                                    frozenset( ['back', 'left']),
                                    frozenset( ['back', 'right']),
                                    frozenset( ['cw']),
                                    frozenset( ['ccw'])
                                 ] )

        try:
            params = message['params']

            direction = frozenset(params['direction'])

            if( direction in allowed_directions ):

                rover_dir = None

                if( direction == frozenset( ['forward'] ) ):
                    rover_dir = ROVER_DIRECTION.FORWARD
                elif( direction == frozenset( ['back']) ):
                    rover_dir = ROVER_DIRECTION.BACK
                elif( direction == frozenset( ['left']) ):
                    rover_dir = ROVER_DIRECTION.LEFT
                elif( direction == frozenset( ['right']) ):
                    rover_dir = ROVER_DIRECTION.RIGHT
                elif( direction == frozenset( ['cw']) ):
                    rover_dir = ROVER_DIRECTION.CW
                elif( direction == frozenset( ['ccw']) ):
                    rover_dir = ROVER_DIRECTION.CCW
                elif( direction == frozenset( ['forward', 'left']) ):
                    rover_dir = ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.LEFT
                elif( direction == frozenset( ['forward', 'right']) ):
                    rover_dir = ROVER_DIRECTION.FORWARD | ROVER_DIRECTION.RIGHT
                elif( direction == frozenset( ['back', 'left']) ):
                   rover_dir = ROVER_DIRECTION.BACK | ROVER_DIRECTION.LEFT
                elif( direction == frozenset( ['back', 'right'] ) ):
                   rover_dir = ROVER_DIRECTION.BACK | ROVER_DIRECTION.RIGHT


                r = rover_hal.move( rover_dir )
                if ( r ==  ROVER_STATUS.OK ):
                    await self.success_response()
                else:
                    await self.error_response("blocked") 

            else:
                await self.error_response("bad_direction") 

        except Exception as e:
            print(type(e))    # the exception instance
            print(e.args)     # arguments stored in .args
            print(e)
            await self.error_response("bad_params")


    # Attempts to move the camera in the desired direction, failing if the camera
    # has reached the top or bottom limit.
    async def cmd_move_camera(self, message):

        print(f'Processing move camera command')


        try:
            params = message['params']

            direction = params['direction']
            cam_dir = None

            if( direction == 'up' ):
                cam_dir = CAM_DIRECTION.UP
            elif( direction == 'down' ):
                cam_dir = CAM_DIRECTION.DOWN
            else:
                await self.error_response("bad_direction") 

            r = rover_hal.move_cam( cam_dir )
            if ( r == ROVER_STATUS.OK ):
                await self.success_response()
            elif( r == ROVER_STATUS.CAM_TOP_LIMIT ):
                await self.error_response("top_limit")
            elif( r == ROVER.CAM_BOTTOM_LIMIT ):
                await self.error_response("bottom_limit")
        except:
            await self.error_response("bad_params")

    # Stops the desired movements
    async def cmd_move_stop(self, message):

        print(f'Processing move stop command')

        # Define the set of sets of allowed motors and combinations
        allowed_motors  = set( [ frozenset( ['wheels'] ),
                                    frozenset( ['camera']),
                                    frozenset( ['camera', 'wheels'])
                                 ] )

        try:
            params = message['params']

            motors = frozenset(params['motors'])

            if( motors in allowed_motors ):

                stopped_motors = None

                if( motors == frozenset( ['wheels'] ) ):
                    stopped_motors = ROVER_MOTORS.WHEELS 
                elif( motors == frozenset( ['camera'] ) ):
                    stopped_motors = ROVER_MOTORS.CAMERA 
                elif( motors == frozenset( ['wheels', 'camera'] ) ):
                    stopped_motors = ROVER_MOTORS.WHEELS | ROVER_MOTORS.CAMERA

                r = rover_hal.stop_motors( stopped_motors )

                if ( r == ROVER_STATUS.OK ):
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

        print(f'Processing laser control command')

        try:
            params = message['params']

            action = params['action']
            laser_action = None

            if( action == 'on' ):
                laser_action = LASER_ACTION.ON
            elif( action == 'off' ):
                laser_action = LASER_ACTION.OFF
            elif( action == 'blink' ):
                laser_action = LASER_ACTION.BLINK
            else:
                await self.error_response("bad_action") 

            r = rover_hal.laser_ctrl( laser_action )
            if ( r == ROVER_STATUS.OK ):
                await self.success_response()

        except:
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

    async def greet( self, websocket, path):
        print('Client connected')
        request_handler = rover_request_handler( websocket, path, cleanup_fun = self.cleanup )
        self.active_connections.add(request_handler)
        await request_handler.serve()

    def cleanup( self, request_handler):
        self.active_connections.remove(request_handler)

    def run(self):
        print('Rover Server started')

        # Create a new event loop for asyncio, start serving by creating a 
        # new request handler for each new connection
        asyncio.set_event_loop( asyncio.new_event_loop())

        conn = websockets.serve( self.greet, '0.0.0.0', rover_shared_data.PORT )

        awaitable = asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().run_forever()


#>>>>>>>>>> GLOBAL VARIABLES <<<<<<<<<<#

rover_hal = rover_HAL()
rover_shared_data = rover_data()

def main():
    global rover_shared_data

    # Standard argument parsing
    parser = argparse.ArgumentParser( description = 'Start the dispatcher')
    parser.add_argument('-p', '--port' , default = 8888, type = int , help = 'The port on which to open the server')
    parser.add_argument('-s', '--serial' , default = '/dev/ttyUSB0', help = 'The serial port to communicate with the arduino')
    args = parser.parse_args()

    rover_shared_data.PORT = args.port
    rover_shared_data.serial_port = args.serial

    rover_hal.open_serial()

    logger = logging.getLogger('websockets')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    # Start server
    server_thread = rover_server_thread()
    server_thread.start()

if __name__ == '__main__':
    main()
