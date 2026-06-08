//
// 连接 API 处理器 — SmartPaddle
//

#include "connection_api_handlers.h"
#include "esp_log.h"
#include "esp_http_server.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_wifi_types.h"
#include <string>
#include "../utils.h"
#include "../wifi_manager.h"
#include "../device_storage.h"
#include "../const.h"

static const char *TAG = LOG_TAG_HTTP_HANDLERS;

extern "C" {
    extern char device_id[32];
    extern bool is_sta_connected;
    extern bool is_sta_connecting;
}


// ===== POST /login — 接收配网表单 =====
static esp_err_t login_post_handler(httpd_req_t *req) {
    extern const uint8_t connecting_page_html_start[] asm("_binary_connecting_page_html_start");
    extern const uint8_t connecting_page_html_end[] asm("_binary_connecting_page_html_end");

    char buf[200];
    const int remaining = req->content_len;

    if (remaining > (int)sizeof(buf)) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "请求内容过长");
        return ESP_FAIL;
    }

    const int ret = httpd_req_recv(req, buf, remaining);
    if (ret <= 0) {
        if (ret == HTTPD_SOCK_ERR_TIMEOUT) {
            httpd_resp_send_408(req);
        }
        return ESP_FAIL;
    }
    buf[ret] = 0;

    char ssid[32] = {0};
    char password[64] = {0};

    ESP_LOGI(TAG, "收到连接请求, 请求内容: %s", buf);

    if (httpd_query_key_value(buf, "ssid", ssid, sizeof(ssid)) != ESP_OK ||
        httpd_query_key_value(buf, "device_id", device_id, sizeof(device_id)) != ESP_OK) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "缺少 SSID 或主机名");
        return ESP_FAIL;
    }
    httpd_query_key_value(buf, "password", password, sizeof(password));

    ESP_LOGI(TAG, "收到连接请求: SSID:[%s], device_id:[%s]", ssid, device_id);

    device_storage_set_connection_info(ssid, password, device_id);

    // 发送 connecting 页面（连接任务由前端页面加载后触发）
    const size_t connecting_page_size = connecting_page_html_end - connecting_page_html_start;
    std::string connecting_page_content(reinterpret_cast<const char *>(connecting_page_html_start), connecting_page_size);
    replace_placeholder(connecting_page_content, "{{SSID}}", ssid);
    replace_placeholder(connecting_page_content, "{{DEVICE_ID}}", device_id);
    const auto connecting_page_buffer = static_cast<char *>(malloc(connecting_page_content.length() + 1));
    if (!connecting_page_buffer) {
        ESP_LOGE(TAG, "无法为连接页面分配内存");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    memcpy(connecting_page_buffer, connecting_page_content.c_str(), connecting_page_content.length());

    httpd_resp_send(req, connecting_page_buffer, HTTPD_RESP_USE_STRLEN);
    free(connecting_page_buffer);

    return ESP_OK;
}

// ===== GET /status — 连接状态 =====
static esp_err_t status_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    const auto ip = wifi_manager_get_sta_ip_info();
    char ip_str[16];
    esp_ip4addr_ntoa(&ip.ip, ip_str, sizeof(ip_str));

    const char *resp_str;
    if (is_sta_connected) {
        const std::string response = R"({"status": "ok", "device_id": ")" + std::string(device_id) +
                               R"(", "ip_address": ")" + std::string(ip_str) + R"("})";
        resp_str = strdup(response.c_str());
    } else {
        resp_str = R"({"status": "connecting"})";
    }
    httpd_resp_send(req, resp_str, strlen(resp_str));
    if (resp_str) free((void*)resp_str);
    return ESP_OK;
}

// ===== GET /dhcp_status — DHCP 详细状态 =====
static esp_err_t dhcp_status_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    wifi_manager_query_dhcp_status();

    const auto ip = wifi_manager_get_sta_ip_info();
    char ip_str[16] = {0};
    char netmask_str[16] = {0};
    char gw_str[16] = {0};

    if (ip.ip.addr != 0) {
        esp_ip4addr_ntoa(&ip.ip, ip_str, sizeof(ip_str));
        esp_ip4addr_ntoa(&ip.netmask, netmask_str, sizeof(netmask_str));
        esp_ip4addr_ntoa(&ip.gw, gw_str, sizeof(gw_str));
    }

    wifi_ap_record_t ap_info = {0};
    int rssi = 0;
    bool wifi_connected = false;

    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        wifi_connected = true;
        esp_wifi_sta_get_rssi(&rssi);
    }

    std::string response = R"({
        "wifi_connected": )" + std::to_string(wifi_connected) + R"(,
        "ssid": ")" + (wifi_connected ? std::string((char*)ap_info.ssid) : "") + R"(",
        "rssi": )" + std::to_string(rssi) + R"(,
        "ip_address": ")" + std::string(ip_str) + R"(",
        "netmask": ")" + std::string(netmask_str) + R"(",
        "gateway": ")" + std::string(gw_str) + R"(",
        "has_valid_ip": )" + std::to_string(ip.ip.addr != 0) + R"(
    })";

    httpd_resp_send(req, response.c_str(), response.length());
    return ESP_OK;
}

