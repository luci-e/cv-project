// The enum of the possible directions the rover can move
typedef enum ROVER_DIRECTION {
  FORWARD = 1,
  BACK = 2,
  LEFT = 4,
  RIGHT = 8,
  CW = 16,
  CCW = 32
} ROVER_DIRECTION;

// The enum of the possible directions the camera can move
typedef enum CAM_DIRECTION {
  UP = 1,
  DOWN = 2
} CAM_DIRECTION;

// The enum of the possible statuses for the laser
typedef enum LASER_ACTION {
  ON = 1,
  OFF = 2,
  BLINK = 4
} LASER_ACTION;

// The enum of the possible status of the camera after a move command
typedef enum ROVER_STATUS {
  OK = 0,
  BLOCKED = 1,
  CAM_TOP_LIMIT = 2,
  CAM_BOTTOM_LIMIT = 4
} ROVER_STATUS;

class rover_HAL {

    class motor_controller {
      public:

        unsigned long stepper_delay = 1;

        int motor_status = 0;
        int motor_pins[4];

        // Stepping sequence for 28BYJ-48 Stepper Motor with ULN2003 Driver
        unsigned int motor_steps[8] = {
          8,
          12,
          4,
          6,
          2,
          3,
          1,
          9
        };

        int steps_len = 8;

        motor_controller() {};

        motor_controller( int* pins ) {
          // The number representing the status of the stepper motors in the motor steps list
          memcpy( this->motor_pins, pins, sizeof(int) * 4 );

          pinMode( this->motor_pins[0], OUTPUT);
          pinMode( this->motor_pins[1], OUTPUT);
          pinMode( this->motor_pins[2], OUTPUT);
          pinMode( this->motor_pins[3], OUTPUT);

          Serial.println("Created motor controller ");
          Serial.println( this->motor_pins[0] );
          Serial.println( this->motor_pins[1] );
          Serial.println( this->motor_pins[2] );
          Serial.println( this->motor_pins[3] );
        }

        void step_motor( bool direction ) {

          if (direction) {
            this->motor_status = (this->motor_status  + 1 ) % this->steps_len;
          } else {
            this->motor_status = (this->motor_status  - 1 + this->steps_len ) % this->steps_len;
          }

          //Serial.print("Motor status: ");
          //Serial.println( this->motor_status );

          unsigned int pin_values = this->motor_steps[this->motor_status];

          //Serial.println( pin_values );

          for ( int pin = 0 ; pin < 4; pin++ ) {
            unsigned int v = ( pin_values >> pin ) & 1;
            if (v) {
              digitalWrite( this->motor_pins[pin],  HIGH);
            } else {
              digitalWrite( this->motor_pins[pin],  LOW);
            }
          }
          delay(this->stepper_delay);
        }
    };

    class distance_sensor_controller {

      public:
        int sensor_pins[2];

        distance_sensor_controller() {}

        distance_sensor_controller( int *sensor_pins) {
          memcpy( this->sensor_pins, sensor_pins, sizeof(int) * 2 );

          pinMode( this->sensor_pins[0], OUTPUT);
          pinMode( this->sensor_pins[1], INPUT );

        }

        unsigned long read_distance() {
          digitalWrite(this->sensor_pins[0], LOW);
          delayMicroseconds(5);
          digitalWrite(this->sensor_pins[0], HIGH);
          delayMicroseconds(10);
          digitalWrite(this->sensor_pins[0], LOW);

          unsigned long duration = pulseIn(this->sensor_pins[1], HIGH);
         
          return (duration/2) / 29.1;
        }
    };

    class laser_controller{
      public:
        int laser_pin;
        
        laser_controller(){}

        laser_controller( int laser_pin ){
          this->laser_pin = laser_pin;
          pinMode( this->laser_pin, OUTPUT );
        }

        void on(){
          digitalWrite( this->laser_pin, HIGH);
        }

        void off(){
          digitalWrite( this->laser_pin, LOW);
        }

    };

  public:

    motor_controller *left_motor;
    motor_controller *right_motor;
    motor_controller *camera_motor;

