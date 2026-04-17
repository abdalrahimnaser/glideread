#include <stdio.h>
#include <string.h>
#include "driver/gpio.h"
#include "hal/gpio_types.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "wifi_provisioner.h"
#include "server.h"
#include "esp_camera.h"

// define before including camera_pins.h
#define CAMERA_MODEL_XIAO_ESP32S3
#include "camera_pins.h"
#include "ESP32_OV5640_cfg.h"
#define REG_VCM_CONTROL_0  0x3602
#define REG_VCM_CONTROL_1  0x3603

#define BUTTON_PIN 1
#define LED_PIN    2

static const char *TAG = "main";

// Debounce: require N consecutive samples before accepting a change.
// With the current loop delay of ~10ms, 3 ticks ~= 30ms debounce.
#define DEBOUNCE_TICKS 3


void runStateMachine();
void valueAssignment();
void readInputs();
void setup();

// defintions (move to .h)
typedef enum {
    IDLE, 
    SCANNING, 
    } system_state_t; // as far as i know this copiles into an int, if u want that explicitly a different type like uint8_t, u can use special syntax that does it.??

// internal params.
system_state_t currentState = IDLE;
// system_state_t prevState = IDLE;

// inputs
int8_t button_state; // active low
int8_t prev_button_state = 1; // assume released at boot (pull-up)

// outputs
int8_t led_state = 0; // active high




sensor_t * s;

uint16_t focus = 0;

int set_focus(sensor_t *s, uint16_t vcm_value)
{
  // Set DAC bits 3:0 into reg bits 7:4
  s->set_reg(s, REG_VCM_CONTROL_0, 0xF0, vcm_value << 4);
  // Set DAC bits 9:4 into reg bits 5:0
  s->set_reg(s, REG_VCM_CONTROL_1, 0x3F, vcm_value >> 4);
  focus = vcm_value;
  return 0;
}

uint8_t focusInit(sensor_t *sensor) {
  uint16_t i;
  uint16_t addr = 0x8000;
  uint8_t state = 0x8F;
  uint8_t rc = 0;
  rc = sensor->set_reg(sensor, 0x3000, 0xff, 0x20);  //reset
  if (rc < 0) return -1;

  for (i = 0; i < sizeof(OV5640_AF_Config); i++) {
    rc = sensor->set_reg(sensor, addr, 0xff, OV5640_AF_Config[i]);
    if (rc < 0) return -1;

    addr++;
  }

  sensor->set_reg(sensor, OV5640_CMD_MAIN, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_ACK, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_PARA0, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_PARA1, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_PARA2, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_PARA3, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_PARA4, 0xff, 0x00);
  sensor->set_reg(sensor, OV5640_CMD_FW_STATUS, 0xff, 0x7f);
  sensor->set_reg(sensor, 0x3000, 0xff, 0x00);

  i = 0;
  do {
    state = sensor->get_reg(sensor, 0x3029, 0xff);
    vTaskDelay(pdMS_TO_TICKS(5));
    i++;
    if (i > 1000) return 1;
  } while (state != FW_STATUS_S_IDLE);

  return 0;
}

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
    // camera setup (defined in camera_server.c)
    camera_config_t cfg = {
        .ledc_channel = LEDC_CHANNEL_0,
        .ledc_timer = LEDC_TIMER_0,

        .pin_d0 = Y2_GPIO_NUM,
        .pin_d1 = Y3_GPIO_NUM,
        .pin_d2 = Y4_GPIO_NUM,
        .pin_d3 = Y5_GPIO_NUM,
        .pin_d4 = Y6_GPIO_NUM,
        .pin_d5 = Y7_GPIO_NUM,
        .pin_d6 = Y8_GPIO_NUM,
        .pin_d7 = Y9_GPIO_NUM,

        .pin_xclk = XCLK_GPIO_NUM,
        .pin_pclk = PCLK_GPIO_NUM,
        .pin_vsync = VSYNC_GPIO_NUM,
        .pin_href = HREF_GPIO_NUM,
        .pin_sscb_sda = SIOD_GPIO_NUM,
        .pin_sscb_scl = SIOC_GPIO_NUM,
        .pin_pwdn = PWDN_GPIO_NUM,
        .pin_reset = RESET_GPIO_NUM,

        .xclk_freq_hz = 20000000,
        .pixel_format = PIXFORMAT_JPEG,

        // Simple defaults for streaming; override later.
        .frame_size = FRAMESIZE_240X240,
        .jpeg_quality = 12,
        .fb_count = 2,
        .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
        .fb_location = CAMERA_FB_IN_PSRAM,
    };
    esp_camera_init(&cfg);

    s = esp_camera_sensor_get();
    if (s->id.PID == OV5640_PID) {
        focusInit(s);
        set_focus(s,1023);
    }


    // led setup
    gpio_reset_pin(LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
    
    // button setup
    gpio_reset_pin(BUTTON_PIN);
    gpio_set_direction(BUTTON_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(BUTTON_PIN, GPIO_PULLUP_ONLY);



    // wifi setup - more details @ https://github.com/MichMich/esp-idf-wifi-provisioner
    wifi_prov_config_t config = WIFI_PROV_DEFAULT_CONFIG();
    config.ap_ssid = "MyDevice-Setup";
    ESP_ERROR_CHECK(wifi_prov_start(&config));
    wifi_prov_wait_for_connection(portMAX_DELAY); // this is to wait till connection happens ... blocks the whole excution if wasn't successful, maybe think of a better way
    

    // http server setup (camera streaming + comms w/ PC)
    run_server(); // do u not need to specify like the thread for this to keep running or so?

}

void readInputs(){
    static int8_t stable_level = 1;      // start released (pull-up)
    static int8_t last_raw_level = 1;
    static uint8_t change_count = 0;

    int8_t raw_level = gpio_get_level(BUTTON_PIN);

    if (raw_level == last_raw_level) {
        // raw input is stable this tick
        if (raw_level != stable_level) {
            if (change_count < DEBOUNCE_TICKS) {
                change_count++;
            }
            if (change_count >= DEBOUNCE_TICKS) {
                stable_level = raw_level;
                change_count = 0;
            }
        } else {
            change_count = 0;
        }
    } else {
        // raw input bounced; restart counting with new raw level
        last_raw_level = raw_level;
        change_count = 0;
    }

    button_state = stable_level; // debounced, active-low
    server_set_button_pressed(button_state == 0);
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
                // send the trigger here
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

    // Detect press edge (released->pressed) as a debug/event counter.
    if (prev_button_state == 1 && button_state == 0) {
        server_trigger_increment();
        ESP_LOGI(TAG, "Button pressed");
    }
    if (prev_button_state == 0 && button_state == 1) {
        ESP_LOGI(TAG, "Button released");
    }
    prev_button_state = button_state;
}