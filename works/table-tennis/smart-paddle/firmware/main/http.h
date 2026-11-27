//
// Created by Norman Wang on 2025/12/31.
//

#ifndef HTTP_H
#define HTTP_H

#include "esp_err.h"
#include "esp_http_server.h"

esp_err_t register_all_http_handlers(httpd_handle_t server);


#endif //HTTP_H
