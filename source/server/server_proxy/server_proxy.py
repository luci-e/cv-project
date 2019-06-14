import os
import json
import argparse
import asyncio
import time
import uuid
import atexit
import math
import numpy as np

import websockets
import threading

from struct import Struct
import cv2

STREAM_BLOCKSIZE = 256


class RingBuffer(object):
    def __init__(self, size, initializer=None):
        """Initialization"""
        self.index = 0
        self.size = size
        self.data = list(initializer for i in range(self.size))

    def append(self, value):
        """Append an element"""
        self.data[self.index] = value
        self.index = (self.index + 1) % self.size

    def set_all(self, value):
        self.data = list(value for i in range(self.size))
        self.index = 0

    def __getitem__(self, key):
        """Get element by index, relative to the current index"""
        if len(self.data) == self.size:
            return self.data[(key + self.index) % self.size]
        else:
            return self.data[key]

    def __repr__(self):
        """Return string representation"""
        return self.data.__repr__() + ' (' + str(len(self.data)) + ' items)'


class ServerData:
    def __init__(self):
        self.stream_port = 8889
        self.ctrl_port = 6666
        self.e_ctrl_port = 8888


class StreamData:
    def __init__(self):
        self.width = 640
        self.height = 360
        self.framerate = 60.0
        self.jsmpeg_magic = b'jsmp'
        self.jsmpeg_header = Struct('>4sHH')


server_data = ServerData()


class CVHelper(object):

    def __init__(self):
        cascade_path = './haarcascades/haarcascade_frontalface_alt.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        self.object_trackers = {
            "csrt": cv2.TrackerCSRT_create,
            "kcf": cv2.TrackerKCF_create,
            "boosting": cv2.TrackerBoosting_create,
            "mil": cv2.TrackerMIL_create,
            "tld": cv2.TrackerTLD_create,
            "medianflow": cv2.TrackerMedianFlow_create,
            "mosse": cv2.TrackerMOSSE_create
        }

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

        return faces


shared_cv_helper = CVHelper()


