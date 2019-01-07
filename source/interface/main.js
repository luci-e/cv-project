'use strict';

import * as RL from './RoverLibs.js';


var PORT = 8888;
var SOCKET_ADDR = 'ws://192.168.0.25:'+PORT;
var CONNECTION_METHOD = '';

document.body.requestFullscreen();

var connection = new RL.ConnectionHandler(SOCKET_ADDR);

connection.connectToServer();
//connection.sendTestMessage();