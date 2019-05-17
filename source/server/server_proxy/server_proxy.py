import os
import json
import argparse
import asyncio
import time
import uuid
import atexit

import websockets
import threading

from struct import Struct
import cv2


class ServerData():
    def __init__(self):
        self.stream_port = 8889
        self.ctrl_port = 6666
        self.e_ctrl_port = 8888


class StreamData():
    def __init__(self):
        self.width = 640
        self.height = 480
        self.framerate = 30
        self.jsmpeg_magic = b'jsmp'
        self.jsmpeg_header = Struct('>4sHH')


server_data = ServerData()
stream_data = StreamData()


class CVHelper(object):

    def __init__(self):
        cascade_path = './haarcascades/haarcascade_frontalface_alt.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)


shared_cv_helper = CVHelper()


class VideoCaptureTreading:
    def __init__(self, src):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.thread = None
        self.read_lock = threading.Lock()
        self.read_next = True

    def start(self):
        print(f'Starting to capture from {self.src}')
        if self.started:
            print('[!] Threaded video capturing has already been started.')
            return None
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.start()
        atexit.register(self.stop)
        return self

    def update(self):
        while self.started:
            time.sleep(1.0 / 25.0)
            grabbed, frame = self.cap.read()

            if self.read_next:
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
                    self.read_next = False

            # Display the resulting frame
            # cv2.imshow('frame', self.frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

    def read(self):
        if not self.read_next:
            with self.read_lock:
                frame = self.frame.copy()
                grabbed = self.grabbed
                self.read_next = True
            return grabbed, frame
        return False, None

    def stop(self):
        self.started = False
        self.thread.join()

    def __exit__(self, exec_type, exc_value, traceback):
        self.cap.release()


class RoverHandler:

    def __init__(self, hello_cmd, cv_helper, reader, writer):
        self.rover_id = hello_cmd['rover_id']
        self.description = hello_cmd['description']
        self.stream_path = f'{self.rover_id}.sdp'
        self.cap = None
        self.converter = None
        self.cv_helper = cv_helper
        self.reader = reader
        self.writer = writer
        self.rover_clients = dict()
        self.stream_clients = dict()

    def start_capture(self):
        self.cap = VideoCaptureTreading(self.stream_path)
        self.cap.start()

    async def start_conversion(self):
        print('Spawning background conversion process')
        try:

            command = f'ffmpeg -f rawvideo -pix_fmt bgr24 -s {stream_data.width}x{stream_data.height} -i - \
            -threads 8 -f mpeg1video -'

            self.converter = await asyncio.create_subprocess_shell(command,
                                                                   stdin=asyncio.subprocess.PIPE,
                                                                   stdout=asyncio.subprocess.PIPE,
                                                                   stderr=asyncio.subprocess.DEVNULL,
                                                                   close_fds=False, shell=True)
            atexit.register(lambda: self.converter.kill())
            asyncio.create_task(self.start_streaming())

            while True:
                await asyncio.sleep(1.0 / 25.0)
                grabbed, frame = self.cap.read()
                if grabbed:
                    self.converter.stdin.write(frame.tostring())
                    await self.converter.stdin.drain()

        except Exception as inst:
            print(type(inst))  # the exception instance
            print(inst.args)  # arguments stored in .args
            print(inst)

    async def start_streaming(self):
        print('Starting streaming')
        try:
            while True:
                buf = await self.converter.stdout.read(32768)
                if buf:
                    for ws in self.stream_clients.values():
                        try:
                            await ws.send(buf)
                        except:
                            pass
        finally:
            self.converter.stdout.close()

    def add_rover_client(self, client_id, websocket):
        print(f'Rover client {client_id} added to rover {self.rover_id}')
        self.rover_clients[client_id] = websocket

    def add_stream_client(self, client_id, websocket):
        print(f'Stream client {client_id} added to rover {self.rover_id}')
        self.stream_clients[client_id] = websocket

    def read_next_frame(self):
        pass