class VideoCaptureTreading:
    def __init__(self, src, stream_data):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.thread = None
        self.read_lock = threading.Lock()
        self.read_next = True
        self.stream_data = stream_data

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
            time.sleep(1.0 / (self.stream_data.framerate / 1.2))
            grabbed, frame = self.cap.read()

            if self.read_next:
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
                    self.read_next = False

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

    def __init__(self, hello_cmd, cv_helper, reader, writer, tracker_name='csrt'):
        self.rover_id = hello_cmd['rover_id']
        self.rover_data = hello_cmd['rover_data']
        self.description = self.rover_data['description']
        self.fov = self.rover_data['fov']

        self.has_wheels = 'wheels' in self.rover_data['mobility']
        self.has_gimbal = 'gimbal' in self.rover_data['mobility']

        self.stream_path = f'{self.rover_id}.sdp'
        self.stream_data = StreamData()
        self.stream_data.width = self.rover_data['stream_size'][0]
        self.stream_data.height = self.rover_data['stream_size'][1]

        self.cap = None
        self.converter = None
        self.cv_helper = cv_helper
        self.reader = reader
        self.writer = writer
        self.rover_clients = dict()
        self.stream_clients = dict()

        self.server_commands = {
            'track_custom': self.cmd_track_custom,
            'stop_tracking': self.cmd_stop_tracking,
            'track_faces': self.cmd_track_faces,
            'follow': self.cmd_follow
        }

        self.init_bb = None
        self.initial_area_percent = 0.0
        self.tracker = None
        self.tracking_initialized = False

        self.camera_follow_x_threshold = 5.0
        self.camera_follow_y_threshold = 5.0
        self.movement_follow_x_threshold = 50.0
        self.movement_follow_y_threshold = 50.0
        self.last_distances = RingBuffer(5, 99999)
        self.last_areas = RingBuffer(5, 99999)
        self.distance_threshold = 0.0
        self.target_area_increase = 1.15
        self.stop_sent = False
        self.camera_wiggle_dampener = 20.0
        self.follow_area_threshold = -0.01
        self.movement_wiggle_dampener = 0.02
        self.rotational_dampener = 50

        self.tracking_custom = False
        self.tracking_face = False
        self.following_wheels = False
        self.following_camera = False
        self.centre = None
        self.delta_x = 0.0
        self.delta_y = 0.0
        self.dist = 0.0
        self.current_area_percent = 0.0

        self.tracker_name = tracker_name
        self.success = False
        self.box = None
        self.set_obj_tracker(self.tracker_name)

    def start_capture(self):
        self.cap = VideoCaptureTreading(self.stream_path, self.stream_data)
        self.cap.start()

    def set_obj_tracker(self, tracker_name):
        self.tracker_name = tracker_name
        self.tracker = self.cv_helper.object_trackers[self.tracker_name]()

    def init_tracking_roi(self, frame):
        if self.tracker is not None:
            self.tracker.clear()

        self.tracker = self.cv_helper.object_trackers[self.tracker_name]()
        self.tracker.init(frame, self.init_bb)
        self.tracking_initialized = True

    def track_roi(self, frame):
        self.success, self.box = self.tracker.update(frame)

        # check to see if the tracking was a success
        if self.success:
            (x, y, w, h) = [int(v) for v in self.box]
            cv2.rectangle(frame, (x, y), (x + w, y + h),
                          (0, 255, 0), 2)

    def initialize_bb(self, bb):
        self.init_bb = bb
        self.initial_area_percent = self.area_percent(bb)

    @staticmethod
    def box_centre(box):
        return box[0] + box[2] / 2, box[1] + box[3] / 2

    def area_percent(self, bb):
        return (bb[2] * bb[3]) / (self.stream_data.width * self.stream_data.height)

    def reset_distance(self):
        self.last_distances.set_all(9999)

    def reset_area(self):
        self.last_areas.set_all(9999)

    async def follow_move_camera(self):
        move_cam = []

        move_x = abs(self.delta_x) > self.camera_follow_x_threshold
        move_y = abs(self.delta_y) > self.camera_follow_y_threshold

        adj_speed_x = round(90.0 * (abs(self.delta_x) / self.stream_data.width) ** 1.2, 2)
        adj_speed_y = round(90.0 * (abs(self.delta_y) / self.stream_data.height) ** 1.2, 2)

        if self.dist > self.distance_threshold:
            self.last_distances.append(self.dist)

            if np.average(self.last_distances.data) < self.camera_wiggle_dampener:
                if not self.stop_sent:
                    msg = {'cmd': 'move_stop', 'params': {'motors': ['camera']}}
                    print(msg)
                    self.stop_sent = True
                    await send_socket_message(msg, self.writer)
            else:
                self.stop_sent = False

                if adj_speed_y > 0.2 and adj_speed_x > 0.2:
                    msg = {'cmd': 'set_cam_speed', 'params': {'speed': [adj_speed_x, adj_speed_y]}}
                    print(msg)
                    await send_socket_message(msg, self.writer)

                if move_x:
                    if self.delta_x > 0:
                        move_cam.append('cw')
                    else:
                        move_cam.append('ccw')
                if move_y:
                    if self.delta_y > 0:
                        move_cam.append('down')
                    else:
                        move_cam.append('up')

                if move_cam:
                    msg = {'cmd': 'move_cam', 'params': {'direction': move_cam}}
                    print(msg)
                    await send_socket_message(msg, self.writer)

    async def follow_move_wheels(self):
        move_cmd = []

        move_x = abs(self.delta_x) > self.movement_follow_x_threshold
        move_y = abs(self.delta_y) > self.movement_follow_y_threshold

        delta_area = self.current_area_percent - self.initial_area_percent
        #print(f'Delta area: {delta_area}')

        if delta_area < self.follow_area_threshold:
            self.last_areas.append(abs(delta_area))

            if np.average(self.last_areas.data) < self.movement_wiggle_dampener:
                if not self.stop_sent:
                    msg = {'cmd': 'move_stop', 'params': {'motors': ['wheels']}}
                    print(msg)
                    self.stop_sent = True
                    await send_socket_message(msg, self.writer)
            else:
                move_cmd.append('forward')
                self.stop_sent = False
                adj_speed = round(0.1 * (1 + abs(delta_area)), 2)

                if adj_speed > 0.04:
                    msg = {'cmd': 'set_speed', 'params': {'speed': adj_speed}}
                    print(msg)
                    await send_socket_message(msg, self.writer)

                if move_x:
                    if self.delta_x > 0:
                        move_cmd.append('right')
                    else:
                        move_cmd.append('left')

                msg = {'cmd': 'move', 'params': {'direction': move_cmd}}
                print(msg)
                await send_socket_message(msg, self.writer)
        else:
            if move_x:
                self.last_distances.append(abs(self.delta_x))

                if np.average(self.last_distances.data) < self.rotational_dampener:
                    if not self.stop_sent:
                        msg = {'cmd': 'move_stop', 'params': {'motors': ['camera']}}
                        print(msg)
                        self.stop_sent = True
                        await send_socket_message(msg, self.writer)
                else:
                    adj_speed = round(0.005 * (1 + (abs(self.delta_x) / self.stream_data.width) ** 3), 10)

                    if adj_speed > 0:
                        msg = {'cmd': 'set_speed', 'params': {'speed': adj_speed}}
                        print(msg)
                        await send_socket_message(msg, self.writer)

                    if self.delta_x > 0:
                        move_cmd.append('right')
                    else:
                        move_cmd.append('left')

                    self.stop_sent = False
                    msg = {'cmd': 'move', 'params': {'direction': move_cmd}}
                    print(msg)
                    await send_socket_message(msg, self.writer)

            else:
                if not self.stop_sent:
                    msg = {'cmd': 'move_stop', 'params': {'motors': ['wheels']}}
                    print(msg)
                    self.stop_sent = True
                    await send_socket_message(msg, self.writer)

    async def follow_roi(self):
        if self.following_wheels or self.following_camera:
            if self.success:

                self.centre = self.box_centre(self.box)
                self.delta_x = self.centre[0] - self.stream_data.width / 2
                self.delta_y = self.centre[1] - self.stream_data.height / 2
                self.dist = math.sqrt(self.delta_x ** 2 + self.delta_y ** 2)
                self.current_area_percent = self.area_percent(self.box)

                # print(f'Dist: {dist}')
                # print(f'Avg : {np.average(self.last_distances.data)}')
                # print(f'Stop sent at last cycle: {self.stop_sent}')
                # print(f'following dx: {delta_x} dy:{delta_y}')

                if self.following_camera and not self.following_wheels:
                    await self.follow_move_camera()
                elif self.following_wheels and not self.following_camera:
                    await self.follow_move_wheels()
                elif self.following_wheels and self.following_camera:
                    pass

    def stop_tracking_roi(self):
        if self.tracking_custom or self.tracking_face:
            self.tracking_face = False
            self.tracking_custom = False
            self.following_wheels = False
            self.following_camera = False
            self.init_bb = None
            self.initial_area_percent = 0.0

    def stop_tracking_custom(self):
        self.tracking_custom = False
        self.following_wheels = False
        self.following_camera = False
        self.init_bb = None
        self.initial_area_percent = 0.0

    def stop_tracking_face(self):
        self.tracking_face = False
        self.following_wheels = False
        self.following_camera = False
        self.init_bb = None
        self.initial_area_percent = 0.0

    async def follow(self, wheels=False, camera=False):

        if self.tracking_custom ^ self.tracking_face:
            if self.has_wheels:
                self.following_wheels = wheels
            if self.has_gimbal:
                self.following_camera = camera

            await self.reset_follow()

    async def reset_follow(self):
        if not self.following_camera:
            stop_msg = {'cmd': 'move_stop', 'params': {'motors': ['camera']}}
            speed_msg = {'cmd': 'set_cam_speed', 'params': {'speed': [20.0, 20.0]}}
            await asyncio.gather(send_socket_message(stop_msg, self.writer),
                                 send_socket_message(speed_msg, self.writer))

        if not self.following_wheels:
            stop_msg = {'cmd': 'move_stop', 'params': {'motors': ['wheels']}}
            speed_msg = {'cmd': 'set_speed', 'params': {'speed': 0.3}}
            await asyncio.gather(send_socket_message(stop_msg, self.writer),
                                 send_socket_message(speed_msg, self.writer))

    async def cmd_track_custom(self, cmd):
        params = cmd['params']
        roi = params['roi']

        if roi[0] > 0 and roi[1] > 0 and roi[2] > 0 and roi[3] > 0:
            self.initialize_bb(tuple(roi))
            self.tracking_custom = True
            self.tracking_initialized = False

    async def cmd_stop_tracking(self, cmd):
        if self.tracking_custom:
            self.stop_tracking_custom()
        elif self.tracking_face:
            self.stop_tracking_face()

    async def cmd_track_faces(self, cmd):
        self.tracking_face = True
        self.tracking_initialized = False

    async def cmd_follow(self, cmd):
        params = cmd['params']
        await self.follow(params['wheels'], params['cam'])

    async def do_tracking(self, frame):
        if self.tracking_initialized:
            self.track_roi(frame)
            await self.follow_roi()
        else:
            if self.tracking_face:
                faces = self.cv_helper.detect_faces(frame)
                if len(faces) > 0:
                    print(f'Initializing ')
                    self.initialize_bb(tuple(faces[0]))
                    self.init_tracking_roi(frame)
            elif self.tracking_custom:
                print(f'Initializing ROI')
                self.init_tracking_roi(frame)

    async def start_conversion(self):
        print('Spawning background conversion process')
        try:

            command = f'ffmpeg -f rawvideo -pix_fmt bgr24 -s {self.stream_data.width}x{self.stream_data.height} -i - \
            -threads 8 -q:v 7 -an -f mpeg1video -'

            self.converter = await asyncio.create_subprocess_shell(command,
                                                                   stdin=asyncio.subprocess.PIPE,
                                                                   stdout=asyncio.subprocess.PIPE,
                                                                   stderr=asyncio.subprocess.DEVNULL,
                                                                   close_fds=False, shell=True)
            atexit.register(lambda: self.converter.kill())
            asyncio.create_task(self.start_streaming())

            while True:
                await asyncio.sleep(1.0 / self.stream_data.framerate)
                grabbed, frame = self.cap.read()
                if grabbed:
                    await self.do_tracking(frame)
                    self.converter.stdin.write(frame.tostring())
                    await self.converter.stdin.drain()

        except Exception as inst:
            print(type(inst))  # the exception instance
            print(inst.args)  # arguments stored in .args
            print(inst)

    async def start_streaming(self):
        print('Starting streaming')
        closed_sockets = set()

        try:
            while True:
                buf = await self.converter.stdout.read(STREAM_BLOCKSIZE)
                if buf:
                    for client_id, ws in self.stream_clients.items():
                        try:
                            await ws.send(buf)
                        except:
                            print('Removing stream socket from rover')
                            closed_sockets.add(client_id)

                for client_id in closed_sockets:
                    try:
                        del self.stream_clients[client_id]
                    except:
                        pass

                closed_sockets.clear()
        finally:
            self.converter.stdout.close()

    async def process_server_command(self, message):
        print(f'Received server command')
        await self.server_commands[message['cmd']](message)

    async def forward_client_cmds(self, client_id):
        ws = self.rover_clients[client_id]
        print(f'Forwarding commands from Client: {client_id}, ws: {ws}')

        try:
            async for message in ws:
                print(repr(message))
                msg = json.loads(message)

                self.reset_distance()
                self.reset_area()

                if msg['cmd'] in self.server_commands:
                    asyncio.create_task(self.process_server_command(msg))
                    await send_websocket_message({'msg': 'ok'}, ws)
                    continue

                self.writer.write(message.encode())
                await self.writer.drain()
                await send_websocket_message({'msg': 'ok'}, ws)
            await asyncio.sleep(0.001)

        except:
            print('Removing ctrl socket from rover')
            del self.rover_clients[client_id]

        try:
            print('Removing ctrl socket from rover')
            del self.rover_clients[client_id]
        except:
            pass

    def add_rover_client(self, client_id, websocket):
        print(f'Rover client {client_id} added to rover {self.rover_id}')
        self.rover_clients[client_id] = websocket
        print(self.rover_clients.items())

    def add_stream_client(self, client_id, websocket):
        print(f'Stream client {client_id} added to rover {self.rover_id}')
        self.stream_clients[client_id] = websocket


