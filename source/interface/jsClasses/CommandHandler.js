'use strict';

//Misc vars for arrowKeys sprite
import * as consts from './Constants.js';

const ARROW_CONTAINER_SIZE = 241;

const IDLE_ID = 0;
const UP_ID = 3;
const LEFT_ID = 1;
const RIGHT_ID = 2;
const DOWN_ID = 4;
const FORWARD_LEFT_ID = 5;
const FORWARD_RIGHT_ID = 6;
const BACKWARD_LEFT_ID = 7;
const BACKWARD_RIGHT_ID = 8;



export default class CommandHandler {

    constructor(keyDiv) {

        this.key_mappings_movement = {
            'w' : consts.ROVER_DIRECTION.FORWARD,
            'a' : consts.ROVER_DIRECTION.LEFT,
            's' : consts.ROVER_DIRECTION.BACK,
            'd' : consts.ROVER_DIRECTION.RIGHT
        };

        this.key_mappings_camera = {
            'r' : consts.CAM_DIRECTION.UP,
            'f' : consts.CAM_DIRECTION.DOWN,
            'q' : consts.CAM_DIRECTION.CCW,
            'e' : consts.CAM_DIRECTION.CW,
            'x' : consts.CAM_DIRECTION.CLR
        };


        // These needs to be mapped to the correct offset for the image
        this.movement_display_mappings = {
            [consts.ROVER_DIRECTION.STOP] : IDLE_ID,
            [consts.ROVER_DIRECTION.FORWARD] : UP_ID,
            [consts.ROVER_DIRECTION.BACK] : DOWN_ID,
            [consts.ROVER_DIRECTION.LEFT] : LEFT_ID,
            [consts.ROVER_DIRECTION.RIGHT] : RIGHT_ID,
            [consts.ROVER_DIRECTION.CW] : RIGHT_ID,
            [consts.ROVER_DIRECTION.CCW] : LEFT_ID,
            [consts.ROVER_DIRECTION.FORWARD | consts.ROVER_DIRECTION.LEFT]  : FORWARD_LEFT_ID,
            [consts.ROVER_DIRECTION.FORWARD | consts.ROVER_DIRECTION.RIGHT] : FORWARD_RIGHT_ID,
            [consts.ROVER_DIRECTION.BACK | consts.ROVER_DIRECTION.LEFT] : BACKWARD_RIGHT_ID,
            [consts.ROVER_DIRECTION.BACK | consts.ROVER_DIRECTION.RIGHT] : BACKWARD_LEFT_ID
        };

        this.cam_display_mappings = {
            [consts.CAM_DIRECTION.STOP] : IDLE_ID,
            [consts.CAM_DIRECTION.UP] : UP_ID,
            [consts.CAM_DIRECTION.DOWN] : DOWN_ID,
            [consts.CAM_DIRECTION.CW] : RIGHT_ID,
            [consts.CAM_DIRECTION.CCW] : LEFT_ID,
            [consts.CAM_DIRECTION.UP | consts.CAM_DIRECTION.CW]  : FORWARD_RIGHT_ID,
            [consts.CAM_DIRECTION.UP | consts.CAM_DIRECTION.CCW] : FORWARD_LEFT_ID,
            [consts.CAM_DIRECTION.DOWN | consts.CAM_DIRECTION.CW] : BACKWARD_RIGHT_ID,
            [consts.CAM_DIRECTION.DOWN | consts.CAM_DIRECTION.CCW] : BACKWARD_LEFT_ID
        };


        this.arrowContainer = document.querySelector('#movementControls');
        this.cameraKeysContainer = document.querySelector('#cameraControls');


        this.movementControls = null;
        this.cameraControls = null;

        this.speedSlider = document.getElementById("speedSlider");
        this.speedTic = document.getElementById("speedTic")

        this.rover = null;
        this.lastTouched = null;
        this.lastCameraTouched = null;

        this.pressed = new Array(256);
        for (let i = 0; i < 256; i++)
            this.pressed[i] = false;

        var that = this;
        this.mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    };


