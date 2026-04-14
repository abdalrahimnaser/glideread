#ifndef __SERVER_H__
#define __SERVER_H__

#include <stdint.h>

void run_server(void);
void server_trigger_increment(void);
uint32_t server_trigger_get(void);
void server_set_button_pressed(uint8_t pressed);
uint8_t server_get_button_pressed(void);

#endif