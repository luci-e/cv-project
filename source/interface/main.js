'use strict';

import * as RL from './RoverLibs.js';


var COMMAND_PORT = 8888;
var STREAMING_PORT = 8889;
var SERVER_ADDRESS = 'ws://127.0.0.1';
var CONNECTION_METHOD = '';



var keys = new RL.CommandHandler("commands-container");
var rover = new RL.RoverHandler("SHA", keys, SERVER_ADDRESS, COMMAND_PORT, STREAMING_PORT);
//var rover = new RL.RoverHandler("SHA2", keys, SOCKET_ADDR);

rover.connectToServer();
//connection.sendTestMessage();

/*
setTimeout(function() {

	let video = document.getElementById('videoInput');
	let videoCtx = video.getContext('2d');
	let src = new cv.Mat(video.height, video.width, cv.CV_8UC4);
	let dst = new cv.Mat(video.height, video.width, cv.CV_8UC4);
	let gray = new cv.Mat();
	//let cap = new cv.VideoCapture(video);
	let faces = new cv.RectVector();
	// load pre-trained classifiers
	let classifier = new cv.CascadeClassifier();  // initialize classifier

	let utils = new Utils('errorMessage'); //use utils class
	let faceCascadeFile = './haarcascade_frontalface_default.xml'; // path to xml

	// use createFileFromUrl to "pre-build" the xml
	utils.createFileFromUrl(faceCascadeFile, faceCascadeFile, () => {
	    classifier.load(faceCascadeFile); // in the callback, load the cascade from file 
	});

	const FPS = 30;


	function processVideo() {
		try {
			if (false) {
				// clean and stop.
				src.delete();
				dst.delete();
				gray.delete();
				faces.delete();
				classifier.delete();
				return;
			}
			let begin = Date.now();
			// start processing.

			let imgData = videoCtx.getImageData(0, 0, video.width, video.height);

			console.log(imgData);


			src = cv.matFromImageData(imgData);
			src.copyTo(dst);

			console.log(src);
			console.log(dst);

			cv.cvtColor(dst, gray, cv.COLOR_RGBA2GRAY, 0);
			// detect faces.
			console.log("OK");
			classifier.detectMultiScale(gray, faces, 1.1, 3, 0);

			// draw faces.
			for (let i = 0; i < faces.size(); ++i) {
				let face = faces.get(i);
				let point1 = new cv.Point(face.x, face.y);
				let point2 = new cv.Point(face.x + face.width, face.y + face.height);
				cv.rectangle(dst, point1, point2, [255, 0, 0, 255]);
			}
			cv.imshow('canvasOutput', dst);
			// schedule the next one.
			let delay = 1000/FPS - (Date.now() - begin);
			setTimeout(processVideo, delay);
		} catch (err) {
			console.log(err);
		}
	};


	// schedule the first one.
	setTimeout(processVideo, 0);

}, 1000);

*/





setTimeout(function() {

	console.log("Starting, hope OpenCV loaded...!");


	let utils = new Utils('errorMessage'); //use utils class

	let faceCascadeFile = './haarcascade_frontalface_default.xml';
	let classifier = new cv.CascadeClassifier();

	var loopFun =  function() {
	
		let src = cv.imread('videoInput');
		let gray = new cv.Mat();
		cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY, 0);
		let faces = new cv.RectVector();
		// load pre-trained classifiers


			// load pre-trained classifiers
		  // initialize classifier





		//eyeCascade.load('haarcascade_eye.xml');
		// detect faces
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
		src.delete(); gray.delete();
		faces.delete();


	
		setTimeout(loopFun, 1000/60);

	}


	//let mat = cv.imread('videoInput');
	//cv.imshow('videoOutput', mat);
	//mat.delete();

	utils.createFileFromUrl(faceCascadeFile, faceCascadeFile, () => {
		classifier.load(faceCascadeFile);
		loopFun();
	});
}, 5000);