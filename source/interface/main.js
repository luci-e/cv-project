'use strict';

import * as RL from './RoverLibs.js';


var PORT = 8888;
var SOCKET_ADDR = 'ws://192.168.1.65:'+PORT;
var CONNECTION_METHOD = '';



var keys = new RL.CommandHandler("commands-container");
var rover = new RL.RoverHandler("SHA", keys, SOCKET_ADDR);
//var rover = new RL.RoverHandler("SHA2", keys, SOCKET_ADDR);

rover.connectToServer();
//connection.sendTestMessage();