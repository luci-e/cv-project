export default class Constants {

	//Misc vars for arrowKeys sprite
	constructor() {
		
		this.ARROW_CONTAINER_SIZE = 241;
		this.AIDLE_ID = 0;
		this.AUP_ID = 3;
		this.ALEFT_ID = 1;
		this.ARIGHT_ID = 2;
		this.ADOWN_ID = 4;
		this.ACCW_ID = 5;
		this.ACW_ID = 6;
	}
}

export const ROVER_DIRECTION = {
	STOP: 0,
	FORWARD: 1,
	BACK: 2,
	LEFT: 4,
	RIGHT: 8,
	CW: 16,
	CCW: 32
};

export const ALLOWED_DIRECTIONS =  new Set([0, 1, 2, 4, 8, 16, 32, 5, 9, 6, 10]);

export const CAM_DIRECTION = {
	STOP: 0,
	UP: 1,
	DOWN: 2,
	CW: 4,
	CCW: 8,
	CLR: 16
};

export const FOLLOW_STATUS = {
	STOP : 0,
	WHEELS : 1,
	GIMBAL : 2
};

export const ALLOWED_CAM_DIRECTIONS =  new Set([0, 1, 2, 4, 8, 5, 9, 6, 10]);

