#include "types.h"
#include <Servo.h>

class rover_HAL {

	class motor_controller {
	public:

		int motor_status = 0;
		int motor_pin = 0;
		Servo motor;

		float angle_upper_limit = 90.0, angle_lower_limit = -90.0;

		unsigned int angle_min_duration,
			angle_centre_duration,
			angle_max_duration;

		unsigned int min_ccw_speed_duration,
			max_ccw_speed_duration,
			min_cw_speed_duration,
			max_cw_speed_duration,
			stop_duration;

		motor_controller() {};

		motor_controller(int pin) {
			this->motor_pin = pin;
			this->motor.attach(pin);

			Serial.println("Created motor controller ");
			Serial.println(this->motor_pin);
		}

		void set_angle(float angle) {
			angle = constrain(angle, angle_lower_limit, angle_upper_limit);
			unsigned int write_duration = this->angle_centre_duration;

			if (angle < 0.0) {
				write_duration = (int)(this->angle_centre_duration + angle * (abs(this->angle_centre_duration - this->angle_min_duration)) / 90.0);
			}
			else if (angle > 0.0) {
				write_duration = (int)(this->angle_centre_duration + angle * (abs(this->angle_max_duration - this->angle_centre_duration)) / 90.0);
			}

			this->motor.writeMicroseconds(write_duration);
		}

		void set_speed(float speed_percent) {
			speed_percent = constrain(speed_percent, -1.0, 1.0);
			unsigned int write_duration = this->stop_duration;

			Serial.print("Setting motor speed to:");
			Serial.println(speed_percent);

			if (speed_percent > 0.0) {
				write_duration = (unsigned int)((float)this->min_cw_speed_duration + speed_percent * (float)(max_cw_speed_duration - min_cw_speed_duration));
			}
			else if (speed_percent < 0.0) {
				write_duration = (unsigned int)((float)this->min_ccw_speed_duration + speed_percent * (float)(min_ccw_speed_duration - max_ccw_speed_duration));
			}

			Serial.print("Writing ");
			Serial.println(write_duration);
			this->motor.writeMicroseconds(write_duration);
		}


	};

	class movement_controller {
	public:
		motor_controller left_motor;
		motor_controller right_motor;
		float current_speed = 0.0;
		float speed_cap = 0.06;
		float acceleration = 0.3;
		float deceleration = 0.7;

		ROVER_DIRECTION current_rover_direction = ROVER_DIRECTION::STOP;

		movement_controller() {};

		movement_controller(int* pins) {
			left_motor = motor_controller(pins[0]);
			right_motor = motor_controller(pins[1]);
		}

		void update_movement() {
			Serial.print("Current speed:");
			Serial.println(this->current_speed);

			switch (this->current_rover_direction) {
			case ROVER_DIRECTION::STOP: {
				this->left_motor.set_speed(-this->current_speed);
				this->right_motor.set_speed(this->current_speed);
				break;
			}
			case ROVER_DIRECTION::FORWARD: {
				this->left_motor.set_speed(this->current_speed);
				this->right_motor.set_speed(-this->current_speed);
				break;
			}
			case ROVER_DIRECTION::BACK: {
				this->left_motor.set_speed(-this->current_speed);
				this->right_motor.set_speed(this->current_speed);
				break;
			}
			case ROVER_DIRECTION::LEFT: {
				this->left_motor.set_speed(0.0);
				this->right_motor.set_speed(-this->current_speed);
				break;
			}
			case ROVER_DIRECTION::RIGHT: {
				this->left_motor.set_speed(this->current_speed);
				this->right_motor.set_speed(0.0);
				break;
			}
			case ROVER_DIRECTION::FORWARD_LEFT: {
				this->left_motor.set_speed(0.8 * this->current_speed);
				this->right_motor.set_speed(-this->current_speed);
				break;
			}
			case ROVER_DIRECTION::FORWARD_RIGHT: {
				this->left_motor.set_speed(this->current_speed);
				this->right_motor.set_speed(-0.8 * this->current_speed);
				break;
			}
			case ROVER_DIRECTION::BACK_LEFT: {
				this->left_motor.set_speed(-0.8 * this->current_speed);
				this->right_motor.set_speed(this->current_speed);
				break;
			}
			case ROVER_DIRECTION::BACK_RIGHT: {
				this->left_motor.set_speed(-this->current_speed);
				this->right_motor.set_speed(0.8 * this->current_speed);
				break;
			}
			case ROVER_DIRECTION::CW: {
				this->left_motor.set_speed(this->current_speed);
				this->right_motor.set_speed(this->current_speed);
				break;
			}
			case ROVER_DIRECTION::CCW: {
				this->left_motor.set_speed(-this->current_speed);
				this->right_motor.set_speed(-this->current_speed);
				break;
			}
			}
		}


