import asyncio
import websockets
import json
import sys

async def send_and_recv( socket, message_dict ):
    request = json.dumps(message_dict)
    print(f"< {request}")
    await socket.send(request)
    response = await socket.recv()
    print(f"< {response}")

async def hello():
    async with websockets.connect(
            'ws://localhost:8888') as websocket:
            
        request = {}
        led_status = False
        
        while True:
            c = sys.stdin.read(1) # reads one byte at a time, similar to getchar()
            if c == 'w':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['forward'] } }
            elif c == 'a':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['left'] } }  
            elif c == 's':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['back'] } }
            elif c == 'd':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['right'] } }
            elif c == 'q':
                request= { 'cmd' : 'move_cam', 'params' : { 'direction' : 'up' } }
            elif c == 'e':
                request= { 'cmd' : 'move_cam', 'params' : { 'direction' : 'down' } }
            elif c == 'r':
                if led_status:
                    request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'off' } }
                else:
                    request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'on' } }
                led_status = not led_status
            elif c == 't':
                request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'blink' } }

            
            await send_and_recv( websocket, request )


asyncio.get_event_loop().run_until_complete(hello())