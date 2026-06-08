#ifndef DEVICE_STORAGE_H
#define DEVICE_STORAGE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void device_storage_set_connection_info(const char *ssid, const char *password, const char *device_id);
void device_storage_clear_all(void);

#ifdef __cplusplus
}

// C++ only functions
#include <string>
void device_storage_get_connection_info(std::string &ssid, std::string &password, std::string &device_id);

#endif

#endif // DEVICE_STORAGE_H
