#include "types.h"
#include <Servo.h>

class rover_HAL {

  class motor_controller {
  public:

    int motor_status = 0;
    int motor_pin = 0;
    Servo motor;

    float angle_upper_limit = 90.0, angle_lower_limit = -90.0;

    int angle_min_duration,
      angle_centre_duration,
      angle_max_duration;

    int min_ccw_speed_duration,
      max_ccw_speed_duration,
      min_cw_speed_duration,
      max_cw_speed_duration,
      stop_duration;

    motor_controller() {};

    motor_controller(int pin) {
      this->motor_pin = pin;

      //Serial.println("Created motor controller ");
      //Serial.println(this->motor_pin);
    }

    void attach_free_rotation() {
      this->motor.attach(this->motor_pin, max_ccw_speed_duration, max_cw_speed_duration);
    }

    void attach_constrained_rotation() {
      this->motor.attach(this->motor_pin, angle_min_duration, angle_max_duration);
    }

    void set_angle(float angle) {
      angle = constrain(angle, this->angle_lower_limit, this->angle_upper_limit);
      unsigned int write_duration = this->angle_centre_duration;

      if (angle < 0.0) {
        write_duration = (unsigned int) map(angle, this->angle_lower_limit, 0.0, this->angle_min_duration, this->angle_centre_duration);
      }
      else if (angle > 0.0) {
        write_duration = (unsigned int) map(angle, 0.0, this->angle_upper_limit, this->angle_centre_duration, this->angle_max_duration);
      }

      //Serial.print("Writing ");
      //Serial.println(write_duration);
      this->motor.writeMicroseconds(write_duration);
    }

    void set_speed(float speed_percent) {
      speed_percent = constrain(speed_percent, -1.0, 1.0);
      unsigned int write_duration = this->stop_duration;

      //Serial.print("Setting motor speed to:");
      //Serial.println(speed_percent);

      if (speed_percent > 0.0) {
        write_duration = (unsigned int)(this->min_cw_speed_duration + speed_percent * (max_cw_speed_duration - min_cw_speed_duration));
      }
      else if (speed_percent < 0.0) {
        write_duration = (unsigned int)(this->min_ccw_speed_duration + speed_percent * (min_ccw_speed_duration - max_ccw_speed_duration));
      }

      //Serial.print("Writing ");
      //Serial.println(write_duration);
      this->motor.writeMicroseconds(write_duration);
    }


  };

  class movement_controller {
  public:
    motor_controller left_motor;
    motor_controller right_motor;
    float current_speed = 0.0;
    float speed_cap = 0.2;
    float acceleration = 1.0 / 1000.0;
    float deceleration = 1.0 / 1000.0;

    ROVER_DIRECTION last_rover_direction = ROVER_DIRECTION::STOP;
    ROVER_DIRECTION current_rover_direction = ROVER_DIRECTION::STOP;

    movement_controller() {};

    movement_controller(int* pins) {
      left_motor = motor_controller(pins[0]);
      right_motor = motor_controller(pins[1]);
    }

    void attach() {
      this->left_motor.attach_free_rotation();
      this->right_motor.attach_free_rotation();
    }

