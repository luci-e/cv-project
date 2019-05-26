// types.h

#ifndef _TYPES_h
#define _TYPES_h

#if defined(ARDUINO) && ARDUINO >= 100
	#include "arduino.h"
#else
	#include "WProgram.h"
#endif

// The enum of the possible directions the rover can move
enum class ROVER_DIRECTION {
	STOP,
	FORWARD,
	BACK,
	LEFT,
	FORWARD_LEFT,
	BACK_LEFT,
	FORWARD_RIGHT,
	BACK_RIGHT,
	RIGHT,
	CW,
	CCW
};

// The enum of the possible directions the camera can move
enum class CAM_DIRECTION : int {
	STOP = 0,
	UP = 1,
	DOWN = 2,
	CW = 4,
	CCW = 8
};

CAM_DIRECTION operator&(CAM_DIRECTION& lhs, CAM_DIRECTION& rhs);
CAM_DIRECTION operator&(CAM_DIRECTION& lhs, CAM_DIRECTION rhs);
CAM_DIRECTION operator|(CAM_DIRECTION lhs, CAM_DIRECTION rhs);
CAM_DIRECTION& operator|=(CAM_DIRECTION& lhs, CAM_DIRECTION rhs);

// The enum of the possible motors on the rover
enum class ROVER_MOTORS {
	WHEELS,
	CAMERA
};

// The enum of the possible status of the camera after a move command
enum class MOTOR_STEPS {
	INFINITE
};

// The enum of the possible statuses for the laser
enum class LASER_ACTION {
	ON,
	OFF,
	BLINK
};

// The enum of the possible status of the camera after a move command
enum class ROVER_STATUS {
	OK,
	ERR,
	BLOCKED
};

#endif

