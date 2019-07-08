'use strict';
import uuid4 from '../libs/uuid.js';
import * as consts from './Constants.js';


const LINE_COLOR = "rgba(48,219,225,0.7)";
const LINE_WIDTH = 10;

export default class RoverHandler {
    constructor(name, bindings, serverAddress, commandPort, streamingPort, createTab) {
        this.serverAddress = serverAddress;
        this.commandPort = commandPort;
        this.streamingPort = streamingPort;

        this.rovers = [];
        this.currentRoverId = null;
        this.roverData = null;

        this.cmd_socket = null;
        this.stream_socket = null;
        this.player = null;

        this.lastCtrlMsg = null;

        this.id = uuid4();
        this.name = name;
        this.commandHandler = bindings;

        // Show loading notice
        this.canvas = document.getElementById('videoOutput');
        this.ctx = this.canvas.getContext("2d");

        this.currentDirection = consts.ROVER_DIRECTION.STOP;
        this.currentCamDirection = consts.CAM_DIRECTION.STOP;

        if (createTab !== false) {
            this.addToWindow();
        }

        this.overlay_canvas = document.getElementById('overlayCanvas');
        this.overlay_ctx = this.overlay_canvas.getContext("2d");

        this.flag = false;
        this.prevX = 0;
        this.currX = 0;
        this.prevY = 0;
        this.currY = 0;

        this.roi = {x: 0, y: 0, w: 0, h: 0};

        this.w = this.overlay_canvas.width;
        this.h = this.overlay_canvas.height;

        this.trackStatusChangeCb = null;
        this.tracking_status = consts.TRACKING_STATUS.STOP;
        this.follow_status = consts.FOLLOW_STATUS.STOP;

        this.initOverlayCanvas();

        this.laser_status = consts.LASER_STATUS.OFF;
        this.light_status = consts.LIGHT_STATUS.OFF;
        this.light_intensity = 125;

        this.commandHandler.bindCommands(this);

        //this.drawCrosshHair();

    }

    addToWindow() {

        var that = this;

        var tab = document.createElement("div");
        tab.className = "tab-element";

        tab.onclick = function () {
            that.foreground();
        };

        tab.appendChild(document.createTextNode(this.getId()));


        document.getElementById("tabs").appendChild(tab);

    }


    foreground() {

        console.log("Switching to rover: " + this.getId());

        var videoWindow = document.getElementById("video-container");
        var listWindow = document.getElementById("list-container");

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

        if (this.connectionMethod)
            this.cmd_socket = new WebSocket(this.serverAddress + ':' + this.commandPort, [this.connectionMethod]);
        else
            this.cmd_socket = new WebSocket(this.serverAddress + ':' + this.commandPort);

        this.cmd_socket.onmessage = this.handshakeHandler.bind(this);

        this.cmd_socket.onopen = function (event) {
            console.log("Succesfully connected to remote server!");
            this.handshakeHandler(null);
        }.bind(this);

        this.cmd_socket.onclose = function (event) {
            console.log(event)
            console.log("Connection to remote server closed!")
        };

        this.cmd_socket.onerror = function (event) {
            console.log("Unexpected error while trying to connect! Sheer Heart Attack may have already exploded!");
        }
    }


    getSocket() {
        return this.cmd_socket;
    }

    handshakeHandler(answer) {
        if (answer == null) {
            let hello_msg = {
                "client_id": this.id,
                "cmd": "hello"
            };

            this.lastCtrlMsg = hello_msg;
            this.sendCtrlMsg(hello_msg);
        } else {
            let message = JSON.parse(answer.data);

            switch (this.lastCtrlMsg.cmd) {
                case "hello": {
                    console.log(message);

                    let list_cmd = {
                        "client_id": this.id,
                        "cmd": "list"
                    };

                    this.lastCtrlMsg = list_cmd;
                    this.sendCtrlMsg(list_cmd);
                    break;
                }

                case "list": {
                    console.log(message);
                    this.rovers = message['rovers'];
                    this.populateRoverList();
                    break;
                }

                case "connect": {
                    console.log(message);
                    this.cmd_socket.onmessage = this.handleAnswer.bind(this);

                    // Connect to stream

                    this.connectToStream();

                    break;
                }
            }

        }

    }