class ProxyServer(object):
    def __init__(self):
        self.id = uuid.uuid1()
        self.rover_handlers = dict()

    async def greet_rover(self, reader, writer):
        print('Rover connected')

        hello_msg = await reader.readline()
        hello_cmd = json.loads(hello_msg.decode())

        print(hello_msg)

        self.rover_handlers[hello_cmd['rover_id']] = RoverHandler(hello_cmd, shared_cv_helper, reader, writer)

        stream_set_msg = await reader.readline()
        stream_set_cmd = json.loads(stream_set_msg.decode())
        print(stream_set_cmd)

        with open(f'{hello_cmd["rover_id"]}.sdp', 'w') as f:
            f.write(stream_set_cmd['conf'])

        self.rover_handlers[hello_cmd['rover_id']].start_capture()

        await self.rover_handlers[hello_cmd['rover_id']].start_conversion()

    async def greet_rover_client(self, websocket, path):
        print(f'Rover Client connected!')

        hello_msg = await websocket.recv()
        print(hello_msg)

        # hello_cmd = json.loads(hello_msg)

        hello_response = {'server_id': str(self.id), 'msg': 'ack'}

        await send_websocket_message(hello_response, websocket)

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

        await send_websocket_message(connect_response, websocket)

        await self.rover_handlers[connect_cmd['rover_id']].forward_client_cmds(connect_cmd['client_id'])
        await websocket.wait_closed()
        print('Rover client disconnected')

    async def do_list_command(self, websocket):
        rovers_list = list(
            map(lambda r: {'rover_id': r.rover_id, 'rover_data': r.rover_data}, self.rover_handlers.values()))

        list_response = {'server_id': str(self.id), 'rovers': rovers_list}

        await send_websocket_message(list_response, websocket)

    async def greet_stream_client(self, websocket, path):
        print(f'Stream Client connected!')

        connect_msg = await websocket.recv()
        connect_cmd = json.loads(connect_msg)

        connect_response = {'server_id': str(self.id), 'client_id': connect_cmd['client_id'],
                            'rover_id': connect_cmd['rover_id'], 'msg': 'ok'}

        await send_websocket_message(connect_response, websocket)
        start_msg = await websocket.recv()

        print(start_msg)

        rover = self.rover_handlers[connect_cmd['rover_id']]

        await websocket.send(
            rover.stream_data.jsmpeg_header.pack(rover.stream_data.jsmpeg_magic, rover.stream_data.width,
                                                 rover.stream_data.height))

        self.rover_handlers[connect_cmd['rover_id']].add_stream_client(connect_cmd['client_id'], websocket)

        await websocket.wait_closed()
        print('Stream client disconnected')

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

    async def start_all(self):
        await asyncio.gather(await self.serve_rovers(),
                             await self.server_rover_clients(),
                             await self.serve_stream_clients())


# Send the message, given as dictionary, to the socket, encoded as json
async def send_socket_message(message, writer):
    try:
        encoded_msg = json.dumps(message) + '\n'
        writer.write(encoded_msg.encode())
        await writer.drain()
    except Exception as e:
        print(e)


# Send the message, given as dictionary, to the socket, encoded as json
async def send_websocket_message(message, websocket):
    try:
        encoded_msg = json.dumps(message) + '\n'
        await websocket.send(encoded_msg)
    except Exception as e:
        print(e)


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