    distance_sensor_controller *distance_sensor;
    laser_controller *laser;

    unsigned long wheel_motor_steps = 512;
    unsigned long camera_motor_steps = 100;

    rover_HAL() {
    }

    void init_motors( int *left_motor_pins, int *right_motor_pins, int *camera_motor_pins) {
      this->left_motor = new motor_controller( left_motor_pins );
      this->right_motor = new motor_controller( right_motor_pins );
      this->camera_motor = new motor_controller( camera_motor_pins );
    }

    void init_distance_sensor( int *distance_sensor_pins ) {
      this->distance_sensor = new distance_sensor_controller( distance_sensor_pins );
    }

    void init_laser( int laser_pin ) {
      this->laser = new laser_controller( laser_pin );
    }

    ROVER_STATUS move( ROVER_DIRECTION direction ) {
      for ( int s = 0; s < this->wheel_motor_steps; s++) {
        if (direction == ROVER_DIRECTION::FORWARD) {
          //Serial.println("moving forward");
          this->left_motor->step_motor(true);
          this->right_motor->step_motor(false);
          
        }else if (direction == ROVER_DIRECTION::BACK) {
          //Serial.println("moving back");
          this->left_motor->step_motor(false);
          this->right_motor->step_motor(true);
          
        }else if (direction == ROVER_DIRECTION::LEFT) {
          this->right_motor->step_motor(false);
          
        }else if (direction == ROVER_DIRECTION::RIGHT) {
          this->left_motor->step_motor(true);
          
        }else if (direction == ROVER_DIRECTION::CW) {
          this->left_motor->step_motor(true);
          this->left_motor->step_motor(true);

        }else if (direction == ROVER_DIRECTION::CCW) {
          this->left_motor->step_motor(false);
          this->right_motor->step_motor(false);

        }else if (direction & ROVER_DIRECTION::FORWARD & ROVER_DIRECTION::LEFT) {
          this->left_motor->step_motor(true);
          this->right_motor->step_motor(false);
          this->right_motor->step_motor(false);
          
        }else if (direction & ROVER_DIRECTION::FORWARD & ROVER_DIRECTION::RIGHT) {
          this->left_motor->step_motor(true);
          this->right_motor->step_motor(false);
          this->left_motor->step_motor(true);
          
        }else if (direction & ROVER_DIRECTION::BACK & ROVER_DIRECTION::LEFT) {
          this->left_motor->step_motor(false);
          this->right_motor->step_motor(true);  
          this->right_motor->step_motor(true);
          
        }else if (direction & ROVER_DIRECTION::BACK & ROVER_DIRECTION::RIGHT) {
          this->left_motor->step_motor(false);
          this->right_motor->step_motor(true);
          this->left_motor->step_motor(false);
          
        }
      }

      return ROVER_STATUS::OK;
    }

    ROVER_STATUS move_cam( CAM_DIRECTION direction ) {
      for ( int s = 0; s < this->camera_motor_steps; s++) {
        if (direction & CAM_DIRECTION::UP ) {
          //Serial.println("moving up");
          this->camera_motor->step_motor(true);
        } if (direction & CAM_DIRECTION::DOWN) {
          //Serial.println("moving down");
          this->camera_motor->step_motor(false);
        }
      }

      return ROVER_STATUS::OK;
    }

    ROVER_STATUS laser_control( LASER_ACTION action ) {
      if ( action & LASER_ACTION::ON ) {
        this->laser->on();
      } if ( action & LASER_ACTION::OFF ) {
        this->laser->off();
      } if ( action & LASER_ACTION::BLINK ) {

      }

      return ROVER_STATUS::OK;
    }