    connectToStream() {
        // Setup the WebSocket connection and start the player
        this.stream_socket = new WebSocket(this.serverAddress + ':' + this.streamingPort);
        //this.player = new jsmpeg(this.stream_socket, {canvas:this.canvas, autoplay:true});

        this.stream_socket.onopen = function (event) {
            console.log("Succesfully connected to stream server!");

            let connect_cmd = {
                "client_id": this.id,
                "rover_id": this.currentRoverId,
                "cmd": "connect"
            };

            this.sendStreamMsg(connect_cmd);

        }.bind(this);

        this.stream_socket.onmessage = this.streamHandshakeHandler.bind(this);


    }

    // The stream handshake handler only receives one message and then commits
    // not alive. This makes it a very lucky handler.
    streamHandshakeHandler(msg) {

        // Also his only role is to receive the message and log it. It doesn't even
        // do anything useful with it. Gods what a stupid handler.
        console.log(JSON.parse(msg.data));

        let start_msg = {
            "client_id": this.id,
            "rover_id": this.currentRoverId,
            "cmd": "start"
        };

        this.sendStreamMsg(start_msg);

        this.player = new jsmpeg(this.stream_socket, {canvas: this.canvas, autoplay: true});

        // Call the onopen as if nothing happened
        this.player.initSocketClient.bind(this.player)(null);
    }

    handleAnswer(answer) {

        //console.log(answer.data);

        answer = JSON.parse(answer.data);

        if (this.lastCtrlMsg) {
            switch (this.lastCtrlMsg.cmd) {
                case "move":

                    if (answer.msg === "ok")
                        console.log("SHA moved forward!");

                    else if (answer.msg === "failed")
                        console.log("SHA exploded");

                    break;
            }
        } else {
            console.log("Received an unexpected message:");
            console.log(answer);
        }
    }

    sendCtrlMsg(msg) {

        try {
            this.cmd_socket.send(JSON.stringify(msg) + '\n');
        } catch (e) {
            console.log("\t-> Could not send message, still not connected!");
        }
    }

    sendStreamMsg(msg) {

        try {
            this.stream_socket.send(JSON.stringify(msg) + '\n');
        } catch (e) {
            console.log("\t-> Could not send message, still not connected!");
        }
    }


    setSpeed(value) {

        value = value.toFixed(3);

        console.log("Request to set the speed to: " + value);

        var msg = {
            cmd: "set_speed",
            params: {
                speed: value
            }
        };

        this.sendCtrlMsg(msg);

    }

