#include "types.h"

CAM_DIRECTION operator&(CAM_DIRECTION& lhs, CAM_DIRECTION& rhs) {
	CAM_DIRECTION result = CAM_DIRECTION::STOP;

	result = static_cast<CAM_DIRECTION>(static_cast<int>(lhs) &
		static_cast<int>(rhs));

	return result;
}

CAM_DIRECTION operator&(CAM_DIRECTION& lhs, CAM_DIRECTION rhs) {
	CAM_DIRECTION result = CAM_DIRECTION::STOP;

	result = static_cast<CAM_DIRECTION>(static_cast<int>(lhs) &
		static_cast<int>(rhs));

	return result;
}

CAM_DIRECTION operator|(CAM_DIRECTION lhs, CAM_DIRECTION rhs) {
	CAM_DIRECTION result = CAM_DIRECTION::STOP;

	result = static_cast<CAM_DIRECTION>(static_cast<int>(lhs) |
		static_cast<int>(rhs));

	return result;
}

CAM_DIRECTION & operator|=(CAM_DIRECTION & lhs, CAM_DIRECTION rhs) {
	lhs = static_cast<CAM_DIRECTION>(static_cast<int>(lhs) |
		static_cast<int>(rhs));

	return lhs;
}
