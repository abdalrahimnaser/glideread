#include <stdio.h>
#include "driver/gpio.h"
#include "hal/gpio_types.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BUTTON_PIN 1
#define LED_PIN    2

// defintions (move to .h)
typedef enum {
    IDLE, 
    SCANNING, 
    } system_state_t; // as far as i know this copiles into an int, if u want that explicitly a different type like uint8_t, u can use special syntax that does it.??
void runStateMachine();
void valueAssignment();
void readInputs();
void setup();

// internal params.
system_state_t currentState = IDLE;
// system_state_t prevState = IDLE;

// inputs
int8_t button_state; // active low

// outputs
int8_t led_state = 0; // active high


void app_main(void)
{
    setup();
    while(1){
        readInputs();
        runStateMachine();
        valueAssignment();
        vTaskDelay(pdMS_TO_TICKS(10)); // allow the freertos scheduler to switch to run the task IDLE0 which feeds the watchdog timer.
    }                                                
}


void setup(){
    // led setup
    gpio_reset_pin(LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
    

    // button setup
    gpio_reset_pin(BUTTON_PIN);
    gpio_set_direction(BUTTON_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(BUTTON_PIN, GPIO_PULLUP_ONLY);
}

void readInputs(){
    button_state = gpio_get_level(BUTTON_PIN);
}

// verilog-like default vals style.
void valueAssignment(){
    // assign led to led_state
    gpio_set_level(LED_PIN, led_state);

}


void runStateMachine() {
    // assign defaults here.
    switch (currentState) {
        case IDLE:
            led_state = 0;
            if (button_state == 0){
                currentState = SCANNING;
            }
            break;
            
        case SCANNING:
            led_state = 1;
            if (button_state == 1){
                currentState = IDLE;
            }
            break;
        default:
            break;
    }
}