import sys
import io
import time
import asyncio

from subprocess import Popen, PIPE, DEVNULL
from string import Template
from struct import Struct
from threading import Thread
from time import sleep, time
from http.server import HTTPServer, BaseHTTPRequestHandler

import cv2
import websockets

###########################################
# CONFIGURATION
WIDTH = 640
HEIGHT = 480
FRAMERATE = 30
HTTP_PORT = 8082
WS_PORT = 8084
COLOR = u'#444'
BGCOLOR = u'#333'
JSMPEG_MAGIC = b'jsmp'
JSMPEG_HEADER = Struct('>4sHH')
VFLIP = False
HFLIP = False

###########################################


class StreamingHttpHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
            return
        elif self.path == '/jsmpg.js':
            content_type = 'application/javascript'
            content = self.server.jsmpg_content
        elif self.path == '/index.html':
            content_type = 'text/html; charset=utf-8'
            tpl = Template(self.server.index_template)
            content = tpl.safe_substitute(dict(
                WS_PORT=WS_PORT, WIDTH=WIDTH, HEIGHT=HEIGHT, COLOR=COLOR,
                BGCOLOR=BGCOLOR))
        else:
            self.send_error(404, 'File not found')
            return
        content = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(content))
        self.send_header('Last-Modified', self.date_time_string(time()))
        self.end_headers()
        if self.command == 'GET':
            self.wfile.write(content)


class StreamingHttpServer(HTTPServer):
    def __init__(self):
        super(StreamingHttpServer, self).__init__(
                ('', HTTP_PORT), StreamingHttpHandler)
        with io.open('index.html', 'r') as f:
            self.index_template = f.read()
        with io.open('jsmpg.js', 'r') as f:
            self.jsmpg_content = f.read()


class BroadcastOutput(object):
    def __init__(self, camera):
        print('Spawning background conversion process')
        try:
            self.converter = Popen([
                'ffmpeg',
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-r', f'{camera.framerate}',
                '-s', f' {int(camera.resolution[0])}x{int(camera.resolution[1])}',
                '-i', '-',
                '-maxrate', '1024k',
                '-bufsize', '2048k',
                '-r', '30',
                '-f', 'mpeg1video',
                '-'],
                stdin=PIPE, stdout=PIPE, close_fds=False,
                shell=False)

        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)              

    def write(self, b):
        self.converter.stdin.write(b)

    def flush(self):
        print('Waiting for background conversion process to exit')
        self.converter.stdin.close()
        self.converter.wait()


class BroadcastThread(Thread):
    def __init__(self, converter ):
        super(BroadcastThread, self).__init__()
        self.converter = converter
        self.connected = set()

    def stop(self):
        self.done = True

    async def greet(self, websocket, path):
        # Register.
        self.connected.add(websocket)
        try:
            await websocket.send(JSMPEG_HEADER.pack(JSMPEG_MAGIC, WIDTH, HEIGHT))
            while True:
                await asyncio.sleep(10)
        finally:
            # Unregister.
            print('Goodbye socket')
            self.connected.remove(websocket)

    async def broadcast(self):
        try:
            while True:
                await asyncio.sleep(1.0/30.0)
                buf = self.converter.stdout.read1(32768)
                if buf:
                    for ws in self.connected:
                        try:
                            await ws.send(buf)
                        except:
                            pass
                elif self.converter.poll() is not None:
                    break
        finally:
            self.converter.stdout.close()

    def run(self):
        # Create a new event loop for asyncio, start serving by creating a
        # new request handler for each new connection
        asyncio.set_event_loop(asyncio.new_event_loop())

        conn = websockets.serve(self.greet, 'localhost', WS_PORT)

        asyncio.get_event_loop().run_until_complete(conn)
        asyncio.get_event_loop().create_task(self.broadcast())
        asyncio.get_event_loop().run_forever()


class USBCamera(Thread):
    def __init__(self, camera_no ):
        super(USBCamera, self).__init__()
        self.cam_no = camera_no
        self.cap = cv2.VideoCapture( self.cam_no )
        self.resolution = ( self.cap.get( cv2.CAP_PROP_FRAME_WIDTH ) , self.cap.get( cv2.CAP_PROP_FRAME_HEIGHT ) )
        self.framerate = self.cap.get( cv2.CAP_PROP_FPS )
        self.vflip = VFLIP
        self.hflip = HFLIP
        
        self.output = None
    
    def start_recording( self ):
        while True:
            # Capture frame-by-frame
            ret, frame = self.cap.read()
            # Our operations on the frame come here
            self.output.write(frame.tostring())
            
    def run(self):
        self.start_recording()

    def list_cameras(self):
        index = 0
        arr = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                arr.append(index)
            cap.release()
            index += 1
        return arr


def main():
    print('Initializing camera')
    
    camera = USBCamera( int( sys.argv[1] ) )

    print('Initializing websockets server on port %d' % WS_PORT)


    print('Initializing HTTP server on port %d' % HTTP_PORT)
    http_server = StreamingHttpServer()
    http_thread = Thread(target=http_server.serve_forever)

    print('Initializing broadcast thread')
    output = BroadcastOutput(camera)
    broadcast_thread = BroadcastThread(output.converter)
    
    camera.output = output
    try:
        print('Starting recording')
        camera.start()
        print('Starting HTTP server thread')
        http_thread.start()
        print('Starting broadcast thread')
        broadcast_thread.start()
    except KeyboardInterrupt:
        pass
    finally:
        print('Waiting for broadcast thread to finish')
        broadcast_thread.join()
        print('Shutting down HTTP server')
        http_server.shutdown()
        print('Waiting for HTTP server thread to finish')
        http_thread.join()


if __name__ == '__main__':
    main()
