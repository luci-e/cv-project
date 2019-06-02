'use strict';


//Misc vars for arrowKeys sprite

const ARROW_CONTAINER_SIZE = 241;

const IDLE_ID = 0;
const UP_ID = 3;
const LEFT_ID = 1;
const RIGHT_ID = 2;
const DOWN_ID = 4;
const CCW_ID = 5;
const CW_ID = 6;


const CIDLE_ID = 0;
const CDOWN_ID = 1;
const CUP_ID = 2;


export default class CommandHandler {

    constructor(keyDiv) {

        this.up = document.querySelector("#" + keyDiv + " #forward");
        this.left = document.querySelector("#" + keyDiv + " #left");
        this.right = document.querySelector("#" + keyDiv + " #right");
        this.down = document.querySelector("#" + keyDiv + " #backward");

        this.ccw = document.querySelector("#" + keyDiv + " #ccw");
        this.cw = document.querySelector("#" + keyDiv + " #cw");

        this.arrowContainer = document.querySelector("#" + keyDiv + " #arrowkeys");
        this.cameraKeysContainer = document.querySelector("#" + keyDiv + " #cameraControls");

        this.cameraUp = document.querySelector("#" + keyDiv + " #cameraUp");
        this.cameraDown = document.querySelector("#" + keyDiv + " #cameraDown");

        this.rover = null;

        this.pressed = new Array(256);
        for (let i = 0; i < 256; i++)
            this.pressed[i] = false;

    };


    bind(rover) {

        this.rover = rover;

        var that = this;


        //FORWARD
        this.bindStartFunction(this.up, function () {
            that.setButtonDisplay(UP_ID);
            return rover.forward();
        });

        this.bindEndFunction(this.up, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });


        //BACKWARD
        this.bindStartFunction(this.down, function () {
            that.setButtonDisplay(DOWN_ID);
            return rover.backward();
        });

        this.bindEndFunction(this.down, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });


        //LEFT
        this.bindStartFunction(this.left, function () {
            that.setButtonDisplay(LEFT_ID);
            return rover.left();
        });

        this.bindEndFunction(this.left, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });


        //RIGHT
        this.bindStartFunction(this.right, function () {
            that.setButtonDisplay(RIGHT_ID);
            return rover.right();
        });

        this.bindEndFunction(this.right, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });


        //CWISE
        this.bindStartFunction(this.cw, function () {
            that.setButtonDisplay(CW_ID);
            return rover.cw();
        });

        this.bindEndFunction(this.cw, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });

        //CCWISE
        this.bindStartFunction(this.ccw, function () {
            that.setButtonDisplay(CCW_ID);
            return rover.ccw();
        });

        this.bindEndFunction(this.ccw, function () {
            that.setButtonDisplay(IDLE_ID);
            return rover.stopAction();
        });

        //CAMERA UP
        this.bindStartFunction(this.cameraUp, function () {
            that.setCameraButtonDisplay(CUP_ID);
            return rover.laserOn();
        });

        this.bindEndFunction(this.cameraUp, function () {
            that.setCameraButtonDisplay(CIDLE_ID);
            return rover.laserOff();
        });


        //CAMERA DOWN
        this.bindStartFunction(this.cameraDown, function () {
            that.setCameraButtonDisplay(CDOWN_ID);
            return rover.cameraDown();
        });

        this.bindEndFunction(this.cameraDown, function () {
            that.setCameraButtonDisplay(CIDLE_ID);
            return rover.stopCamera();
        });


        document.body.onkeydown = function (e) {
            that.handleKeyPress(e);
        };

        document.body.onkeyup = function (e) {

            that.handleKeyRelease(e);
            that.updateKeyDisplay();
        }

        //document.body.onmouseout = function() {
        //	console.log("HELLO THERE");
        //	return rover.stopActionUp();
        //}


    }

    handleKeyPress(e) {

        //don't event check switch if key is already pressed
        if (!this.pressed[e.keyCode]) {

            console.log("HELLO THERE");

            switch (e.key) {
                case "w":
                    this.setButtonDisplay(UP_ID);
                    this.rover.forward();
                    break;

                case "a":
                    this.setButtonDisplay(LEFT_ID);
                    this.rover.repeatAction(this.rover.left, 750);
                    break;

                case "s":
                    this.setButtonDisplay(DOWN_ID);
                    this.rover.repeatAction(this.rover.backward, 750);
                    break;

                case "d":
                    this.setButtonDisplay(RIGHT_ID);
                    this.rover.repeatAction(this.rover.right, 750);
                    break;
            }

            this.pressed[e.keyCode] = true;

        }

    }

    updateKeyDisplay() {

    }

    handleKeyRelease(e) {

        this.pressed[e.keyCode] = false;
        this.rover.stopAction();

    }


    setButtonDisplay(id) {

        var xOffset = -ARROW_CONTAINER_SIZE * id;

        this.arrowContainer.style.backgroundPosition = xOffset + "px 0px";
    }


    setCameraButtonDisplay(id) {
        var xOffset = -ARROW_CONTAINER_SIZE * id;

        this.cameraKeysContainer.style.backgroundPosition = xOffset + "px 0px";
    }


    bindStartFunction(button, action) {

        button.onmousedown = function () {
            return action();
        };
        button.ontouchstart = function () {
            button.onmouseout = function () {
                return false;
            };
            button.onmousedown = function () {
                return false;
            };
            return action();
        };

    }

    bindEndFunction(button, action) {
        var rover = this.rover;

        button.onmouseout = function () {
            return action();
        };
        button.onmouseup = function () {
            return action();
        };
        button.ontouchend = function () {
            return action();
        };

    }

}


/*this.up.ontouchstart = function() {
	that.setButtonDisplay(UP_ID);
	that.up.onmouseout = function() {return false;};
	that.up.onmousedown = function() {return false;};
	return rover.repeatAction(rover.forward, 750);
}*/