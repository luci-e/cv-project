'use strict';



export default class CommandHandler {

	constructor(keyDiv) {

		this.up = document.querySelector("#"+keyDiv+" #forward");
		this.left = document.querySelector("#"+keyDiv+" #left");
		this.right = document.querySelector("#"+keyDiv+" #right");
		this.down = document.querySelector("#"+keyDiv+" #backward");

		this.cameraUp = document.querySelector("#"+keyDiv+" #cameraUp");
		this.cameraDown = document.querySelector("#"+keyDiv+" #cameraDown");

		this.rover = null;

		this.pressed = new Array(256);
		for(var i=0; i<256; i++)
			this.pressed[i] = false;

	};


	bind(rover) {

		this.rover = rover;

		var that = this;

		this.up.onmousedown = function() {
			return rover.repeatAction(rover.forward, 750);
		}
		this.up.onmouseout = function() {
			return rover.stopAction();
		}

		this.up.ontouchstart = function() {
			that.up.onmouseout = function() {return false;};
			that.up.onmousedown = function() {return false;};
			return rover.repeatAction(rover.forward, 750);
		}
		this.up.ontouchend = function() {
			return rover.stopAction();
		}


		this.down.onmousedown = function() {
			return rover.repeatAction(rover.backward, 750);
		}
		this.down.onmouseout = function() {
			return rover.stopAction();
		}


		this.down.ontouchstart = function() {
			that.down.onmouseout = function() {return false;};
			that.down.onmousedown = function() {return false;};
			return rover.repeatAction(rover.backward, 750);
		}
		this.down.ontouchend = function() {
			return rover.stopAction();
		}


		this.left.onmousedown = function() {
			return rover.repeatAction(rover.left, 750);
		}
		this.left.onmouseout = function() {
			return rover.stopAction();
		}

		this.left.ontouchstart = function() {
			that.left.onmouseout = function() {return false;};
			that.left.onmousedown = function() {return false;};
			return rover.repeatAction(rover.left, 750);
		}
		this.left.ontouchend = function() {
			return rover.stopAction();
		}

		this.right.onmousedown = function() {
			return rover.repeatAction(rover.right, 750);
		}
		this.right.onmouseout = function() {
			return rover.stopAction();
		}
		this.right.ontouchstart = function() {
			that.right.onmouseout = function() {return false;};
			that.right.onmousedown = function() {return false;};
			return rover.repeatAction(rover.right, 750);
		}
		this.right.ontouchend = function() {
			return rover.stopAction();
		}


		this.cameraDown.onmousedown = function() {
			return rover.cameraUp();
		}

		document.body.onmouseup = function() {
			return rover.stopAction();

		}
		document.body.ontouchend = function() {
			return rover.stopAction();

		}

		document.body.onkeydown = function(e) {
			that.handleKeyPress(e);
		}

		document.body.onkeyup = function(e) {
			that.handleKeyRelease(e);
		}

		//document.body.onmouseout = function() {
		//	console.log("HELLO THERE");
		//	return rover.stopActionUp();
		//}


	}

	handleKeyPress(e) {
		
		//don't event check switch if key is already pressed
		if(!this.pressed[e.keyCode]) {

			console.log("HELLO THERE");

				switch(e.key) {
					case "w":
						this.rover.repeatAction(this.rover.forward, 750);
						break;

					case "a":
						this.rover.repeatAction(this.rover.left, 750);
						break;

					case "s":
						this.rover.repeatAction(this.rover.right, 750);
						break;

					case "d":
						this.rover.repeatAction(this.rover.backward, 750);
						break;
				}

				this.pressed[e.keyCode] = true;

		}

	}

	handleKeyRelease(e) {

		this.pressed[e.keyCode] = false;
		this.rover.stopAction();

	}




}