class ProxyServer(object):
    def __init__(self):
        self.id = uuid.uuid1()
        self.rover_handlers = dict()

    async def greet_rover(self, reader, writer):
        print('Rover connected')

        hello_msg = await reader.readline()
        hello_cmd = json.loads(hello_msg.decode())

        self.rover_handlers[hello_cmd['rover_id']] = RoverHandler(hello_cmd, shared_cv_helper, reader, writer)

        stream_set_msg = await reader.readline()
        stream_set_cmd = json.loads(stream_set_msg.decode())
        print(stream_set_cmd)

        with open(f'{hello_cmd["rover_id"]}.sdp', 'w') as f:
            f.write(stream_set_cmd['conf'])

        self.rover_handlers[hello_cmd['rover_id']].start_capture()

        await self.rover_handlers[hello_cmd['rover_id']].start_conversion()

    async def greet_rover_client(self, websocket, path):
        print('Rover Client connected')

        hello_msg = await websocket.recv()
        print(hello_msg)

        #hello_cmd = json.loads(hello_msg)

        hello_response = {'server_id': str(self.id), 'msg': 'ack'}

        await self.send_websocket_message(hello_response, websocket)

        list_msg = await websocket.recv()
        # list_cmd = json.loads(list_msg.decode())

        print(list_msg)

        await self.do_list_command(websocket)

        connect_msg = await websocket.recv()
        connect_cmd = json.loads(connect_msg)

        print(connect_msg)

        self.rover_handlers[connect_cmd['rover_id']].add_rover_client(connect_cmd['client_id'], websocket)

        connect_response = {'server_id': str(self.id), 'client_id': connect_cmd['client_id'],
                            'rover_id': connect_cmd['rover_id'], 'msg': 'ok'}

        await self.send_websocket_message(connect_response, websocket)

    async def do_list_command(self, websocket):
        rovers_list = list(
            map(lambda r: {'rover_id': r.rover_id, 'description': r.description}, self.rover_handlers.values()))

        list_response = {'server_id': str(self.id), 'rovers': rovers_list}

        await self.send_websocket_message(list_response, websocket)

    async def greet_stream_client(self, websocket, path):
        print('Stream Client connected')

        connect_msg = await websocket.recv()
        connect_cmd = json.loads(connect_msg)

        connect_response = {'server_id': str(self.id), 'client_id': connect_cmd['client_id'],
                            'rover_id': connect_cmd['rover_id'], 'msg': 'ok'}

        await self.send_websocket_message(connect_response, websocket)

        await websocket.send(stream_data.jsmpeg_header.pack(stream_data.jsmpeg_magic, stream_data.width,
                                                            stream_data.height))

        self.rover_handlers[connect_cmd['rover_id']].add_stream_client(connect_cmd['client_id'], websocket)

        while True:
            await asyncio.sleep(100)

    async def serve_rovers(self):
        print('Starting internal rover server')
        server = await asyncio.start_server(
            self.greet_rover, '0.0.0.0', server_data.ctrl_port)

        return server.serve_forever()

    async def server_rover_clients(self):
        print('Starting external rover server')
        conn = websockets.serve(self.greet_rover_client, '0.0.0.0', server_data.e_ctrl_port)
        return conn

    async def serve_stream_clients(self):
        print('Starting external stream server')
        conn = websockets.serve(self.greet_stream_client, '0.0.0.0', server_data.stream_port)
        return conn

    # Send the message, given as dictionary, to the socket, encoded as json
    @staticmethod
    async def send_socket_message(message, writer):
        try:
            encoded_msg = json.dumps(message) + '\n'
            await writer.write(encoded_msg.encode())
        except Exception as e:
            print(e)

    # Send the message, given as dictionary, to the socket, encoded as json
    @staticmethod
    async def send_websocket_message(message, websocket):
        try:
            encoded_msg = json.dumps(message) + '\n'
            await websocket.send(encoded_msg)
        except Exception as e:
            print(e)

    async def start_all(self):
        await asyncio.gather(await self.serve_rovers(),
                             await self.server_rover_clients(),
                             await self.serve_stream_clients())


async def main():
    global server_data, stream_data

    # Standard argument parsing
    parser = argparse.ArgumentParser(description='Start the dispatcher')
    parser.add_argument('-c', '--control_port', default=6666, type=int, help='The internal ctrl port')
    parser.add_argument('-ctrl', '--external_control_port', default=8888, type=int, help='The external ctrl port')

    parser.add_argument('-t', '--stream_port', default=8889, type=int, help='The external stream port')

    args = parser.parse_args()

    server_data.ctrl_port = args.control_port
    server_data.e_ctrl_port = args.external_control_port

    server_data.stream_port = args.stream_port

    # Move script to http folder
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'protocol_whitelist;file,rtp,udp'

    proxy_server = ProxyServer()

    print(f'Serving on ctrl port {server_data.ctrl_port}, stream port {server_data.stream_port}')
    await proxy_server.start_all()


if __name__ == '__main__':
    asyncio.run(main())
