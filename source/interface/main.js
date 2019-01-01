'use strict';

import * as RL from './RoverLibs.js';


var PORT = 80;
var SOCKET_ADDR = 'ws://127.0.0.1:'+PORT;
var CONNECTION_METHOD = '';


var connection = new RL.ConnectionHandler(SOCKET_ADDR);

connection.connectToServer();
//connection.sendTestMessage();