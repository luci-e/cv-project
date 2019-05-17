'use strict';
import uuid4 from '../libs/uuid.js';

export default class RoverHandler {
    constructor(name, bindings, serverAddress, commandPort, streamingPort, createTab) {
        this.serverAddress = serverAddress;
        this.commandPort = commandPort;
        this.streamingPort = streamingPort;
        this.rovers = [];
        this.socket;

        this.lastCtrlMsg;
        this.lastStreamMsg;

        this.id= uuid4();
        this.name=name;
        this.commandHandler = bindings;
        // Show loading notice
        this.canvas = document.getElementById('videoInput');

        this.getCommandHandler().bind(this);

        if(createTab != false)
            this.addToWindow();

        // Setup the WebSocket connection and start the player
        //var client = new WebSocket(this.serverAddress+':'+this.streamingPort);
        //var player = new jsmpeg(client, {canvas:this.canvas});
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
            this.socket = new WebSocket(this.serverAddress+':'+this.commandPort, [this.connectionMethod]);
        else
            this.socket = new WebSocket(this.serverAddress+':'+this.commandPort);

        //var that = this;
        this.socket.onmessage = this.handshakeHandler.bind(this);

        this.socket.onopen = function(event) {
            console.log("Succesfully connected to remote server!");
            this.handshakeHandler(null);
        }.bind(this);

        // this.socket.onmessage = function (answer) {
        //     that.handleAnswer(answer);
        // }


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

    handshakeHandler(answer){
        if(answer == null){
            let hello_msg = {
                "client_id": this.id,
                "cmd": "hello"
            }

            this.lastCtrlMsg = hello_msg;
            this.sendCtrlMsg(hello_msg);
        }else{
            let message = JSON.parse(answer.data);

            switch(this.lastCtrlMsg.cmd){
                case "hello":{
                    console.log(message);

                    let list_cmd = {
                        "client_id": this.id,
                        "cmd": "list"
                    }

                    this.lastCtrlMsg = list_cmd;
                    this.sendCtrlMsg(list_cmd);
                    break;
                }

                case "list":{
                    console.log(message);
                    this.rovers = message['rovers'];

                    let connect_cmd = {
                        "client_id": this.id,
                        "rover_id": message['rovers'][0]['rover_id'],
                        "cmd": "connect"
                    }

                    this.lastCtrlMsg = connect_cmd;
                    this.sendCtrlMsg(connect_cmd);
                    break;
                }

                case "connect":{
                    console.log(message);
                    this.socket.onmessage = this.handleAnswer.bind(this);
                    break;
                }
            }

        }

    }

    handleAnswer(answer) {

        //console.log(answer.data);

        answer = JSON.parse(answer.data);

        if(this.lastCtrlMsg) {
            switch(this.lastCtrlMsg.cmd) {
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

    sendCtrlMsg(msg) {

        try {
            this.getSocket().send(JSON.stringify(msg)+'\n');
        }
        catch(e) {
            console.log("\t-> Could not send message, still not connected!");
        }
    }


    repeatAction(action, timeForAction) {

        action(this);

    }

    forward() {

        var msg = {
            cmd: "move",
            params: {
                direction: ["forward"]
            }
        };
        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);

        console.log(this.getId()+": Sending move forward message");

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

    right() {

        console.log(this.getId()+": Sending move right message");

        var msg = {
            cmd: "move",
            params: {
                direction: ["cw"]
            }
        }

        this.lastCtrlMsg = msg;

        this.sendCtrlMsg(msg);
    }

    left() {

        console.log(this.getId()+": Sending move left message");

        var msg = {
            cmd: "move",
            params: {
                direction: ["ccw"]
            }
        }

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    backward() {

        console.log(this.getId()+": Sending move backward message");

        var msg = {
            cmd: "move",
            params: {
                direction: ["back"]
            }
        }

        this.lastCtrlMsg = msg;

        this.sendCtrlMsg(msg);
    }


    cw() {

        console.log(this.getId()+": Sending move cw message");

        var msg = {
            cmd: "move",
            params: {
                direction: ["forward", "right"]
            }
        }

        this.lastCtrlMsg = msg;

        this.sendCtrlMsg(msg);
    }


    ccw() {

        console.log(this.getId()+": Sending move cw message");

        var msg = {
            cmd: "move",
            params: {
                direction: ["forward", "left"]
            }
        }

        this.lastCtrlMsg = msg;

        this.sendCtrlMsg(msg);
    }




    handleAnswer(message) {
        console.log("Received message from server: "+message.data);
    }

    cameraUp() {

        console.log("HELLO THERE");

        var msg = {
            cmd: "move_cam",
            params: {
                direction: "up"
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }


    cameraDown() {

        console.log("HELLO THERE");

        var msg = {
            cmd: "move_cam",
            params: {
                direction: "down"
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }

    laserOn() {

        console.log("HELLO THERE");

        var msg = {
            cmd: "laser_ctrl",
            params: {
                action: "on"
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
    }


    laserOff() {

        console.log("HELLO THERE");

        var msg = {
            cmd: "laser_ctrl",
            params: {
                action: "off"
            }
        };

        this.lastCtrlMsg = msg;
        this.sendCtrlMsg(msg);
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