		void update(unsigned long delta_t) {
			// Update the speed
			if (this->current_rover_direction != ROVER_DIRECTION::STOP) {
				if (this->current_speed < this->speed_cap) {
					float delta_v = this->acceleration * (float)delta_t / 1000.0;
					Serial.print("Delta_v:");
					Serial.println(delta_v);

					this->current_speed = constrain(this->current_speed + delta_v, 0.0, this->speed_cap);
					this->update_movement();
				}
				else if (this->current_speed > this->speed_cap) {
					goto brake;
				}
			}
			else {
				if (this->current_speed > 0.0) {
				brake:
					float delta_v = this->deceleration * (float)delta_t / 1000.0;
					Serial.print("Delta_v:");
					Serial.println(delta_v);

					this->current_speed = constrain(this->current_speed - delta_v, 0.0, this->speed_cap);
					this->update_movement();
				}
			}


		}

		void stop() {
			this->left_motor.set_speed(0.0);
			this->right_motor.set_speed(0.0);
			this->current_rover_direction = ROVER_DIRECTION::STOP;
			this->current_speed = 0;
		}
	};

	class camera_controller {
	public:
		motor_controller x_motor;
		motor_controller z_motor;
		CAM_DIRECTION current_camera_direction = CAM_DIRECTION::STOP;
		int xAngle = 0, zAngle = 0;

		int xAngle_upper_limit = 90, xAngle_lower_limit = -90;
		int zAngle_upper_limit = 90, zAngle_lower_limit = -90;

		float angular_velocity = 5;

		camera_controller() {};

		camera_controller(int* pins) {
			x_motor = motor_controller(pins[0]);
			z_motor = motor_controller(pins[1]);
		}

		void update_limits() {
			this->x_motor.angle_upper_limit = this->xAngle_upper_limit;
			this->x_motor.angle_lower_limit = this->xAngle_lower_limit;
			this->z_motor.angle_upper_limit = this->zAngle_upper_limit;
			this->z_motor.angle_lower_limit = this->zAngle_lower_limit;
		}

		void update_movement() {
			this->xAngle = constrain(this->xAngle, this->xAngle_lower_limit, this->xAngle_upper_limit);
			this->zAngle = constrain(this->zAngle, this->zAngle_lower_limit, this->zAngle_upper_limit);

			Serial.print("Setting cam to ");
			Serial.print(this->xAngle);
			Serial.print(" ");
			Serial.println(this->zAngle);

			this->x_motor.set_angle(this->xAngle);
			this->z_motor.set_angle(this->zAngle);

			if ((this->xAngle == this->xAngle_lower_limit || this->xAngle == this->xAngle_upper_limit) &&
				(this->zAngle == this->zAngle_lower_limit || this->zAngle == this->zAngle_upper_limit)) {
				this->current_camera_direction = CAM_DIRECTION::STOP;
			}
		}


		void stop() {
			this->current_camera_direction = CAM_DIRECTION::STOP;
		}


