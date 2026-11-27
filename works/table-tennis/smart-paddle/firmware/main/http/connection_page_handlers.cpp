//
// Captive Portal 页面处理器 — SmartPaddle
//

#include "connection_page_handlers.h"
#include "esp_log.h"
#include "esp_http_server.h"
#include "esp_netif.h"
#include "esp_system.h"
#include <string>
#include "../utils.h"
#include "../wifi_manager.h"
#include "../const.h"

static const char *TAG = LOG_TAG_HTTP_HANDLERS;

extern char device_id[32];
extern bool is_sta_connected;
extern bool is_sta_connecting;

// 嵌入式 HTML 资源声明
extern const uint8_t connect_page_html_start[] asm("_binary_connect_page_html_start");
extern const uint8_t connect_page_html_end[] asm("_binary_connect_page_html_end");
extern const uint8_t connecting_page_html_start[] asm("_binary_connecting_page_html_start");
extern const uint8_t connecting_page_html_end[] asm("_binary_connecting_page_html_end");
extern const uint8_t connected_page_html_start[] asm("_binary_connected_page_html_start");
extern const uint8_t connected_page_html_end[] asm("_binary_connected_page_html_end");


static bool show_connected_page(httpd_req_t *req, esp_err_t &value) {
    esp_netif_ip_info_t ip_info = wifi_manager_get_sta_ip_info();
    if (ip_info.ip.addr != 0) {
        char ip_str[16];
        esp_ip4addr_ntoa(&ip_info.ip, ip_str, sizeof(ip_str));

        const size_t connected_page_size = connected_page_html_end - connected_page_html_start;
        const auto page_buffer = static_cast<char *>(malloc(connected_page_size + 1));
        if (!page_buffer) {
            ESP_LOGE(TAG, "无法为状态页面分配内存");
            httpd_resp_send_500(req);
            value = ESP_FAIL;
            return true;
        }
        memcpy(page_buffer, connected_page_html_start, connected_page_size);
        page_buffer[connected_page_size] = '\0';

        std::string page_content(page_buffer);
        replace_placeholder(page_content, "{{DEVICE_ID}}", device_id);
        replace_placeholder(page_content, "{{IP_ADDRESS}}", ip_str);
        replace_placeholder(page_content, "{{WIFI_STATUS}}", "已连接");

        httpd_resp_set_type(req, "text/html; charset=UTF-8");
        httpd_resp_send(req, page_content.c_str(), HTTPD_RESP_USE_STRLEN);
        free(page_buffer);
        value = ESP_OK;
        ESP_LOGI(TAG, "已连接到 AP, IP 地址: %s", ip_str);
        return true;
    }
    return false;
}

static void show_connect_page(httpd_req_t *req, esp_err_t &value) {
    const size_t connect_page_size = connect_page_html_end - connect_page_html_start;
    const auto page_buffer = static_cast<char *>(malloc(connect_page_size + 1));
    if (!page_buffer) {
        ESP_LOGE(TAG, "无法为连接页面分配内存");
        httpd_resp_send_500(req);
        value = ESP_FAIL;
        return;
    }

    std::string html_content(reinterpret_cast<const char *>(connect_page_html_start), connect_page_size);
    replace_placeholder(html_content, "{{DEVICE_ID}}", device_id);
    memcpy(page_buffer, html_content.c_str(), html_content.length());
    page_buffer[html_content.length()] = '\0';

    httpd_resp_set_type(req, "text/html; charset=UTF-8");
    httpd_resp_send(req, page_buffer, HTTPD_RESP_USE_STRLEN);
    free(page_buffer);
    value = ESP_OK;
}

// Captive Portal 通配符处理器
esp_err_t captive_portal_get_handler(httpd_req_t *req) {
    if (is_sta_connected) {
        if (esp_err_t value; show_connected_page(req, value)) return value;
    } else if (!is_sta_connecting) {
        esp_err_t value;
        show_connect_page(req, value);
        return value;
    }
    return ESP_OK;
}

static const httpd_uri_t captive_portal_uri = {
    .uri = "/*",
    .method = HTTP_GET,
    .handler = captive_portal_get_handler,
    .user_ctx = nullptr,
};

esp_err_t register_connection_page_handlers(httpd_handle_t server) {
    return httpd_register_uri_handler(server, &captive_portal_uri);
}