// ===== GET /try_connect_to_ap — 触发重连 =====
static esp_err_t try_connect_to_ap_handler(httpd_req_t *req) {
    if (is_sta_connected) {
        ESP_LOGI(TAG, "已连接到 AP，无法重新连接");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Already connected to AP");
        return ESP_FAIL;
    }

    std::string ssid, password, device_id_str;
    device_storage_get_connection_info(ssid, password, device_id_str);

    if (ssid.empty() || password.empty()) {
        ESP_LOGE(TAG, "没有存储的连接信息");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "No stored connection info");
        return ESP_FAIL;
    }
    if (is_sta_connecting) {
        ESP_LOGW(TAG, "正在连接中，无法重新连接");
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Already connecting");
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, R"({"status": "ok"})", HTTPD_RESP_USE_STRLEN);

    vTaskDelay(pdMS_TO_TICKS(500));
    start_wifi_connect_task(ssid.c_str(), password.c_str());
    return ESP_OK;
}

// ===== POST /sta_result_checking_page_loaded — 前端页面加载完成，触发连接 =====
static esp_err_t sta_result_checking_page_loaded_handler(httpd_req_t *req) {
    std::string ssid, password, device_id_str;
    device_storage_get_connection_info(ssid, password, device_id_str);

    if (ssid.empty() || password.empty()) {
        ESP_LOGW(TAG, "没有存储的连接信息，忽略 page_loaded 请求");
        httpd_resp_set_status(req, "204 No Content");
        return httpd_resp_send(req, NULL, 0);
    }

    if (is_sta_connected) {
        ESP_LOGI(TAG, "已连接到 STA，忽略 page_loaded 请求");
        httpd_resp_set_status(req, "204 No Content");
        return httpd_resp_send(req, NULL, 0);
    }

    if (is_sta_connecting) {
        ESP_LOGI(TAG, "正在连接中，忽略 page_loaded 请求");
        httpd_resp_set_status(req, "204 No Content");
        return httpd_resp_send(req, NULL, 0);
    }

    is_sta_connecting = true;
    start_wifi_connect_task(ssid.c_str(), password.c_str());

    httpd_resp_set_status(req, "204 No Content");
    return httpd_resp_send(req, NULL, 0);
}

// ===== URI 定义 =====
static const httpd_uri_t login_uri = {
    .uri = "/login",
    .method = HTTP_POST,
    .handler = login_post_handler,
    .user_ctx = nullptr,
};

static const httpd_uri_t status_uri = {
    .uri = "/status",
    .method = HTTP_GET,
    .handler = status_get_handler,
    .user_ctx = nullptr,
};

static const httpd_uri_t try_connect_to_ap_uri = {
    .uri = "/try_connect_to_ap",
    .method = HTTP_GET,
    .handler = try_connect_to_ap_handler,
    .user_ctx = nullptr,
};

static const httpd_uri_t sta_result_checking_page_loaded_uri = {
    .uri = "/sta_result_checking_page_loaded",
    .method = HTTP_POST,
    .handler = sta_result_checking_page_loaded_handler,
    .user_ctx = nullptr,
};

static const httpd_uri_t dhcp_status_uri = {
    .uri = "/dhcp_status",
    .method = HTTP_GET,
    .handler = dhcp_status_get_handler,
    .user_ctx = nullptr,
};

esp_err_t register_connection_api_handlers(httpd_handle_t server) {
    esp_err_t ret = ESP_OK;
    ret = httpd_register_uri_handler(server, &login_uri);          if (ret != ESP_OK) return ret;
    ret = httpd_register_uri_handler(server, &status_uri);         if (ret != ESP_OK) return ret;
    ret = httpd_register_uri_handler(server, &try_connect_to_ap_uri); if (ret != ESP_OK) return ret;
    ret = httpd_register_uri_handler(server, &sta_result_checking_page_loaded_uri); if (ret != ESP_OK) return ret;
    ret = httpd_register_uri_handler(server, &dhcp_status_uri);    if (ret != ESP_OK) return ret;
    return ret;
}