		void update(unsigned long delta_t) {
			if (this->current_camera_direction != CAM_DIRECTION::STOP) {
				int delta_angle = max( (int)(this->angular_velocity * (float)delta_t / 1000.0), 1.0);
				Serial.println(delta_angle);

				if ((this->current_camera_direction & CAM_DIRECTION::UP) != CAM_DIRECTION::STOP) {
					this->xAngle += delta_angle;
					Serial.println("Moving up");
				}
				else if ((this->current_camera_direction & CAM_DIRECTION::DOWN) != CAM_DIRECTION::STOP) {
					this->xAngle -= delta_angle;
					Serial.println("Moving down");
				}

				if ((this->current_camera_direction & CAM_DIRECTION::CW) != CAM_DIRECTION::STOP) {
					this->zAngle += delta_angle;
					Serial.println("Moving cw");
				}
				else if ((this->current_camera_direction & CAM_DIRECTION::CCW) != CAM_DIRECTION::STOP) {
					this->zAngle -= delta_angle;
					Serial.println("Moving ccw");
				}

				this->update_movement();
			}
		}
	};

	class distance_sensor_controller {

	public:
		int sensor_pins[2];

		distance_sensor_controller() {}

		distance_sensor_controller(int* sensor_pins) {
			memcpy(this->sensor_pins, sensor_pins, sizeof(int) * 2);

			pinMode(this->sensor_pins[0], OUTPUT);
			pinMode(this->sensor_pins[1], INPUT);

		}

		unsigned long get_distance() {
			digitalWrite(this->sensor_pins[0], LOW);
			delayMicroseconds(5);
			digitalWrite(this->sensor_pins[0], HIGH);
			delayMicroseconds(10);
			digitalWrite(this->sensor_pins[0], LOW);

			unsigned long duration = pulseIn(this->sensor_pins[1], HIGH);

			return (duration / 2.0) / 29.1;
		}
	};

	class laser_controller {
	public:
		int laser_pin;

		laser_controller() {}

		laser_controller(int laser_pin) {
			this->laser_pin = laser_pin;
			pinMode(this->laser_pin, OUTPUT);
		}

		void on() {
			digitalWrite(this->laser_pin, HIGH);
		}

		void off() {
			digitalWrite(this->laser_pin, LOW);
		}

		ROVER_STATUS laser_control(LASER_ACTION action) {

			switch (action) {
			case LASER_ACTION::ON: {

			}

			case LASER_ACTION::OFF: {

			}

			case LASER_ACTION::BLINK: {

			}

			default: {
				return ROVER_STATUS::ERR;
			}
			}
			return ROVER_STATUS::OK;
		}
	};

public:

	movement_controller move_controller;
	camera_controller cam_controller;
	distance_sensor_controller distance_sensor;
	laser_controller laser;

	rover_HAL() {}

	void init_motor_controllers(int* motor_pins, int* camera_motor_pins) {
		this->move_controller = movement_controller(motor_pins);
		this->cam_controller = camera_controller(camera_motor_pins);
	}

	void init_distance_sensor(int* distance_sensor_pins) {
		this->distance_sensor = distance_sensor_controller(distance_sensor_pins);
	}

	void init_laser(int laser_pin) {
		this->laser = laser_controller(laser_pin);
	}

