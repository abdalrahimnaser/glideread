#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include <inttypes.h>
#include <stdatomic.h>
#include "lwip/inet.h"
#include "server.h"


static const char *TAG = "http_server";

// Debug counter incremented on each press edge.
static atomic_uint_least32_t s_trigger_counter = 0;
// Current logical button state (1=pressed, 0=released).
static atomic_uchar s_button_pressed = 0;

static httpd_handle_t s_stream_server = NULL;
static httpd_handle_t s_ctrl_server = NULL;

// -----------------------------
// Minimal MJPEG camera streaming
// -----------------------------

static const char *STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char *STREAM_BOUNDARY = "\r\n--frame\r\n";
static const char *STREAM_PART_HEADER = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t root_get_handler(httpd_req_t *req)
{
    const char *resp =
        "ok\n"
        "GET /stream for MJPEG\n"
        "GET /scan_state for button state\n"
        "Note: /scan_state served on port 81\n";
    httpd_resp_set_type(req, "text/plain");
    return httpd_resp_send(req, resp, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t scan_state_get_handler(httpd_req_t *req)
{
    uint32_t counter = (uint32_t)atomic_load(&s_trigger_counter);
    uint8_t pressed = (uint8_t)atomic_load(&s_button_pressed);

    char resp[128];
    int n = snprintf(resp, sizeof(resp),
                     "{\"trigger_counter\":%" PRIu32 ",\"button_pressed\":%s}\n",
                     counter,
                     pressed ? "true" : "false");
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, resp, n);
}

static esp_err_t stream_get_handler(httpd_req_t *req)
{
    esp_err_t res = ESP_OK;
    char part_buf[128];

    res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    while (true) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            ESP_LOGW(TAG, "esp_camera_fb_get() failed");
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        if (fb->format != PIXFORMAT_JPEG) {
            // With our config this should not happen; keep it simple.
            ESP_LOGW(TAG, "Non-JPEG frame (%d), dropping", fb->format);
            esp_camera_fb_return(fb);
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        if (res == ESP_OK) {
            int hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART_HEADER, (unsigned)fb->len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        }

        esp_camera_fb_return(fb);

        if (res != ESP_OK) {
            break; // client disconnected or socket error
        }
    }

    // Close out the chunked response.
    httpd_resp_send_chunk(req, NULL, 0);
    return res;
}

static esp_err_t httpd_start_stream_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;

    esp_err_t err = httpd_start(&s_stream_server, &config);
    if (err != ESP_OK) {
        return err;
    }

    httpd_uri_t uri_root = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = root_get_handler,
        .user_ctx = NULL,
    };
    httpd_register_uri_handler(s_stream_server, &uri_root);

    httpd_uri_t uri_stream = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_get_handler,
        .user_ctx = NULL,
    };
    httpd_register_uri_handler(s_stream_server, &uri_stream);

    return ESP_OK;
}

static esp_err_t httpd_start_ctrl_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 81;
    // Each server must have a unique ctrl_port; otherwise the 2nd server fails to bind it.
    config.ctrl_port = config.ctrl_port + 1;

    esp_err_t err = httpd_start(&s_ctrl_server, &config);
    if (err != ESP_OK) {
        return err;
    }

    httpd_uri_t uri_scan_state = {
        .uri = "/scan_state",
        .method = HTTP_GET,
        .handler = scan_state_get_handler,
        .user_ctx = NULL,
    };
    httpd_register_uri_handler(s_ctrl_server, &uri_scan_state);

    return ESP_OK;
}



static void log_sta_ip(void)
{
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (!netif) {
        ESP_LOGW(TAG, "No WIFI_STA_DEF netif handle yet");
        return;
    }

    esp_netif_ip_info_t ip;
    if (esp_netif_get_ip_info(netif, &ip) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to get STA IP info");
        return;
    }

    ESP_LOGI(TAG, "STA IP: " IPSTR, IP2STR(&ip.ip));
    ESP_LOGI(TAG, "Stream URL: http://" IPSTR "/stream", IP2STR(&ip.ip));
    ESP_LOGI(TAG, "Scan state URL: http://" IPSTR ":81/scan_state", IP2STR(&ip.ip));
}


void run_server(void){
    ESP_ERROR_CHECK(httpd_start_stream_server());
    esp_err_t err = httpd_start_ctrl_server();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Control server failed to start (err=0x%x). /scan_state will be unavailable.", (unsigned)err);
    }
    log_sta_ip();
}

void server_trigger_increment(void)
{
    (void)atomic_fetch_add(&s_trigger_counter, 1);
}

uint32_t server_trigger_get(void)
{
    return (uint32_t)atomic_load(&s_trigger_counter);
}

void server_set_button_pressed(uint8_t pressed)
{
    atomic_store(&s_button_pressed, (unsigned char)(pressed ? 1 : 0));
}

uint8_t server_get_button_pressed(void)
{
    return (uint8_t)atomic_load(&s_button_pressed);
}