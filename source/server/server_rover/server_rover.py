import pdb
import os 
import json
import time
import sys
import argparse
import asyncio
import websockets
import functools

from threading import Thread

PORT = 80


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
        print(message)
        await self.socket.send(message)


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