	ROVER_STATUS execute_command(String* command, unsigned int argcount) {
		String cmd = command[0];
		String param = command[1];

		cmd.toLowerCase();
		param.toLowerCase();

		Serial.print("Cmd : ");
		Serial.println(cmd);
		Serial.print("Param : ");
		Serial.println(param);

		if (cmd.equals("move")) {
			ROVER_DIRECTION dir = ROVER_DIRECTION::STOP;
			float duration = 0;

			unsigned long front_distance = this->distance_sensor.get_distance();
			Serial.print("Front distance : ");
			Serial.println(front_distance);

			if (param.equals("w")) {
				dir = ROVER_DIRECTION::FORWARD;
			}
			else if (param.equals("a")) {
				dir = ROVER_DIRECTION::LEFT;
			}
			else if (param.equals("s")) {
				dir = ROVER_DIRECTION::BACK;
			}
			else if (param.equals("d")) {
				dir = ROVER_DIRECTION::RIGHT;
			}
			else if (param.equals("wa")) {
				dir = ROVER_DIRECTION::FORWARD_LEFT;
			}
			else if (param.equals("wd")) {
				dir = ROVER_DIRECTION::FORWARD_RIGHT;
			}
			else if (param.equals("sa")) {
				dir = ROVER_DIRECTION::BACK_RIGHT;
			}
			else if (param.equals("sd")) {
				dir = ROVER_DIRECTION::BACK_LEFT;
			}
			else if (param.equals("e")) {
				dir = ROVER_DIRECTION::CW;
			}
			else if (param.equals("q")) {
				dir = ROVER_DIRECTION::CCW;
			}
			else {
				return ROVER_STATUS::ERR;
			}

			this->move_controller.current_rover_direction = dir;
			this->move_controller.update_movement();

			// Check if it's a free movement
			if (argcount == 3) {
				duration = command[2].toFloat();
			}

		}
		else if (cmd.equals("speed")) {
			float speed = command[1].toFloat();
			this->move_controller.speed_cap = speed;
			this->move_controller.update_movement();
		}
		else if (cmd.equals("move_cam")) {
			String param = command[1];
			CAM_DIRECTION dir = CAM_DIRECTION::STOP;

			if (param.equals("r")) {
				dir = CAM_DIRECTION::UP;
			}
			else if (param.equals("rt")) {
				dir = (CAM_DIRECTION::UP | CAM_DIRECTION::CCW);
			}
			else if (param.equals("ry")) {
				dir = (CAM_DIRECTION::UP | CAM_DIRECTION::CW);
			}
			else if (param.equals("ft")) {
				dir = (CAM_DIRECTION::DOWN | CAM_DIRECTION::CCW);
			}
			else if (param.equals("fy")) {
				dir = (CAM_DIRECTION::DOWN | CAM_DIRECTION::CW);
			}
			else if (param.equals("t")) {
				dir = CAM_DIRECTION::CCW;
			}
			else if (param.equals("y")) {
				dir = CAM_DIRECTION::CW;
			}
			else {
				return ROVER_STATUS::ERR;
			}

			// Check if it's a free movement
			this->cam_controller.current_camera_direction = dir;
		}
		else if (cmd.equals("set_cam")) {
			int xAngle = 0, zAngle = 0;

			xAngle = command[1].toInt();
			zAngle = command[2].toInt();

			this->cam_controller.xAngle = xAngle;
			this->cam_controller.zAngle = zAngle;

			this->cam_controller.update_movement();
			this->cam_controller.current_camera_direction = CAM_DIRECTION::STOP;
		}
		else if (cmd.equals("laser_ctrl")) {

			LASER_ACTION action = LASER_ACTION::OFF;

			if (param.equals("o")) {
				action = LASER_ACTION::OFF;
			}
			else if (param.equals("i")) {
				action = LASER_ACTION::ON;
			}
			else if (param.equals("p")) {
				action = LASER_ACTION::BLINK;
			}
			else {
				return ROVER_STATUS::ERR;
			}
			this->laser.laser_control(action);

		}
		else if (cmd.equals("move_stop")) {

			int motors = 0;

			if (param.equals("w")) {
				this->move_controller.current_rover_direction = ROVER_DIRECTION::STOP;
			}
			else if (param.equals("c")) {
				this->cam_controller.stop();
			}
			else if (param.equals("wc")) {
				this->move_controller.current_rover_direction = ROVER_DIRECTION::STOP;
				this->cam_controller.stop();
			}
			else {
				return ROVER_STATUS::ERR;
			}
		}

		return ROVER_STATUS::OK;
	}

	void update(unsigned long delta_t) {
		//Serial.print("delta_t: ");
		//Serial.println(delta_t);

		this->move_controller.update(delta_t);
		this->cam_controller.update(delta_t);
	}

};

