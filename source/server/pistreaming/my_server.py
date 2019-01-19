#!/usr/bin/env python

import sys
import io
import os
import shutil
import asyncio
import websockets

from subprocess import Popen, PIPE
from string import Template
from struct import Struct
from threading import Thread
from time import sleep, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from wsgiref.simple_server import make_server

import cv2
from ws4py.websocket import WebSocket
from ws4py.server.wsgirefserver import (
    WSGIServer,
    WebSocketWSGIHandler,
    WebSocketWSGIRequestHandler,
)
from ws4py.server.wsgiutils import WebSocketWSGIApplication

###########################################
# CONFIGURATION
WIDTH = 640
HEIGHT = 480
FRAMERATE = 24
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


class StreamingWebSocket(WebSocket):
    def opened(self):
        self.send(JSMPEG_HEADER.pack(JSMPEG_MAGIC, WIDTH, HEIGHT), binary=True)


class BroadcastOutput(object):
    def __init__(self, camera):
        print('Spawning background conversion process')
        self.converter = Popen([
            'ffmpeg',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '%dx%d' % camera.resolution,
            '-r', str(float(camera.framerate)),
            '-i', '-',
            '-f', 'mpeg1video',
            '-b', '64k',
            '-r', str(float(camera.framerate)),
            '-'],
            stdin=PIPE, stdout=PIPE, stderr=io.open(os.devnull, 'wb'),
            shell=False, close_fds=True)

    def write(self, b):
        self.converter.stdin.write(b)

    def flush(self):
        print('Waiting for background conversion process to exit')
        self.converter.stdin.close()
        self.converter.wait()


class BroadcastThread(Thread):
    def __init__(self, converter, websocket_server):
        super(BroadcastThread, self).__init__()
        self.converter = converter
        self.websocket_server = websocket_server

    def run(self):
        try:
            while True:
                buf = self.converter.stdout.read1(32768)
                if buf:
                    self.websocket_server.manager.broadcast(buf, binary=True)
                elif self.converter.poll() is not None:
                    break
        finally:
            self.converter.stdout.close()


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
            sleep(1/FRAMERATE)
            # Capture frame-by-frame
            ret, frame = self.cap.read()
            # Our operations on the frame come here
            self.output.write(frame.tostring())
            
    def run(self):
        self.start_recording()
        


def main():
    print('Initializing camera')
    
    camera = USBCamera( int( sys.argv[1] ) )
    print('Initializing websockets server on port %d' % WS_PORT)
    WebSocketWSGIHandler.http_version = '1.1'
    websocket_server = make_server(
        '', WS_PORT,
        server_class=WSGIServer,
        handler_class=WebSocketWSGIRequestHandler,
        app=WebSocketWSGIApplication(handler_cls=StreamingWebSocket))
    websocket_server.initialize_websockets_manager()
    websocket_thread = Thread(target=websocket_server.serve_forever)
    print('Initializing HTTP server on port %d' % HTTP_PORT)
    http_server = StreamingHttpServer()
    http_thread = Thread(target=http_server.serve_forever)
    print('Initializing broadcast thread')
    output = BroadcastOutput(camera)
    broadcast_thread = BroadcastThread(output.converter, websocket_server)
    
    camera.output = output
    print('Starting recording')
    try:
        camera.start()
        print('Starting websockets thread')
        websocket_thread.start()
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
        print('Shutting down websockets server')
        websocket_server.shutdown()
        print('Waiting for HTTP server thread to finish')
        http_thread.join()
        print('Waiting for websockets thread to finish')
        websocket_thread.join()


if __name__ == '__main__':
    main()
