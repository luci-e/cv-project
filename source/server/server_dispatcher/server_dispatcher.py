import http.server
import socketserver
import pdb
import os 
import json
import time
import sys
import argparse

from threading import Thread

PORT = 80
BASE_DIR = ''

class shal_request_handler( http.server.SimpleHTTPRequestHandler ):
	def __init__( self, request, client_address, server):
	    super(shal_request_handler, self).__init__( request, client_address, server )
	    #TODO : add code to send initial json list


class HTTP_server_thread(Thread):    
    def __init__(self):
        Thread.__init__(self)
        self.done = False

    def stop(self):
        self.done = True

    def run(self):
        print('HTTP Server started')
        with socketserver.TCPServer(("", PORT), shal_request_handler) as httpd:
            print( f'serving at port {PORT} at base dir {BASE_DIR}' )
            httpd.serve_forever()

def main():
	global PORT, BASE_DIR

	# Standard argument parsing
	parser = argparse.ArgumentParser( description = 'Start the dispatcher')
	parser.add_argument('-p', '--port' , default = 80, type = int , help = 'The port on which to open the server')
	parser.add_argument('-b', '--base_dir' , default = '../../interface', help = 'The base directory of the server')
	args = parser.parse_args()

	BASE_DIR = args.base_dir
	PORT = args.port

	# Move script to http folder
	os.chdir(BASE_DIR)

	# Start server
	http_thread = HTTP_server_thread()
	http_thread.start()

if __name__ == '__main__':
    main()
