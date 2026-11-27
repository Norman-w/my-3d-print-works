#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include "esp_netif.h"

void wifi_init_softap_and_sta(void);
void start_wifi_connect_task(const char* ssid, const char* password);
void wifi_manager_auto_connect_saved(void);
esp_netif_ip_info_t wifi_manager_get_sta_ip_info();
void wifi_manager_query_dhcp_status(void);

#endif // WIFI_MANAGER_H 