#define MAX_CMD_ARGS 10

class command_parser {

public:
	String command_buffer;
	String current_command[MAX_CMD_ARGS];

	String separators;
	char delimiter;

	unsigned int buffer_size;
	unsigned int current_size = 0;
	unsigned int argcount = 0;

	command_parser() {}

	command_parser(unsigned int buffer_size, String separators, char delimiter) {
		this->command_buffer.reserve(buffer_size);
		this->buffer_size = buffer_size;
		this->separators = separators;
		this->delimiter = delimiter;
	}

	int push_char(char c) {
		this->current_size += 1;
		if (this->current_size < this->buffer_size) {

			if (this->separators.indexOf(c) >= 0 || this->delimiter == c) {
				this->current_command[argcount] = this->command_buffer.substring(0, this->current_size);
				this->current_size = 0;
				this->argcount++;
				this->command_buffer = "";

				if (this->delimiter == c) {
					return 2;
				}

				return 1;
			}

			this->command_buffer += c;
			return 0;

		}
		else {
			return -1;
		}
	}

	void reset() {
		this->current_size = 0;
		this->argcount = 0;
		this->command_buffer = "";
	}

};

rover_HAL g_rover_hal;
command_parser g_command_parser(16u, String(" "), '\n');;

void setup() {
	Serial.begin(9600);

	// Set pins
	int wheels_motors_pins[2] = { 8, 9 };
	int camera_motors_pins[2] = { 10, 11 };
	int distance_sensor_pins[2] = { A0, A1 };
	int laser_pin = A2;

	// Init controllers
	g_rover_hal.init_motor_controllers(wheels_motors_pins, camera_motors_pins);
	g_rover_hal.init_distance_sensor(distance_sensor_pins);
	g_rover_hal.init_laser(laser_pin);

	// Set wheel motors properties
	g_rover_hal.move_controller.left_motor.min_cw_speed_duration = 1520;
	g_rover_hal.move_controller.left_motor.max_cw_speed_duration = 2000;
	g_rover_hal.move_controller.left_motor.min_ccw_speed_duration = 1460;
	g_rover_hal.move_controller.left_motor.max_ccw_speed_duration = 1000;
	g_rover_hal.move_controller.left_motor.stop_duration = 1500;

	g_rover_hal.move_controller.right_motor.min_cw_speed_duration = 1520;
	g_rover_hal.move_controller.right_motor.max_cw_speed_duration = 2000;
	g_rover_hal.move_controller.right_motor.min_ccw_speed_duration = 1460;
	g_rover_hal.move_controller.right_motor.max_ccw_speed_duration = 1000;
	g_rover_hal.move_controller.right_motor.stop_duration = 1500;


	// Set camera motors properties
	g_rover_hal.cam_controller.x_motor.angle_min_duration = 2000;
	g_rover_hal.cam_controller.x_motor.angle_centre_duration = 1500;
	g_rover_hal.cam_controller.x_motor.angle_max_duration = 1000;

	g_rover_hal.cam_controller.z_motor.angle_min_duration = 2000;
	g_rover_hal.cam_controller.z_motor.angle_centre_duration = 1500;
	g_rover_hal.cam_controller.z_motor.angle_max_duration = 1000;

	g_rover_hal.cam_controller.update_movement();
}

unsigned long last_tick = millis();

void loop() {

	// put your main code here, to run repeatedly:
	while (Serial.available()) {
		int ret = g_command_parser.push_char(Serial.read());

		switch (ret) {
		case 1: {
			Serial.println(g_command_parser.current_command[g_command_parser.argcount - 1]);
			break;
		}

		case 2: {
			g_rover_hal.execute_command(g_command_parser.current_command, g_command_parser.argcount);
			g_command_parser.reset();
			break;
		}
		}
	}

	// Perform the updates
	unsigned long now = millis();
	g_rover_hal.update(now - last_tick);
	last_tick = now;
}