    updateMovement() {
        console.log(this.currentDirection);
        let direction = [];

        if (this.currentDirection === consts.ROVER_DIRECTION.STOP) {
            this.stopAction();
            return;
        } else {
            if (this.currentDirection & consts.ROVER_DIRECTION.FORWARD) {
                direction.push('forward')
            }
            if (this.currentDirection & consts.ROVER_DIRECTION.BACK) {
                direction.push('back')
            }
            if (this.currentDirection & consts.ROVER_DIRECTION.LEFT) {
                direction.push('left')
            }
            if (this.currentDirection & consts.ROVER_DIRECTION.RIGHT) {
                direction.push('right')
            }
            if (this.currentDirection & consts.ROVER_DIRECTION.CW) {
                direction.push('cw')
            }
            if (this.currentDirection & consts.ROVER_DIRECTION.CCW) {
                direction.push('ccw')
            }
        }

        if (direction.length === 0)
            return;

        let msg = {
            cmd: "move",
            params: {
                direction: direction
            }
        };
        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    updateCamMovement() {
        console.log(this.currentCamDirection);
        let camDirection = [];

        if (this.currentCamDirection === consts.CAM_DIRECTION.STOP) {
            this.stopCamera();
            return;
        } else {
            if (this.currentCamDirection & consts.CAM_DIRECTION.UP) {
                camDirection.push('up')
            }
            if (this.currentCamDirection & consts.CAM_DIRECTION.DOWN) {
                camDirection.push('down')
            }
            if (this.currentCamDirection & consts.CAM_DIRECTION.CW) {
                camDirection.push('cw')
            }
            if (this.currentCamDirection & consts.CAM_DIRECTION.CCW) {
                camDirection.push('ccw')
            }
        }

        if (camDirection.length === 0)
            return;

        let msg = {
            cmd: "move_cam",
            params: {
                direction: camDirection
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    stopAction() {

        var msg = {
            cmd: "move_stop",
            params: {
                motors: ["wheels"]
            }
        };
        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }


    stopCamera() {

        var msg = {
            cmd: "move_stop",
            params: {
                motors: ["camera"]
            }
        };
        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    cameraReset() {

        this.currentCamDirection = consts.CAM_DIRECTION.STOP;

        var msg = {
            cmd: "set_cam",
            params: {
                angles: [0, 0]
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);

    }

    toggleLaser() {

        let new_status = 'off';

        if( this.laser_status == consts.LASER_STATUS.OFF){
            this.laser_status = consts.LASER_STATUS.ON;
            new_status = 'on';
        }else{
            this.laser_status = consts.LASER_STATUS.OFF;
            new_status = 'off';
        }

        var msg = {
            cmd: "laser_ctrl",
            params: {
                action: new_status
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }


    toggleLight() {

        let new_status = 'off';

        if( this.light_status == consts.LIGHT_STATUS.OFF){
            this.light_status = consts.LIGHT_STATUS.ON;
            new_status = 'on';
        }else{
            this.light_status = consts.LIGHT_STATUS.OFF;
            new_status = 'off';
        }

        let msg = {
            cmd: "light_ctrl",
            params: {
                action: new_status
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    adjustLight(deltaIntensity){
        if( this.light_status === consts.LIGHT_STATUS.ON){
            deltaIntensity = -deltaIntensity;
            deltaIntensity = parseInt( Math.max(-8, Math.min(deltaIntensity, 8)) );
            this.light_intensity += deltaIntensity;
            this.light_intensity = parseInt( Math.max(0, Math.min(this.light_intensity, 255)) );

            let msg = {
                cmd: "light_ctrl",
                params: {
                    action: 'dim',
                    intensity: this.light_intensity
                }
            };

            this.lastCtrlMsg = msg;
            this.sendCtrlMsg(msg);
        }
    }


    sendTestMessage() {
        var msg = {
            cmd: "set_speed",
            params: {
                speed: 0.8
            }
        };


        console.log(this.getSocket());
        this.cmd_socket.send(JSON.stringify(msg));

        console.log("Test Message sent to server!");
    }

    drawFaces(faces) {

        var size = faces.length;
        for (var i = 0; i < size; i++) {
            var f = faces[i];
            this.drawRect(f.x, f.y, f.width, f.height);
        }

    }

    updateFollowStatus() {
        let wheels = this.follow_status === consts.FOLLOW_STATUS.WHEELS;
        let cam = this.follow_status === consts.FOLLOW_STATUS.GIMBAL;

        let msg = {
            cmd: "follow",
            params: {
                wheels: wheels,
                cam: cam
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    cycleFollowStatus() {
        switch (this.follow_status) {
            case consts.FOLLOW_STATUS.STOP:
                if (this.roverData['mobility'].includes('wheels')) {
                    this.follow_status = consts.FOLLOW_STATUS.WHEELS;
                } else if (this.roverData['mobility'].includes('gimbal')) {
                    this.follow_status = consts.FOLLOW_STATUS.GIMBAL;
                }
                break;
            case consts.FOLLOW_STATUS.WHEELS:
                if (this.roverData['mobility'].includes('gimbal')) {
                    this.follow_status = consts.FOLLOW_STATUS.GIMBAL;
                } else {
                    this.follow_status = consts.FOLLOW_STATUS.STOP;
                }
                break;
            case consts.FOLLOW_STATUS.GIMBAL:
                this.follow_status = consts.FOLLOW_STATUS.STOP;
                break;
        }

        this.updateFollowStatus();
    }

    sendStopTrackingMsg(){
        this.tracking_status = consts.TRACKING_STATUS.STOP;
        this.follow_status = consts.FOLLOW_STATUS.STOP;

        let msg = {
            cmd: "stop_tracking",
            params: {}
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    sendTrackFacesMsg(){
        this.tracking_status = consts.TRACKING_STATUS.FACES;

        let msg = {
            cmd: "track_faces",
            params: {}
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    sendTrackMsg() {
        this.tracking_status = consts.TRACKING_STATUS.CUSTOM;
        this.trackStatusChangeCb();

        let x = Math.min(this.roi.x, this.currX);
        let y = Math.min(this.roi.y, this.currY);
        let w = Math.abs(this.roi.w);
        let h = Math.abs(this.roi.h);

        let msg = {
            cmd: "track_custom",
            params: {
                roi: [x, y, w, h]
            }

        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }


    drawRect(x, y, width, height) {


        //CONFIG FOR LINE STYLE
        this.ctx.strokeStyle = LINE_COLOR;
        this.ctx.lineWidth = LINE_WIDTH;


        this.ctx.rect(x, y, width, height);
        this.ctx.stroke();

    }

    initOverlayCanvas() {

        this.overlay_canvas.addEventListener("mousemove", function (e) {
            this.findXY('move', e);
        }.bind(this), false);
        this.overlay_canvas.addEventListener("mousedown", function (e) {
            this.findXY('down', e);
        }.bind(this), false);
        this.overlay_canvas.addEventListener("mouseup", function (e) {
            this.findXY('up', e);
        }.bind(this), false);
        this.overlay_canvas.addEventListener("mouseout", function (e) {
            this.findXY('out', e);
        }.bind(this), false);

    }

    findXY(res, e) {
        if (res === 'down') {
            this.prevX = this.currX;
            this.prevY = this.currY;
            this.currX = e.clientX - this.canvas.offsetLeft;
            this.currY = e.clientY - this.canvas.offsetTop;

            this.flag = true;

            this.roi.x = this.currX;
            this.roi.y = this.currY;
        }
        if (res === 'up' || res === "out") {

            if (this.flag) {
                this.sendTrackMsg();
            }

            this.flag = false;

            if (this.roi.w !== 0 && this.roi.h !== 0) {
                //send the command to the server adjusted for negative values
                this.roi.x = 0;
                this.roi.y = 0;
                this.roi.w = 0;
                this.roi.h = 0;
            }


            this.overlay_ctx.clearRect(0, 0, this.w, this.h);

        }
        if (res === 'move') {
            if (this.flag) {
                this.prevX = this.currX;
                this.prevY = this.currY;
                this.currX = e.clientX - this.canvas.offsetLeft;
                this.currY = e.clientY - this.canvas.offsetTop;

                this.draw_current_roi();
            }
        }

    }


    draw_current_roi() {
        this.overlay_ctx.strokeStyle = LINE_COLOR;
        this.overlay_ctx.lineWidth = LINE_WIDTH;


        this.roi.w = this.currX - this.roi.x;
        this.roi.h = this.currY - this.roi.y;
        this.overlay_ctx.clearRect(0, 0, this.w, this.h);
        this.overlay_ctx.strokeRect(this.roi.x, this.roi.y, this.roi.w, this.roi.h);
    }

    selectRover(roverIndex) {
        if( roverIndex < 0)
            return;

        this.currentRoverId = this.rovers[roverIndex].rover_id;
        this.roverData = this.rovers[roverIndex].rover_data;

        let roverList = document.getElementById('roverSelector');
        roverList.style.display = 'none'

        console.log(this.roverData);

        let connect_cmd = {
            "client_id": this.id,
            "rover_id": this.currentRoverId,
            "cmd": "connect"
        };

        this.lastCtrlMsg = connect_cmd;
        this.sendCtrlMsg(connect_cmd);
    }

    createRoverElement(rover, index) {
        let roverHandler = this;
        let fragmentString = `<div class='roverElement' data-idx='${index}'> Rover name ${rover.rover_data.name} <br> \
                                Description: ${rover.rover_data.description} </div>`;
        return document.createRange().createContextualFragment(fragmentString);
    }

    populateRoverList() {
        let roverHandler = this;
        let roverList = document.getElementById('roverSelector');
        roverList.style.display = 'flex'

        let rover;
        for (rover = 0; rover < this.rovers.length; rover++) {
            let appendedRover = roverList.appendChild(this.createRoverElement(this.rovers[rover], rover));
        }

        document.querySelectorAll('.roverElement').forEach(function (e){
            e.onclick = function (event) {
                roverHandler.selectRover(e.dataset.idx);
            };
        })

    }

    drawCrosshHair() {
        let crosshair = document.getElementById('crossHair');
        let ctx = crosshair.getContext("2d");
        ctx.lineWidth = 5;

        ctx.strokeRect(310, 170, 20, 20);
    }
}