    void update_movement() {
      //Serial.print("Current speed:");
      //Serial.println(this->current_speed);

      switch (this->current_rover_direction) {
      case ROVER_DIRECTION::STOP: {
        this->left_motor.set_speed(0.0);
        this->right_motor.set_speed(0.0);
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
        //this->left_motor.set_speed(0.0);
        //this->right_motor.set_speed(-this->current_speed);
        // Actually do ccw
        this->left_motor.set_speed(-min(0.05, this->current_speed));
        this->right_motor.set_speed(-min(0.05, this->current_speed));
        
        break;
      }
      case ROVER_DIRECTION::RIGHT: {
        //this->left_motor.set_speed(this->current_speed);
        //this->right_motor.set_speed(0.0);
        // Actually do cw
        this->left_motor.set_speed(min(0.05, this->current_speed));
        this->right_motor.set_speed(min(0.05, this->current_speed));
        
        break;
      }
      case ROVER_DIRECTION::FORWARD_LEFT: {
        this->left_motor.set_speed(0.6 * this->current_speed);
        this->right_motor.set_speed(-this->current_speed);
        break;
      }
      case ROVER_DIRECTION::FORWARD_RIGHT: {
        this->left_motor.set_speed(this->current_speed);
        this->right_motor.set_speed(-0.6 * this->current_speed);
        break;
      }
      case ROVER_DIRECTION::BACK_LEFT: {
        this->left_motor.set_speed(-0.6 * this->current_speed);
        this->right_motor.set_speed(this->current_speed);
        break;
      }
      case ROVER_DIRECTION::BACK_RIGHT: {
        this->left_motor.set_speed(-this->current_speed);
        this->right_motor.set_speed(0.6 * this->current_speed);
        break;
      }
      case ROVER_DIRECTION::CW: {
        this->left_motor.set_speed(min(0.05, this->current_speed));
        this->right_motor.set_speed(min(0.05, this->current_speed));
        break;
      }
      case ROVER_DIRECTION::CCW: {
        this->left_motor.set_speed(-min(0.05, this->current_speed));
        this->right_motor.set_speed(-min(0.05, this->current_speed));
        break;
      }
      }
    }


