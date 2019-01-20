import pdb
import os 
import json
import time
import sys
import argparse
import asyncio
import websockets


#os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')
import gpiozero
from gpiozero.pins.mock import MockFactory

from gpiozero import Device, OutputDevice, LED

# Set the default pin factory to a mock factory
#cDevice.pin_factory = MockFactory()

from enum import Flag
from threading import Thread

# The enum of the possible directions the rover can move
class ROVER_DIRECTION( Flag ):
    FORWARD = 1
    BACK = 2
    LEFT = 4
    RIGHT = 8

# The enum of the possible directions the camera can move
class CAM_DIRECTION( Flag ):
    UP = 1
    DOWN = 2

# The enum of the possible statuses for the laser
class LASER_ACTION( Flag ):
    ON = 1
    OFF = 2
    BLINK = 3

# The enum of the possible status of the camera after a move command
class ROVER_STATUS( Flag ):
    OK = 0
    BLOCKED = 1
    CAM_TOP_LIMIT = 2
    CAM_BOTTOM_LIMIT = 4

# The rover Hardware Abastraction Layer handles all requests that must be handled 
# by the hardware. Although not enforced, this is a singleton.
class rover_HAL():

    class motor_controller():
        def __init__(self, pins):
            # The number representing the status of the stepper motors in the motor steps list
            self.motor_status = 0
            self.motor_pins = [ OutputDevice(pins[0]),
                                OutputDevice(pins[1]),
                                OutputDevice(pins[2]),
                                OutputDevice(pins[3])
                            ]

            self.delay = 0.0005

            # Stepping sequence for 28BYJ-48 Stepper Motor with ULN2003 Driver
            self.motor_steps = [
                8,
                12,
                4,
                6,
                2,
                3,
                1,
                9
            ]

            self.steps_len = len(self.motor_steps)

        def step_motor(self, direction):
            if(direction):
                self.motor_status = (self.motor_status  + 1 ) % self.steps_len
            else:
                self.motor_status = (self.motor_status  - 1 + self.steps_len ) % self.steps_len

            pin_values = self.motor_steps[self.motor_status]
            for pin in range(4):
                v = pin_values >> pin & 1
                if(v):
                    self.motor_pins[pin].on()
                else:
                    self.motor_pins[pin].off()
            time.sleep(self.delay)            



    def __init__(self):


        # The pins on the raspberry pi that control
        # the motors
        # the limiting switches
        # the LASER
        # the ultrasonic sensor

        self.left_motor_pins = [6,13,19,26]
        self.right_motor_pins = [12,16,20,21]
        self.camera_motor_pins = [4,17,27,22]
        self.laser = LED(25)
        self.top_limiting_switch_pin = 0
        self.bottom_limiting_switch_pin = 0

        self.left_motor = self.motor_controller(self.left_motor_pins)
        self.right_motor = self.motor_controller(self.right_motor_pins)
        self.camera_motor = self.motor_controller(self.camera_motor_pins)

    def is_blocked( self ):
        pass

    def step_camera_motor(self, amount):
        pass

    def move( self, direction ):
        for s in range(512):
            if (direction & ROVER_DIRECTION.FORWARD):
                self.left_motor.step_motor(False)
                self.right_motor.step_motor(True)
            if (direction & ROVER_DIRECTION.BACK):
                self.left_motor.step_motor(True)
                self.right_motor.step_motor(False)
            if (direction & ROVER_DIRECTION.LEFT):
                self.left_motor.step_motor(False)
                self.right_motor.step_motor(False)
            if (direction & ROVER_DIRECTION.RIGHT):
                self.left_motor.step_motor(True)
                self.right_motor.step_motor(True)

        return ROVER_STATUS.OK

    def move_cam( self, direction ):
        for s in range(128):
            if (direction & CAM_DIRECTION.UP):
                self.camera_motor.step_motor(True)
            if (direction & CAM_DIRECTION.DOWN):
                self.camera_motor.step_motor(False)

        return ROVER_STATUS.OK

    def laser_ctrl( self, action ):
        if( action == LASER_ACTION.ON ):
            self.laser.on()
        elif( action == LASER_ACTION.OFF ):
            self.laser.on()
        elif( action == LASER_ACTION.BLINK ):
            self.laser.blink()

        return ROVER_STATUS.OK

# A class holding all data that is common to the rover and can be accessed by any other
# class. Although not enforced, this is a singleton.
class rover_data():
    def __init__(self):
        self.PORT = 8888

class rover_request_handler():
    def __init__(self, websocket, path):
        self.socket = websocket
        self.path = path

    async def serve(self):
        try:
            print('Client connected')
            while(True):
                async for message in self.socket:
                    print(f'{message}')
                    await self.process(message)
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
                                    frozenset( ['back', 'right'])
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
        request_handler = rover_request_handler( websocket, path )
        self.active_connections.add(request_handler)
        await request_handler.serve()

    def run(self):
        print('Rover Server started')

        # Create a new event loop for asyncio, start serving by creating a 
        # new request handler for each new connection
        asyncio.set_event_loop( asyncio.new_event_loop())

        conn = websockets.serve( self.greet, '0.0.0.0', rover_shared_data.PORT )

        asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().run_forever()


#>>>>>>>>>> GLOBAL VARIABLES <<<<<<<<<<#

rover_hal = rover_HAL()
rover_shared_data = rover_data()

def main():
    global rover_shared_data

    # Standard argument parsing
    parser = argparse.ArgumentParser( description = 'Start the dispatcher')
    parser.add_argument('-p', '--port' , default = 8888, type = int , help = 'The port on which to open the server')
    args = parser.parse_args()

    rover_shared_data.PORT = args.port

    # Start server
    server_thread = rover_server_thread()
    server_thread.start()

if __name__ == '__main__':
    main()
