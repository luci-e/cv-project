import pdb
import os 
import json
import time
import sys
import argparse
import asyncio
import websockets

from enum import Flag
from threading import Thread

PORT = 80
#rover_hal = rover_HAL()

class DIRECTION( Flag ):
    FORWARD = 1
    BACK = 2
    LEFT = 4
    RIGHT = 8

# The rover Hardware Abastraction Layer handles all requests that must be handled 
# by the hardware. Although not enforced, this is a singleton.
class rover_HAL():
    def __init__(self):
        pass

    def is_blocked( self ):
        pass

    def move( self, direction ):
        pass

class rover_request_handler():
    def __init__(self, websocket, path):
        self.socket = websocket
        self.path = path

    async def serve(self):
        try:
            async for message in self.socket:
                await self.process(message)
        except:
            print('Connection lost')

    async def process(self, message):
        
        try:
            msg = json.loads(message)
            cmd = msg['cmd']

            if( cmd == 'move' ):
                await cmd_move(msg)
            elif( cmd == 'move_cam' ):
                await cmd_move_camera(msg)
            elif( cmd == 'track' ):
                await cmd_track_person(msg)
            elif( cmd == 'untrack' ):
                await cmd_untrack_person(msg)
            elif( cmd == 'attack' ):
                await cmd_attack_person(msg)
            elif( cmd == 'stop_attack' ):
                await cmd_stop_attack_person(msg)
            elif( cmd == 'laser_ctrl' ):
                await cmd_laser_ctrl(msg)
            elif( cmd == 'list_faces' ):
                await cmd_list_faces(msg)
            else:
                await error_response("unknown_cmd")
        except:
            await error_response("parsing_error")


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
                  "info" : "{failure_reason}" }
        await send_message(error)

    async def success_response( self  ):
        ok = { "msg" : "ok" }
        await send_message(ok)

    async def cmd_move(self, message):

        # Define the set of sets of allowed directions and combinations
        allowed_directions = set( [ set( ['forward'] ),
                                    set( ['back']),
                                    set( ['left']),
                                    set( ['right']),
                                    set( ['forward', 'left']),
                                    set( ['forward', 'right']),
                                    set( ['back', 'left']),
                                    set( ['back', 'right'])
                                 ] )

        try:
            params = json.loads( message['params'] )

            direction = set(params['direction'])

            if( direction in allowed_directions ):

                rover_dir = None

                if( direction == set( ['forward'] ) ):
                    rover_dir = DIRECTION.FORWARD
                elif( direction == set( ['back']) ):
                    rover_dir = DIRECTION.BACK
                elif( direction == set( ['left']) ):
                    rover_dir = DIRECTION.LEFT
                elif( direction == set( ['right']) ):
                    rover_dir = DIRECTION.RIGHT
                elif( direction == set( ['forward', 'left']) ):
                    rover_dir = DIRECTION.FORWARD | DIRECTION.LEFT
                elif( direction == set( ['forward', 'right']) ):
                    rover_dir = DIRECTION.FORWARD | DIRECTION.RIGHT
                elif( direction == set( ['back', 'left']) ):
                   rover_dir = DIRECTION.BACK | DIRECTION.LEFT
                elif( direction == set( ['back', 'right'] ) ):
                   rover_dir = DIRECTION.BACK | DIRECTION.RIGHT

                r = rover_hal.move( rover_dir )
                if ( r == 0 ):
                    await success_response()
                else:
                    await error_response("blocked") 

            else:
                await error_response("bad_direction") 

        except:
            await error_response("bad_params")


    async def cmd_move_camera(self, message):
        pass

    async def cmd_track_person(self, message):
        pass

    async def cmd_untrack_person(self, message):
       pass

    async def cmd_attack_person(self, message):
        pass

    async def cmd_stop_attack_person(self, message):
        pass

    async def cmd_laser_ctrl(self, message):
        pass

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

        conn = websockets.serve( self.greet, 'localhost', PORT )

        asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().run_forever()

def main():
    global PORT

    # Standard argument parsing
    parser = argparse.ArgumentParser( description = 'Start the dispatcher')
    parser.add_argument('-p', '--port' , default = 80, type = int , help = 'The port on which to open the server')
    args = parser.parse_args()

    PORT = args.port

    # Start server
    server_thread = rover_server_thread()
    server_thread.start()

if __name__ == '__main__':
    main()
