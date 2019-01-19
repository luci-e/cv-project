'use strict';

export default class CommandHandler {

	constructor(keyDiv) {

		this.up = document.querySelector("#"+keyDiv+" #forward");
		this.left = document.querySelector("#"+keyDiv+" #left");
		this.right = document.querySelector("#"+keyDiv+" #right");
		this.down = document.querySelector("#"+keyDiv+" #backward");


	};


	bind(rover) {

		var that = this;

		this.up.onmousedown = function() {
			return rover.performAction(rover.forward, 750);
		}
		this.up.onmouseout = function() {
			return rover.stopAction();
		}

		this.up.ontouchstart = function() {
			that.up.onmouseout = function() {return false;};
			that.up.onmousedown = function() {return false;};
			return rover.performAction(rover.forward, 750);
		}
		this.up.ontouchend = function() {
			return rover.stopAction();
		}


		this.down.onmousedown = function() {
			return rover.performAction(rover.backward, 750);
		}
		this.down.onmouseout = function() {
			return rover.stopAction();
		}


		this.down.ontouchstart = function() {
			that.down.onmouseout = function() {return false;};
			that.down.onmousedown = function() {return false;};
			return rover.performAction(rover.backward, 750);
		}
		this.down.ontouchend = function() {
			return rover.stopAction();
		}


		this.left.onmousedown = function() {
			return rover.performAction(rover.left, 750);
		}
		this.left.onmouseout = function() {
			return rover.stopAction();
		}

		this.left.ontouchstart = function() {
			that.left.onmouseout = function() {return false;};
			that.left.onmousedown = function() {return false;};
			return rover.performAction(rover.left, 750);
		}
		this.left.ontouchend = function() {
			return rover.stopAction();
		}

		this.right.onmousedown = function() {
			return rover.performAction(rover.right, 750);
		}
		this.right.onmouseout = function() {
			return rover.stopAction();
		}
		this.right.ontouchstart = function() {
			that.right.onmouseout = function() {return false;};
			that.right.onmousedown = function() {return false;};
			return rover.performAction(rover.right, 750);
		}
		this.right.ontouchend = function() {
			return rover.stopAction();
		}

		document.body.onmouseup = function() {
			return rover.stopAction();

		}
		document.body.ontouchend = function() {
			return rover.stopAction();

		}
		//document.body.onmouseout = function() {
		//	console.log("HELLO THERE");
		//	return rover.stopActionUp();
		//}


	}




}