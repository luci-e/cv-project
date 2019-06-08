'use strict';

import * as RL from './RoverLibs.js';

const SERVER_ADDRESS = 'ws://192.168.0.18';
const COMMAND_PORT = 8888;
const STREAMING_PORT = 8889;


var keys = new RL.CommandHandler("commands-container");
var rover = new RL.RoverHandler("SHA", keys, SERVER_ADDRESS, COMMAND_PORT, STREAMING_PORT);
//var rover = new RL.RoverHandler("SHA2", keys, SOCKET_ADDR);


rover.connectToServer();

//
// setTimeout(function() {
//
// 	console.log("Starting, hope OpenCV loaded...");
//
//
// 	let utils = new Utils('errorMessage'); //use utils class
//
// 	let faceCascadeFile = './haarcascade_frontalface_default.xml';
// 	let classifier = new cv.CascadeClassifier();
// 	let dst = new cv.Mat(640, 480, cv.CV_8UC4);
//
//
//
// 	let faces = new cv.RectVector();
// 	let src = new cv.imread('videoInput');
// 	let gray = new cv.Mat();
// 	let FPS = 30;
//
// 	var loopFun =  function() {
//
// 		let begin = Date.now()
//
//
// 		src = new cv.imread('videoInput');
// 		src.copyTo(dst);
//
// 		cv.cvtColor(dst, gray, cv.COLOR_RGBA2GRAY, 0);
//
// 		classifier.detectMultiScale(gray, faces, 1.1, 3, 0);
//
// 		for (let i = 0; i < faces.size(); ++i) {
// 		    let point1 = new cv.Point(faces.get(i).x, faces.get(i).y);
// 		    let point2 = new cv.Point(faces.get(i).x + faces.get(i).width,
// 		                              faces.get(i).y + faces.get(i).height);
// 		    cv.rectangle(dst, point1, point2, [255, 0, 0, 255]);
// 		}
//
// 		cv.imshow('videoOutput', dst);
//
//
// 		setTimeout(loopFun, 1000/FPS - Date.now() + begin);
//
//
// 	}
//
// 	//load classifier and run loopFun when done
// 	utils.createFileFromUrl(faceCascadeFile, faceCascadeFile, () => {
// 		classifier.load(faceCascadeFile);
// 		loopFun();
// 	});
//
//
//
// }, 5000);