    bindCommands(rover) {

        this.rover = rover;
        // We Python now boyzzzz
        let self = this;

        this.movementControls = document.querySelectorAll('#movementControls div');
        this.movementControls.forEach( function(element){
            self.bindStartFunction(element, function(){
                self.handleMovementControlBegin( element.dataset.bid );
            });

            self.bindEndFunction(element, function(){
                self.handleMovementControlEnd( element.dataset.bid );
            });

        });

        this.cameraControls = document.querySelectorAll('#cameraControls div');
        this.cameraControls.forEach( function(element){
            self.bindStartFunction(element, function(){
                self.handleCameraControlBegin( element.dataset.bid );
            });

            self.bindEndFunction(element, function(){
                self.handleCameraControlEnd( element.dataset.bid );
            });

        });

        this.speedSlider.onmousedown = function(e) {
            if(e.path[0].id != "speedTic")
                self.moveSlider(e.offsetX);
        };



        console.log(this.movementControls);
        console.log(this.cameraControls);


        //offsetWidth
        //offsetHeight
        //offsetTop
        //offsetLeft


        //keep track of the touch with the mobile!
        if (this.mobile) {
            console.log(this.movementControls);
            console.log(this.cameraControls);


            document.getElementById("movementControls").ontouchmove = function(e) {
                
                let touch = e.touches[0];
                let button = document.elementFromPoint(touch.clientX, touch.clientY)
                let bid = button.dataset.bid

                if (self.lastTouched != bid) {

                    if(self.lastTouched != null)
                        self.handleMovementControlEnd(self.lastTouched)

                    self.lastTouched = bid;
                    self.handleMovementControlBegin(bid);

                }
                
            }

            document.getElementById("wrapper").ontouchend = function(e) {

                self.handleMovementControlEnd(rover.currentDirection);
                self.lastTouched = null;

            }


            document.getElementById("cameraControls").ontouchmove = function(e) {
                
                let touch = e.touches[0];
                let button = document.elementFromPoint(touch.clientX, touch.clientY)
                let bid = button.dataset.bid

                if (self.lastCameraTouched != bid) {

                    if(self.lastCameraTouched != null)
                        self.handleCameraControlEnd(self.lastCameraTouched);

                    self.lastCameraTouched = bid;
                    self.handleCameraControlBegin(bid);

                }
                
            }

            document.getElementById("wrapper").ontouchend = function(e) {

                self.handleCameraControlEnd(rover.currentCamDirection);
                self.lastCameraTouched = null;

            }

        }


        document.body.onkeydown = this.handleKeyPress.bind(this);
        document.body.onkeyup = this.handleKeyRelease.bind(this);
    }


    handleCameraControlBegin(button) {
        if (button == consts.CAM_DIRECTION.CLR){
            this.setCameraButtonDisplay(this.cam_display_mappings[consts.CAM_DIRECTION.STOP])
            this.rover.cameraReset();
            return;
        }

        let newCamDirection = this.rover.currentCamDirection | button;
        if( consts.ALLOWED_CAM_DIRECTIONS.has(newCamDirection)){
            this.setCameraButtonDisplay(this.cam_display_mappings[newCamDirection])
            this.rover.currentCamDirection = newCamDirection;
            this.rover.updateCamMovement();
        }
    }

    handleCameraControlEnd(button) {
        if (button == consts.CAM_DIRECTION.CLR){
            return;
        }

        let newCamDirection = this.rover.currentCamDirection ^ button;
        if( consts.ALLOWED_CAM_DIRECTIONS.has(newCamDirection)){
            this.setCameraButtonDisplay(this.cam_display_mappings[newCamDirection])
            this.rover.currentCamDirection = newCamDirection;
            this.rover.updateCamMovement();
        }
    }