    ROVER_STATUS execute_command( String *command) {
      String cmd = command[0];
      String param = command[1];

      cmd.toLowerCase();
      param.toLowerCase();

      Serial.print( "Cmd : ");
      Serial.println( cmd );
      Serial.print( "Param : ");
      Serial.println( param );

      if ( cmd.equals("move") ) {
        ROVER_DIRECTION dir = 0;

        if ( param.equals("w")) {
          dir |= ROVER_DIRECTION::FORWARD;
        } else if ( param.equals("a")) {
          dir |= ROVER_DIRECTION::LEFT;
        } else if ( param.equals("s")) {
          dir |= ROVER_DIRECTION::BACK;
        } else if ( param.equals("d")) {
          dir |= ROVER_DIRECTION::RIGHT;
        } else if ( param.equals("wa")) {
          dir |= ( ROVER_DIRECTION::FORWARD | ROVER_DIRECTION::LEFT );
        } else if ( param.equals("wd")) {
          dir |= ( ROVER_DIRECTION::FORWARD | ROVER_DIRECTION::RIGHT );
        } else if ( param.equals("sa")) {
          dir |= ( ROVER_DIRECTION::BACK | ROVER_DIRECTION::RIGHT );
        } else if ( param.equals("sd")) {
          dir |= ( ROVER_DIRECTION::BACK | ROVER_DIRECTION::LEFT );
        } else if ( param.equals("e")) {
          dir |= ( ROVER_DIRECTION::CW );
        } else if ( param.equals("q")) {
          dir |= ( ROVER_DIRECTION::CCW );
        }

        this->move( dir );

      } else if ( cmd.equals("move_cam") ) {
        String param = command[1];
        CAM_DIRECTION dir = 0;

        if ( param.equals("r") ) {
          dir |= CAM_DIRECTION::UP;
        } else if ( param.equals("f") ) {
          dir |= CAM_DIRECTION::DOWN;
        }

        this->move_cam( dir );

      } else if ( cmd.equals("laser_ctrl") ) {

        LASER_ACTION action = 0;

        if ( param.equals("o") ) {
          action |= LASER_ACTION::OFF;
        } else if ( param.equals("i") ) {
          action |= LASER_ACTION::ON;
        } else if ( param.equals("p") ) {
          action |= LASER_ACTION::BLINK;
        }

        this->laser_control( action );

      }

      return ROVER_STATUS::OK;
    }

} g_rover_hal;

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

    command_parser( unsigned int buffer_size, String separators, char delimiter) {
      this->command_buffer.reserve( buffer_size );
      this->buffer_size = buffer_size;
      this->separators = separators;
      this->delimiter = delimiter;
    }

    int push_char( char c ) {
      this->current_size += 1;
      if ( this->current_size < this->buffer_size ) {

        if (this->separators.indexOf(c) >= 0 || this->delimiter == c) {
          this->current_command[argcount] = this->command_buffer.substring(0, this->current_size);
          this->current_size = 0;
          this->argcount++;
          this->command_buffer = "";

          if ( this->delimiter == c ) {
            return 2;
          }

          return 1;
        }

        this->command_buffer += c;
        return 0;

      } else {
        return -1;
      }
    }

    void reset() {
      this->current_size = 0;
      this->argcount = 0;
      this->command_buffer = "";
    }

} g_command_parser;


void setup() {
  Serial.begin(9600);

  // put your setup code here, to run once:
  int left_motor_pins[4] = {2, 3, 4, 5};
  int right_motor_pins[4] = {6, 7, 8, 9};
  int camera_motor_pins[4] = {10, 11, 12, 13};
  int distance_sensor_pins[2] = { A0, A1 };
  int laser_pin = A2;

  g_rover_hal = rover_HAL();

  g_rover_hal.init_motors( left_motor_pins, right_motor_pins, camera_motor_pins);
  g_rover_hal.init_distance_sensor( distance_sensor_pins );
  g_rover_hal.init_laser( laser_pin );

  g_command_parser = command_parser(16u, String(" "), '\n');
}

void loop() {
  // put your main code here, to run repeatedly:
  while (Serial.available()) {
    int ret = g_command_parser.push_char( Serial.read() );

    switch (ret) {
      case 1: {
          Serial.println( g_command_parser.current_command[ g_command_parser.argcount - 1]);
          break;
        }

      case 2: {
          g_rover_hal.execute_command( g_command_parser.current_command );
          g_command_parser.reset();
          break;
        }
    }
  }

}
