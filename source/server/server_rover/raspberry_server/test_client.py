import asyncio
import websockets
import json
import sys
import uuid
import atexit


async def send_and_recv(socket, message_dict):
    request = json.dumps(message_dict)
    print(f"< {request}")
    await socket.send(request)
    response = await socket.recv()
    print(f"< {response}")


async def hello():
    async with websockets.connect(
            'ws://localhost:7778') as websocket:

        request = {}
        led_status = False

        while True:
            c = input()  # reads one byte at a time, similar to getchar()

            if c == 'w':
                request = {'cmd': 'move', 'params': {'direction': ['forward']}}
            elif c == 'a':
                request = {'cmd': 'move', 'params': {'direction': ['left']}}
            if c == 'wa':
                request = {'cmd': 'move', 'params': {'direction': ['forward', 'left']}}
            elif c == 'wd':
                request = {'cmd': 'move', 'params': {'direction': ['forward', 'right']}}
            elif c == 's':
                request = {'cmd': 'move', 'params': {'direction': ['back']}}
            elif c == 'sa':
                request = {'cmd': 'move', 'params': {'direction': ['back', 'left']}}
            elif c == 'sd':
                request = {'cmd': 'move', 'params': {'direction': ['back', 'right']}}
            elif c == 'd':
                request = {'cmd': 'move', 'params': {'direction': ['right']}}
            elif c == 'q':
                request = {'cmd': 'move', 'params': {'direction': ['ccw']}}
            elif c == 'e':
                request = {'cmd': 'move', 'params': {'direction': ['cw']}}
            elif c == 'r':
                request = {'cmd': 'move_cam', 'params': {'direction': 'up'}}
            elif c == 'f':
                request = {'cmd': 'move_cam', 'params': {'direction': 'down'}}
            elif c == 'h':
                request = {'cmd': 'move_stop', 'params': {'motors': ['wheels', 'camera']}}
            elif c == 'i':
                if led_status:
                    request = {'cmd': 'laser_ctrl', 'params': {'action': 'off'}}
                else:
                    request = {'cmd': 'laser_ctrl', 'params': {'action': 'on'}}
                led_status = not led_status
            elif c == 't':
                request = {'cmd': 'laser_ctrl', 'params': {'action': 'blink'}}

            await send_and_recv(websocket, request)


rover_list = None

server_address = 'localhost'
e_ctrl_port = 6667
stream_port = 7778
client_id = uuid.uuid1()


async def control_test():
    global rover_list

    reader, writer = await asyncio.open_connection(server_address, e_ctrl_port)

    hello_msg = {
        "client_id": str(client_id),
        "cmd": "hello"
    }

    await send_socket_message(hello_msg, writer)

    ack_msg = await reader.readline()
    print(ack_msg)

    list_cmd = {
        "client_id": str(client_id),
        "cmd": "list"
    }

    await send_socket_message(list_cmd, writer)

    list_response = await reader.readline()
    rover_list = json.loads(list_response.decode())

    print(list_response)

    connect_cmd = {
        "client_id": str(client_id),
        "rover_id": rover_list['rovers'][0]['rover_id'],
        "cmd": "connect"
    }

    await send_socket_message(connect_cmd, writer)
    connected_msg = await reader.readline()
    print(connected_msg)

    asyncio.create_task(stream_test())

    while True:
        await asyncio.sleep(10)


async def stream_test():
    print('Connecting to stream')

    try:
        async with websockets.connect('ws://localhost:7778') as websocket:

            connect_cmd = {
                "client_id": str(client_id),
                "rover_id": rover_list['rovers'][0]['rover_id'],
                "cmd": "connect"
            }

            await send_websocket_message(connect_cmd, websocket)

            connect_response = await websocket.recv()
            print(connect_response)

            stream_header = await websocket.recv()
            print(stream_header)

            command = f'ffplay -f mpeg1video -pix_fmt bgr24 -s 640x480 -i - '

            # converter = await asyncio.create_subprocess_shell(command,
            #                                                   stdin=asyncio.subprocess.PIPE,
            #                                                   stdout=asyncio.subprocess.PIPE,
            #                                                   stderr=asyncio.subprocess.DEVNULL,
            #                                                   close_fds=False, shell=True)
            # atexit.register(lambda: converter.kill())

            while True:
                frame = await websocket.recv()
                print(frame)
                # converter.stdin.write(frame)

    except Exception as e:
        print(type(e))  # the exception instance
        print(e.args)  # arguments stored in .args
        print(e)
        print('Connection lost')


async def send_socket_message(message, writer):
    try:
        encoded_msg = json.dumps(message) + '\n'
        await writer.write(encoded_msg.encode())
    except Exception as e:
        pass
        # print(type(e))  # the exception instance
        # print(e.args)  # arguments stored in .args
        # print(e)
        # print('Connection lost')


async def send_websocket_message(message, websocket):
    try:
        encoded_msg = json.dumps(message) + '\n'
        await websocket.send(encoded_msg.encode())
    except Exception as e:
        pass
        # print(type(e))  # the exception instance
        # print(e.args)  # arguments stored in .args
        # print(e)
        # print('Connection lost')


asyncio.run(control_test())
