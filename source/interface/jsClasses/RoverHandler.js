'use strict';

export default class RoverHandler {
	constructor(id, bindings, serverAddress, connectionMethod, createTab) {
		this.serverAddress = serverAddress;
		this.connectionMethod = connectionMethod;
		this.rovers = [];
		this.socket;
		this.lastMsg;
		this.id= id;
		this.commandHandler = bindings;

		this.getCommandHandler().bind(this);

		if(createTab != false)
				this.addToWindow();
	}

	addToWindow() {

		var that = this;

		var tab = document.createElement("div");
		tab.className="tab-element";

		tab.onclick=function() {
			that.foreground();
		}

		tab.appendChild(document.createTextNode(this.getId()));


		document.getElementById("tabs").appendChild(tab);

	}

	foreground() {

		console.log("Switching to rover: "+this.getId());

		var videoWindow = document.getElementById("video-container");
		var listWindow  = document.getElementById("list-container");

		//DO STUFF with the windows

		this.getCommandHandler().bind(this);
	}

	getCommandHandler() {
		return this.commandHandler;
	}

	getId() {
		return this.id;
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

		try {
				this.getSocket().send(JSON.stringify(msg));
		}
		catch(e) {
			console.log("\t-> Could not send message, still not connected!");
		}
	}

	up() {

		console.log(this.getId()+": Sending move forward message");

		var msg = {
			cmd: "move",
			params: {
				direction: ["forward"]
			}
		}

		this.lastMsg = msg;

		this.sendMsg(msg);

	}

	right() {

		console.log(this.getId()+": Sending move right message");

		var msg = {
			cmd: "move",
			params: {
				direction: ["right"]
			}
		}

		this.lastMsg = msg;

		this.sendMsg(msg);
	}

	left() {

		console.log(this.getId()+": Sending move left message");

		var msg = {
			cmd: "move",
			params: {
				direction: ["left"]
			}
		}

		this.lastMsg = msg;

		this.sendMsg(msg);
	}
	
	down() {

	}

	handleAnswer(message) {
		console.log("Received message from server: "+message.data);
	}


	sendTestMessage() {
		var msg = {
			text: "KOCCHI WO MIRO!",
			cmd: "ciccia"
		};


		console.log(this.getSocket());
		this.getSocket().send(JSON.stringify(msg));

		console.log("Test Message sent to server!");
	}
}
