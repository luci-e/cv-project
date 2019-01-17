'use strict';

export default class CommandHandler {

	constructor(keyDiv) {

		this.up = document.querySelector("#"+keyDiv+" #up");
		this.left = document.querySelector("#"+keyDiv+" #left");
		this.right = document.querySelector("#"+keyDiv+" #right");
		this.down = document.querySelector("#"+keyDiv+" #down");


	};


	bind(rover) {

		this.up.onclick = function() {
			return rover.up();
		}
		this.down.onclick = function() {
			return rover.down();
		}
		this.left.onclick = function() {
			return rover.left();
		}
		this.right.onclick = function() {
			return rover.right();
		}

	}




}