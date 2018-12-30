'use strict';

import * as RL from './RoverLibs.js';

var SOCKET_ADDR = '';
var CONNECTION_METHOD = '';


var connection = new RL.ConnectionHandler(SOCKET_ADDR, CONNECTION_METHOD);
var rover1 = new RL.RoverHandler('Sheer Heart Attack');

connection.addRover(rover1);