    void update(unsigned long delta_t) {
      // Update the speed
      if (this->current_rover_direction != ROVER_DIRECTION::STOP) {
        if (this->current_speed < this->speed_cap) {
          float delta_v = this->acceleration * (float)delta_t;
          //Serial.print("Delta_v:");
          //Serial.println(delta_v);

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
          float delta_v = this->deceleration * (float)delta_t;
          //Serial.print("Delta_v:");
          //Serial.println(delta_v);

          this->current_speed = max(this->current_speed - delta_v, 0.0);
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
    float xAngle = 0, zAngle = 0;

    float xAngle_upper_limit = 90.0, xAngle_lower_limit = -90.0;
    float zAngle_upper_limit = 90.0, zAngle_lower_limit = -90.0;

    float angular_velocity_x = 30 / 1000.0;
    float angular_velocity_z = 30 / 1000.0;

    camera_controller() {};

    camera_controller(int* pins) {
      x_motor = motor_controller(pins[0]);
      z_motor = motor_controller(pins[1]);
    }

    void attach() {
      this->x_motor.attach_constrained_rotation();
      this->z_motor.attach_constrained_rotation();
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

      //Serial.print("Setting cam to ");
      //Serial.print(this->xAngle);
      //Serial.print(" ");
      //Serial.println(this->zAngle);

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
        float delta_angle_x = this->angular_velocity_x * (float)delta_t;
        float delta_angle_z = this->angular_velocity_z * (float)delta_t;

        //Serial.println(delta_angle);

        if ((this->current_camera_direction & CAM_DIRECTION::UP) != CAM_DIRECTION::STOP) {
          this->xAngle -= delta_angle_x;
          //Serial.println("Moving up");
        }
        else if ((this->current_camera_direction & CAM_DIRECTION::DOWN) != CAM_DIRECTION::STOP) {
          this->xAngle += delta_angle_x;
          //Serial.println("Moving down");
        }

        if ((this->current_camera_direction & CAM_DIRECTION::CW) != CAM_DIRECTION::STOP) {
          this->zAngle -= delta_angle_z;
          //Serial.println("Moving cw");
        }
        else if ((this->current_camera_direction & CAM_DIRECTION::CCW) != CAM_DIRECTION::STOP) {
          this->zAngle += delta_angle_z;
          //Serial.println("Moving ccw");
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

  class light_controller {
  public:
    int light_pin;
    int intensity = 0;

    light_controller() {}

    light_controller(int light_pin) {
      this->light_pin = light_pin;
      pinMode(this->light_pin, OUTPUT);
    }

    void on() {
      digitalWrite(this->light_pin, HIGH);
    }

    void off() {
      digitalWrite(this->light_pin, LOW);
    }

    void dim(){
      analogWrite(this->light_pin, this->intensity);
    }

    ROVER_STATUS laser_control(LASER_ACTION action) {

      switch (action) {
      case LASER_ACTION::ON: {
        this->on();
        break;
      }

      case LASER_ACTION::OFF: {
        this->off();
        break;
      }

      case LASER_ACTION::BLINK: {

      }

      default: {
        return ROVER_STATUS::ERR;
      }
      }
      return ROVER_STATUS::OK;
    }


    ROVER_STATUS light_control(LIGHT_ACTION action) {

      switch (action) {
      case LIGHT_ACTION::ON: {
        this->on();
        break;
      }

      case LIGHT_ACTION::OFF: {
        this->off();
        break;
      }

      case LIGHT_ACTION::DIM: {
        this->dim();
        break;
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
  light_controller laser;
  light_controller lights;

  rover_HAL() {}

  void init_motor_controllers(int* motor_pins, int* camera_motor_pins) {
    this->move_controller = movement_controller(motor_pins);
    this->cam_controller = camera_controller(camera_motor_pins);
  }

  void init_distance_sensor(int* distance_sensor_pins) {
    this->distance_sensor = distance_sensor_controller(distance_sensor_pins);
  }

  void init_laser(int laser_pin) {
    this->laser = light_controller(laser_pin);
  }

  void init_lights(int light_pin) {
    this->lights = light_controller(light_pin);
  }

  ROVER_STATUS execute_command(String* command, unsigned int argcount) {
    String cmd = command[0];
    cmd.toLowerCase();

    //Serial.print("Cmd : ");
    //Serial.println(cmd);

    if (cmd.equals("move")) {
      String p_direction = command[1];
      p_direction.toLowerCase();

      //Serial.print("Direction: ");
      //Serial.println(p_direction);

      ROVER_DIRECTION dir = ROVER_DIRECTION::STOP;
      float duration = 0;

      //unsigned long front_distance = this->distance_sensor.get_distance();
      //Serial.print("Front distance : ");
      //Serial.println(front_distance);


      if (p_direction.equals("w")) {
        dir = ROVER_DIRECTION::FORWARD;
      }
      else if (p_direction.equals("a")) {
        dir = ROVER_DIRECTION::LEFT;
      }
      else if (p_direction.equals("s")) {
        dir = ROVER_DIRECTION::BACK;
      }
      else if (p_direction.equals("d")) {
        dir = ROVER_DIRECTION::RIGHT;
      }
      else if (p_direction.equals("wa")) {
        dir = ROVER_DIRECTION::FORWARD_LEFT;
      }
      else if (p_direction.equals("wd")) {
        dir = ROVER_DIRECTION::FORWARD_RIGHT;
      }
      else if (p_direction.equals("sa")) {
        dir = ROVER_DIRECTION::BACK_RIGHT;
      }
      else if (p_direction.equals("sd")) {
        dir = ROVER_DIRECTION::BACK_LEFT;
      }
      else if (p_direction.equals("e")) {
        dir = ROVER_DIRECTION::CW;
      }
      else if (p_direction.equals("q")) {
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
      String p_speed = command[1];
      p_speed.toLowerCase();

      //Serial.print("Speed: ");
      //Serial.println(p_speed);

      float speed = p_speed.toFloat();
      this->move_controller.speed_cap = speed;
      this->move_controller.update_movement();
    }
    else if (cmd.equals("cam_speed")) {
      String p_speed_x = command[2];
      String p_speed_z = command[1];
      p_speed_x.toLowerCase();
      p_speed_z.toLowerCase();

      //Serial.print("Speed: ");
      //Serial.println(p_speed);

      float speed_x = p_speed_x.toFloat();
      float speed_z = p_speed_z.toFloat();

      this->cam_controller.angular_velocity_x = speed_x / 1000.0;
      this->cam_controller.angular_velocity_z = speed_z / 1000.0;

    }
    else if (cmd.equals("move_cam")) {
      String p_cam_dir = command[1];
      p_cam_dir.toLowerCase();

      //Serial.print("Cam dir: ");
      //Serial.println(p_cam_dir);

      CAM_DIRECTION dir = CAM_DIRECTION::STOP;

      if (p_cam_dir.equals("r")) {
        //Serial.print("Going up: ");
        dir = CAM_DIRECTION::UP;
      }
      else if (p_cam_dir.equals("rt")) {
        //Serial.print("Going : up ccw");
        dir = (CAM_DIRECTION::UP | CAM_DIRECTION::CCW);
      }
      else if (p_cam_dir.equals("ry")) {
        //Serial.print("Going : up cw");
        dir = (CAM_DIRECTION::UP | CAM_DIRECTION::CW);
      }
      if (p_cam_dir.equals("f")) {
        //Serial.print("Going : down");
        dir = CAM_DIRECTION::DOWN;
      }
      else if (p_cam_dir.equals("ft")) {
        //Serial.print("Going : down ccw");
        dir = (CAM_DIRECTION::DOWN | CAM_DIRECTION::CCW);
      }
      else if (p_cam_dir.equals("fy")) {
        //Serial.print("Going : down cw");
        dir = (CAM_DIRECTION::DOWN | CAM_DIRECTION::CW);
      }
      else if (p_cam_dir.equals("t")) {
        //Serial.print("Going : ccw");
        dir = CAM_DIRECTION::CCW;
      }
      else if (p_cam_dir.equals("y")) {
        //Serial.print("Going : cw");
        dir = CAM_DIRECTION::CW;
      }

      //Serial.print("Cam direction:");
      //Serial.println(static_cast<int>(dir));

      // Check if it's a free movement
      this->cam_controller.current_camera_direction = dir;
    }
    else if (cmd.equals("set_cam")) {

      String p_x_angle = command[1];
      String p_z_angle = command[2];

      p_x_angle.toLowerCase();
      p_z_angle.toLowerCase();

      //Serial.print("Angles: ");
      //Serial.print(p_x_angle);
      //Serial.print(" ");
      //Serial.println(p_z_angle);

      float xAngle = 0.0, zAngle = 0.0;

      xAngle = p_x_angle.toFloat();
      zAngle = p_z_angle.toFloat();

      this->cam_controller.xAngle = xAngle;
      this->cam_controller.zAngle = zAngle;

      this->cam_controller.update_movement();
      this->cam_controller.current_camera_direction = CAM_DIRECTION::STOP;
    }
    else if (cmd.equals("laser_ctrl")) {
      String p_laser_cmd = command[1];
      p_laser_cmd.toLowerCase();

      //Serial.print("Laser cmd: ");
      //Serial.println(p_laser_cmd);

      LASER_ACTION action = LASER_ACTION::OFF;

      if (p_laser_cmd.equals("o")) {
        action = LASER_ACTION::OFF;
      }
      else if (p_laser_cmd.equals("i")) {
        action = LASER_ACTION::ON;
      }
      else if (p_laser_cmd.equals("p")) {
        action = LASER_ACTION::BLINK;
      }
      else {
        return ROVER_STATUS::ERR;
      }
      this->laser.laser_control(action);
    }
    else if (cmd.equals("light_ctrl")) {
      String p_light_cmd = command[1];
      p_light_cmd.toLowerCase();

      //Serial.print("Light cmd: ");
      //Serial.println(p_light_cmd);

      LIGHT_ACTION action = LIGHT_ACTION::OFF;

      if (p_light_cmd.equals("o")) {
        action = LIGHT_ACTION::OFF;
      }
      else if (p_light_cmd.equals("i")) {
        action = LIGHT_ACTION::ON;
      }
      else if (p_light_cmd.equals("p")) {
        action = LIGHT_ACTION::BLINK;
      }
      else if(p_light_cmd.equals("d")){
        String p_light_intensity = command[2];
        p_light_intensity.toLowerCase();
        
        int intensity = p_light_intensity.toInt();
        intensity = constrain( intensity, 0, 255);

        this->lights.intensity = intensity;
        action = LIGHT_ACTION::DIM;
      }
      else {
        return ROVER_STATUS::ERR;
      }
      this->lights.light_control(action);
    }
    else if (cmd.equals("move_stop")) {
      String p_motors = command[1];
      p_motors.toLowerCase();

      //Serial.print("Motors stop: ");
      //Serial.println(p_motors);

      int motors = 0;

      if (p_motors.equals("w")) {
        this->move_controller.current_rover_direction = ROVER_DIRECTION::STOP;
      }
      else if (p_motors.equals("c")) {
        this->cam_controller.stop();
      }
      else if (p_motors.equals("wc")) {
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
  unsigned int last_index = 0;

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
        this->current_command[argcount].trim();

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
  
  int parse_string( String str ){
    int len = str.length();
    
    for( int i = 0; i <= len; i++){
      char c = str.charAt(i);
      if (this->separators.indexOf(c) >= 0 || i == len ) {
        this->current_command[argcount] = str.substring(this->last_index, i);
        this->current_command[argcount].trim();
        this->argcount++;
        this->last_index = i+1;

      }
    }
  }

  void reset() {
    this->current_size = 0;
    this->argcount = 0;
    this->last_index = 0;
    this->command_buffer = "";
  }

};

rover_HAL g_rover_hal;
command_parser g_command_parser(16u, String(" "), '\n');;

void setup() {
  Serial.begin(9600);

  // Set pins
  int wheels_motors_pins[2] = { 7, 8 };
  int camera_motors_pins[2] = { 12, 17 };
  int distance_sensor_pins[2] = { A0, A1 };
  int laser_pin = 9;
  int light_pin = 10;

  // Init controllers
  g_rover_hal.init_motor_controllers(wheels_motors_pins, camera_motors_pins);
  g_rover_hal.init_distance_sensor(distance_sensor_pins);
  g_rover_hal.init_laser(laser_pin);
  g_rover_hal.init_lights(light_pin);

  // Set wheel motors properties
  g_rover_hal.move_controller.left_motor.min_cw_speed_duration = 1520;
  g_rover_hal.move_controller.left_motor.max_cw_speed_duration = 2000;
  g_rover_hal.move_controller.left_motor.min_ccw_speed_duration = 1457;
  g_rover_hal.move_controller.left_motor.max_ccw_speed_duration = 995;
  g_rover_hal.move_controller.left_motor.stop_duration = 1500;

  g_rover_hal.move_controller.right_motor.min_cw_speed_duration = 1520;
  g_rover_hal.move_controller.right_motor.max_cw_speed_duration = 2000;
  g_rover_hal.move_controller.right_motor.min_ccw_speed_duration = 1457;
  g_rover_hal.move_controller.right_motor.max_ccw_speed_duration = 995;
  g_rover_hal.move_controller.right_motor.stop_duration = 1500;

  g_rover_hal.move_controller.attach();

  // Set camera motors properties
  g_rover_hal.cam_controller.x_motor.angle_min_duration = 544;
  g_rover_hal.cam_controller.x_motor.angle_centre_duration = 1500;
  g_rover_hal.cam_controller.x_motor.angle_max_duration = 2500;

  g_rover_hal.cam_controller.z_motor.angle_min_duration = 544;
  g_rover_hal.cam_controller.z_motor.angle_centre_duration = 1500;
  g_rover_hal.cam_controller.z_motor.angle_max_duration = 2500;

  g_rover_hal.cam_controller.attach();

  g_rover_hal.cam_controller.update_movement();
}

unsigned long last_tick = millis();

void loop() {

  bool ex_cmd = false;

  // put your main code here, to run repeatedly:
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    g_command_parser.parse_string(cmd);
    g_rover_hal.execute_command( g_command_parser.current_command, g_command_parser.argcount);
    g_command_parser.reset();
    ex_cmd = true;
  }
    
    // Perform the updates
    unsigned long now = millis();
    unsigned long delta_t = now - last_tick;

    //Serial.println(delta_t);

    if( (delta_t > 0) || ex_cmd ){
      g_rover_hal.update(delta_t);
      last_tick = now;
    }
}
