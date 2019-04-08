'use strict';

import * as RL from './RoverLibs.js';

var SERVER_ADDRESS = 'ws://127.0.0.1';
var COMMAND_PORT = 8888;
var STREAMING_PORT = 8889;



var keys = new RL.CommandHandler("commands-container");
var rover = new RL.RoverHandler("SHA", keys, SERVER_ADDRESS, COMMAND_PORT, STREAMING_PORT);
//var rover = new RL.RoverHandler("SHA2", keys, SOCKET_ADDR);

rover.connectToServer();


setTimeout(function() {

	console.log("Starting, hope OpenCV loaded...");


	let utils = new Utils('errorMessage'); //use utils class

	let faceCascadeFile = './haarcascade_frontalface_default.xml';
	let classifier = new cv.CascadeClassifier();

	var loopFun =  function() {
	
		let src = cv.imread('videoInput');
		let gray = new cv.Mat();
		cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY, 0);
		let faces = new cv.RectVector();
		let msize = new cv.Size(0, 0);


		classifier.detectMultiScale(gray, faces, 1.1, 3, 0, msize, msize);

		for (let i = 0; i < faces.size(); ++i) {
		    let roiGray = gray.roi(faces.get(i));
		    let roiSrc = src.roi(faces.get(i));
		    let point1 = new cv.Point(faces.get(i).x, faces.get(i).y);
		    let point2 = new cv.Point(faces.get(i).x + faces.get(i).width,
		                              faces.get(i).y + faces.get(i).height);
		    cv.rectangle(src, point1, point2, [255, 0, 0, 255]);
		    roiGray.delete(); roiSrc.delete();
		}

		cv.imshow('videoOutput', src);
		src.delete(); gray.delete(); faces.delete();
	
		setTimeout(loopFun, 1000/60);

	}

	//load classifier and run loopFun when done
	utils.createFileFromUrl(faceCascadeFile, faceCascadeFile, () => {
		classifier.load(faceCascadeFile);
		loopFun();
	});


}, 5000);