#include "esp_camera.h"
#include <WiFi.h>

#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM

#include "ESP32_OV5640_cfg.h"
#include "camera_pins.h"

// ===========================
// Enter your WiFi credentials
// ===========================
const char* ssid = "Galaxy S22+9414";
const char* password = "ajxg6831";

// const char* ssid = "North Block";
// const char* password = "367tgb#NB";


void startCameraServer();
void setupLedFlash(int pin);

#define REG_VCM_CONTROL_0  0x3602
#define REG_VCM_CONTROL_1  0x3603


sensor_t * s;

uint16_t focus = 0;

int set_focus(sensor_t *s, uint16_t vcm_value)
{
  // Set DAC bits 3:0 into reg bits 7:4
  s->set_reg(s, REG_VCM_CONTROL_0, 0xF0, vcm_value << 4);
  // Set DAC bits 9:4 into reg bits 5:0
  s->set_reg(s, REG_VCM_CONTROL_1, 0x3F, vcm_value >> 4);
  focus = vcm_value;
  Serial.println((std::string("Focus set to ") + std::to_string(focus)).c_str());
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
    delay(5);
    i++;
    if (i > 1000) return 1;
  } while (state != FW_STATUS_S_IDLE);

  return 0;
}

void setup() {
  Serial.begin(115200);
  while(!Serial);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG; // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if(config.pixel_format == PIXFORMAT_JPEG){
    if(psramFound()){
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  s = esp_camera_sensor_get();

  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }

  // drop down frame size for higher initial frame rate
  if(config.pixel_format == PIXFORMAT_JPEG){
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

  if (s->id.PID == OV5640_PID) {
    focusInit(s);
    set_focus(s,1023);
  }

  delay(5000);

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println(WiFi.status());
    // Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
  Serial.println("enter the camera focus value");


}

void loop() {


  // Do nothing. Everything is done in another task by the web server
  if (Serial.available() > 0) {
    // Read the input until a newline character
    String input = Serial.readStringUntil('\n');
    input.trim(); // Remove any stray spaces or carriage returns

    if (input.length() > 0) {
      int val = input.toInt(); // Convert string to integer
      
      // Constrain value to the 10-bit range (0-1023)
      if (val >= 0 && val <= 1023) {

        if (set_focus(s, (uint16_t)val)!=0){Serial.println("error in writing to regs");}
      } else {
        Serial.println("Invalid range! Please enter a value between 0 and 1023.");
      }
    }
  }

}