'use strict';

export default class ConnectionHandler {
	constructor(serverAddress, connectionMethod) {
		this.serverAddress = serverAddress;
		this.connectionMethod = connectionMethod;
		this.rovers = [];
		this.socket;
	}

	connectToServer() {
		if(this.connectionMethod)
			this.socket = new WebSocket(this.serverAddress, [this.connectionMethod]);
		else
			this.socket = new WebSocket(this.serverAddress);




		var that = this;
		this.socket.onmessage = function(event) {
			that.handleAnswer(event);
		}

		this.socket.onopen = function(event) {
			console.log("Succesfully connected to remove server!");
			that.sendTestMessage();
		}

		this.socket.onclose = function(event) {
			console.log("Connection to remote server closed!")
		}

		this.socket.onerror = function(event) {
			console.log("Unexpected error while trying to connect! Sheer Heart Attack may have already exploded!");
		}



        setTimeout(function() {
        	console.log(that.getSocket().readyState);
        }, 5);

		console.log(this.socket);
	}

	getSocket() {
		return this.socket;
	}


	handleAnswer(message) {
		console.log("Received message from server: "+message)
	}

	sendTestMessage() {
		var msg = {
			text: "KOCCHI WO MIRO!",
			cmd: "attack"
		};


		console.log(this.getSocket());
		this.getSocket().send(JSON.stringify(msg));

		console.log("Test Message sent to server!");
	}
}


var player = new JSMpeg.Player();