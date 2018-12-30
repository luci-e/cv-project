'use strict';

import RoverHandler from './RoverHandler.js'

export default class ConnectionHandler {
	constructor(serverAddress, connectionMethod) {
		this.serverAddress = serverAddress;
		this.connectionMethod = connectionMethod;
		this.rovers = [];
		this.socket;
	}

	addRover(roverHandler) {

		console.log("Rover: \""+roverHandler.getIdentifier()+"\" added.");

		this.rovers.push(roverHandler);
	}


	connectToServer() {
		this.socket = new WebSocket(this.serverAddress, [this.connectionMethod]);
	}

	getSocket() {
		return this.getSocket;
	}


	sendTestMessage() {
		var msg = {
			text: "KOCCHI WO MIRO!"
		};

		getSocket().emit('sendMessage', msg);
	}
}