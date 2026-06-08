//
// Created by Norman Wang on 2025/12/30.
//

#ifndef CONNECTION_PAGE_HANDLERS_H
#define CONNECTION_PAGE_HANDLERS_H


#include "esp_http_server.h"

#ifdef __cplusplus
extern "C" {
#endif

    // 为 Web 服务器注册所有 HTTP
    esp_err_t register_connection_page_handlers(httpd_handle_t server);

#ifdef __cplusplus
}
#endif


#endif //CONNECTION_PAGE_HANDLERS_H
