import asyncio
import websockets
import json

async def send_and_recv( socket, message_dict ):
	request = json.dumps(message_dict)
	print(f"< {request}")
	await socket.send(request)
	response = await socket.recv()
	print(f"< {response}")

async def hello():
    async with websockets.connect(
            'ws://localhost:8888') as websocket:
        
        requests = [ { 'cmd' : 'move', 'params' : { 'direction' : ['left', 'right'] } },
                     { 'cmd' : 'move', 'params' : { 'direction' : ['forward', 'right'] } },
                     { 'cmd' : 'move', 'params' : { 'direction' : ['back', 'right'] } },
                     { 'cmd' : 'move', 'params' : { 'direction' : ['back', 'left'] } },
                     { 'cmd' : 'move', 'params' : { 'direction' : ['left', 'back'] } },
                     { 'cmd' : 'move', 'params' : { 'direction' : ['forward', 'left'] } },
                     { 'cmd' : 'move_cam', 'params' : { 'direction' : 'up' } },
                     { 'cmd' : 'move_cam', 'params' : { 'direction' : 'down' } },
                     { 'cmd' : 'move_cam', 'params' : { 'direction' : 'bo' } }
        ]

        for r in requests:
            await send_and_recv( websocket, r )

asyncio.get_event_loop().run_until_complete(hello())