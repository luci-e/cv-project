'use strict';

export default class ConnectionHandler {
	constructor(serverAddress, connectionMethod) {
		this.serverAddress = serverAddress;
		this.connectionMethod = connectionMethod;
		this.rovers = [];
		this.socket;
		this.lastMsg;
	}

	connectToServer() {
		if(this.connectionMethod)
			this.socket = new WebSocket(this.serverAddress, [this.connectionMethod]);
		else
			this.socket = new WebSocket(this.serverAddress);




		var that = this;
		this.socket.onmessage = this.handleAnswer;

		this.socket.onopen = function(event) {
			console.log("Succesfully connected to remove server!");
			that.sendMoveForward();
		}

		this.socket.onmessage = function (answer) {
			that.handleAnswer(answer);
		}

		this.socket.onclose = function(event) {
			console.log("Connection to remote server closed!")
		}

		this.socket.onerror = function(event) {
			console.log("Unexpected error while trying to connect! Sheer Heart Attack may have already exploded!");
		}

	}

	getSocket() {
		return this.socket;
	}


	handleAnswer(answer) {

		//console.log(answer.data);

		answer = JSON.parse(answer.data);

		if(this.lastMsg) {
			switch(this.lastMsg.cmd) {
				case "move":

						if(answer.msg == "ok")
							console.log("SHA moved forward!");

						else if(answer.msg == "failed")
							console.log("SHA exploded")

					break;
				

			}
		}
		else {
			console.log("Received an unexpected message:");
			console.log(answer);
		}
	}

	sendMsg(msg) {
		return this.getSocket().send(JSON.stringify(msg));
	}

	sendMoveForward() {

		var msg = {
			cmd: "move",
			params: {
				direction: ["forward", "right"]
			}
		}

		this.lastMsg = msg;

		this.sendMsg(msg);
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
