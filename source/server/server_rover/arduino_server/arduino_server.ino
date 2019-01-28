// The enum of the possible directions the rover can move
typedef enum ROVER_DIRECTION {
  FORWARD = 1,
  BACK = 2,
  LEFT = 4,
  RIGHT = 8
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

    class motor_controller{
        public:

          unsigned long stepper_delay = 2;
                    
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

          motor_controller(){};
              
          motor_controller( int* pins ){
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
  
          void step_motor( bool direction ){
            
              if(direction){
                  this->motor_status = (this->motor_status  + 1 ) % this->steps_len;
              }else{
                  this->motor_status = (this->motor_status  - 1 + this->steps_len ) % this->steps_len;
              }

              //Serial.print("Motor status: ");
              //Serial.println( this->motor_status );
  
              unsigned int pin_values = this->motor_steps[this->motor_status];
              
              //Serial.println( pin_values );
              
              for( int pin = 0 ; pin < 4; pin++ ){
                  unsigned int v = ( pin_values >> pin ) & 1;
                  if(v){
                      digitalWrite( this->motor_pins[pin],  HIGH);
                  }else{
                      digitalWrite( this->motor_pins[pin],  LOW);
                  }
              }
              delay(this->stepper_delay);        
          }          
    };

  public:

    motor_controller *left_motor;
    motor_controller *right_motor;
    motor_controller *camera_motor;

    unsigned long wheel_motor_steps = 512;
    unsigned long camera_motor_step = 100;
          
    rover_HAL() {
    }

    void init_motors( int *left_motor_pins, int *right_motor_pins, int *camera_motor_pins){
      this->left_motor = new motor_controller( left_motor_pins );
      this->right_motor = new motor_controller( right_motor_pins );
      this->camera_motor = new motor_controller( camera_motor_pins );
    }

    int move( ROVER_DIRECTION direction ){
      for( int s = 0; s < this->wheel_motor_steps; s++){
        if (direction & ROVER_DIRECTION::FORWARD){
            //Serial.println("moving forward");
            this->left_motor->step_motor(false);
            this->right_motor->step_motor(true);
        }if (direction & ROVER_DIRECTION::BACK){
            //Serial.println("moving back");
            this->left_motor->step_motor(true);
            this->right_motor->step_motor(false);
        }if (direction & ROVER_DIRECTION::LEFT){
            this->left_motor->step_motor(false);
            this->right_motor->step_motor(false);
        }if (direction & ROVER_DIRECTION::RIGHT){
            this->left_motor->step_motor(true);
            this->right_motor->step_motor(true);
        }  
      }
      
      return ROVER_STATUS::OK;
    }
    
}g_rover_hal;



void setup() {
  Serial.begin(9600);

  // put your setup code here, to run once:
  int left_motor_pins[4] = {2,3,4,5};
  int right_motor_pins[4] = {6,7,8,9};
  int camera_motor_pins[4] = {10,11,12,13};

  g_rover_hal = rover_HAL();
  g_rover_hal.init_motors( left_motor_pins, right_motor_pins, camera_motor_pins);
}

void loop() {
  // put your main code here, to run repeatedly:
  while (Serial.available()) {
    String command = Serial.readString();

    Serial.print("Received ");
    Serial.println(command);
    // delay 10 milliseconds before the next reading:

    if( command.charAt(0) == 'e'){
      g_rover_hal.move( ROVER_DIRECTION::FORWARD );
    }else{
      g_rover_hal.move( ROVER_DIRECTION::BACK );
    }
    delay(10);
  }

}