    handleMovementControlBegin(button) {
        let newDirection = this.rover.currentDirection | button;
        if( consts.ALLOWED_DIRECTIONS.has(newDirection)){
            this.setButtonDisplay(this.movement_display_mappings[newDirection])
            this.rover.currentDirection = newDirection;
            this.rover.updateMovement();
        }
    }

    handleMovementControlEnd(button) {
        let newDirection = this.rover.currentDirection ^ button;
        if( consts.ALLOWED_DIRECTIONS.has(newDirection)){
            this.setButtonDisplay(this.movement_display_mappings[newDirection])
            this.rover.currentDirection = newDirection;
            this.rover.updateMovement();
        }
    }

    handleKeyPress(e) {
        //don't event check switch if key is already pressed
        if (!this.pressed[e.keyCode]) {
            if( e.key in this.key_mappings_movement )
                this.handleMovementControlBegin(this.key_mappings_movement[e.key]);
            else if( e.key in this.key_mappings_camera )
                this.handleCameraControlBegin(this.key_mappings_camera[e.key]);

            this.pressed[e.keyCode] = true;
        }
    }

    handleKeyRelease(e) {
        if (this.pressed[e.keyCode]) {
            if( e.key in this.key_mappings_movement )
                this.handleMovementControlEnd(this.key_mappings_movement[e.key]);
            else if( e.key in this.key_mappings_camera )
                this.handleCameraControlEnd(this.key_mappings_camera[e.key]);

            this.pressed[e.keyCode] = false;
        }
    }


    setButtonDisplay(id) {

        var xOffset = -ARROW_CONTAINER_SIZE * id;

        this.arrowContainer.style.backgroundPosition = xOffset + "px 0px";
    }


    setCameraButtonDisplay(id) {
        var xOffset = -ARROW_CONTAINER_SIZE * id;

        this.cameraKeysContainer.style.backgroundPosition = xOffset + "px 0px";
    }


    bindStartFunction(ctrl, action) {

        if(this.mobile) {
           
            ctrl.ontouchstart = function () {
                return action();
            };

        } else {

            ctrl.onmousedown = function () {
                return action();
            };

            ctrl.onmouseover = function(event){
                if( event.button == 0 && event.buttons ){
                    return action();
                }
            };
        }


    }

    bindEndFunction(ctrl, action) {
        var rover = this.rover;

        if (this.mobile) {

            ctrl.ontouchend = function () {          
                return action();
            };

        } else {

            ctrl.onmouseup = function () {
                console.log("HELLO HERE");
                return action();
            };

            ctrl.onmouseleave = function(event){
                if( event.button == 0 && event.buttons ){
                    return action();
                }
            };
        }

    }


    moveSlider(offset) {
        //ugly stuff to get the right offset with the bars
        offset-=7;
        offset = Math.min(Math.max(offset, 30), 298);
        var value = (offset-30)/(298-30);

        this.rover.setSpeed(value);
        this.speedTic.style.left=offset+"px";
    }



    //offsetWidth
    //offsetHeight
    //offsetTop
    //offsetLeft

    /*getButtonHovered(x, y) {


        document.getElementById("cameraControls").innerHTML =  x+" "+y;

        let len = this.movementControls.length;

        for(let i=0; i<len; i++) {

            let div = this.movementControls[i];
            let minX = div.offsetLeft, minY = div.offsetTop;
            let w = div.offsetWidth, h = div.offsetHeight;


            if (( x - minX < w ) && ( y - minY < h)) {
                this.cameraControls.innerHTML =  x+" "+y+"\nHELLO GENERAL DIVOBI: "+this.movementControls[i]
            }

        }
    }*/

}

/*this.up.ontouchstart = function() {
	that.setButtonDisplay(UP_ID);
	that.up.onmouseout = function() {return false;};
	that.up.onmousedown = function() {return false;};
	return rover.repeatAction(rover.forward, 750);
}*/