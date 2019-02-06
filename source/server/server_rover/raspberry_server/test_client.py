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
            c = input() # reads one byte at a time, similar to getchar()
            
            if c == 'w':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['forward'] } }
            elif c == 'a':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['left'] } }
            if c == 'wa':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['forward', 'left'] } }
            elif c == 'wd':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['forward', 'right'] } }
            elif c == 's':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['back'] } }
            elif c == 'sa':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['back', 'left'] } }
            elif c == 'sd':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['back', 'right'] } }
            elif c == 'd':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['right'] } }
            elif c == 'q':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['ccw'] } }
            elif c == 'e':
                request= { 'cmd' : 'move', 'params' : { 'direction' : ['cw'] } }
            elif c == 'r':
                request= { 'cmd' : 'move_cam', 'params' : { 'direction' : 'up' } }
            elif c == 'f':
                request= { 'cmd' : 'move_cam', 'params' : { 'direction' : 'down' } }
            elif c == 'h':
                request= { 'cmd' : 'move_stop', 'params' : { 'motors' : ['wheels', 'camera'] } }                
            elif c == 'i':
                if led_status:
                    request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'off' } }
                else:
                    request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'on' } }
                led_status = not led_status
            elif c == 't':
                request= { 'cmd' : 'laser_ctrl', 'params' : { 'action' : 'blink' } }

            
            await send_and_recv( websocket, request )


asyncio.get_event_loop().run_until_complete(hello())