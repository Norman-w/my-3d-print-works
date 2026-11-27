#include "wifi_manager.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "device_storage.h"
#include "mdns.h"
#include "const.h"

// ===== 全局状态（extern 自 main.cpp） =====
extern "C" {
    extern char device_id[32];
    extern bool is_sta_connected;
    extern bool is_sta_connecting;
    extern bool is_connection_error;
}

static const char *TAG = LOG_TAG_WIFI_MANAGER;

// ===== 默认 SoftAP 配置 =====
#define AP_SSID_DEFAULT      CONFIG_ESP_WIFI_SSID
#define AP_PASS_DEFAULT      CONFIG_ESP_WIFI_PASSWORD
#define AP_CHANNEL_DEFAULT   CONFIG_ESP_WIFI_CHANNEL
#define AP_MAX_STA_CONN      CONFIG_ESP_MAX_STA_CONN

#define MAX_WIFI_RETRY_COUNT       5
static int s_retry_count = 0;

// ===== mDNS 服务 =====
void start_mdns_service() {
    if (const esp_err_t err = mdns_init()) {
        ESP_LOGE(TAG, "mDNS 初始化失败: %s", esp_err_to_name(err));
        return;
    }

    // 如果没有设置 device_id，使用 MAC 后缀生成
    if (device_id[0] == '\0') {
        uint8_t mac[6];
        esp_read_mac(mac, ESP_MAC_WIFI_STA);
        snprintf(device_id, sizeof(device_id), "SP-%02X%02X", mac[4], mac[5]);
        ESP_LOGI(TAG, "生成默认设备ID: %s", device_id);
    }

    esp_err_t ret = mdns_hostname_set(device_id);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "mDNS 主机名设置失败: %s", esp_err_to_name(ret));
    }

    mdns_instance_name_set("SmartPaddle");
    ESP_LOGI(TAG, "mDNS 服务已启动, 主机名: %s.local", device_id);
}

// ===== 重连任务参数结构 =====
typedef struct {
    char ssid[32];
    char password[64];
} wifi_connect_task_params_t;

// ===== 延迟重连任务 =====
static void wifi_retry_connect_task(void *pvParameters) {
    wifi_connect_task_params_t *params = (wifi_connect_task_params_t *)pvParameters;

    uint32_t delay_ms = 1000 + (s_retry_count * 500);
    ESP_LOGI(TAG, "重连任务等待 %lu ms 后重试...", delay_ms);
    vTaskDelay(pdMS_TO_TICKS(delay_ms));

    is_connection_error = false;
    is_sta_connecting = true;
    is_sta_connected = false;

    ESP_LOGI(TAG, "执行重连到 %s", params->ssid);
    esp_err_t ret = esp_wifi_connect();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "重连调用失败: %s", esp_err_to_name(ret));
    }

    free(params);
    vTaskDelete(NULL);
}

// ===== STA 连接任务 =====
static void wifi_sta_connect_task(void *pvParameters) {
    wifi_connect_task_params_t *params = (wifi_connect_task_params_t *)pvParameters;
    s_retry_count = 0;

    ESP_LOGI(TAG, "开始 STA 连接流程: %s", params->ssid);

    // 确保 WiFi 模式为 APSTA
    wifi_mode_t current_mode;
    esp_wifi_get_mode(&current_mode);

    if (current_mode != WIFI_MODE_APSTA) {
        ESP_LOGI(TAG, "设置 WiFi 模式为 APSTA...");
        esp_wifi_set_mode(WIFI_MODE_APSTA);
        vTaskDelay(pdMS_TO_TICKS(300));
    }

    // 配置 STA
    wifi_config_t wifi_config;
    memset(&wifi_config, 0, sizeof(wifi_config_t));
    strcpy((char *)wifi_config.sta.ssid, params->ssid);
    strcpy((char *)wifi_config.sta.password, params->password);
    wifi_config.sta.scan_method = WIFI_FAST_SCAN;
    wifi_config.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;
    wifi_config.sta.threshold.rssi = -127;
    wifi_config.sta.threshold.authmode = WIFI_AUTH_OPEN;

    ESP_LOGI(TAG, "配置 STA 连接参数 - SSID: '%s'", params->ssid);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);

    ESP_LOGI(TAG, "开始连接到 %s...", params->ssid);
    esp_err_t conn_err = esp_wifi_connect();
    if (conn_err != ESP_OK) {
        ESP_LOGE(TAG, "连接 WiFi 失败，错误码: 0x%x (%s)", conn_err, esp_err_to_name(conn_err));
        is_sta_connecting = false;
        vTaskDelay(pdMS_TO_TICKS(5000));
    }

    free(params);
    vTaskDelete(NULL);
}

// ===== 自动连接已保存的 WiFi =====
void wifi_manager_auto_connect_saved(void) {
    std::string ssid, password, device_id_str;
    device_storage_get_connection_info(ssid, password, device_id_str);

    if (ssid.empty()) {
        ESP_LOGI(TAG, "没有找到保存的 WiFi 配置，保持 AP 模式");
        return;
    }

    ESP_LOGI(TAG, "找到保存的 WiFi 配置 - SSID: '%s'", ssid.c_str());

    if (!device_id_str.empty()) {
        strncpy(device_id, device_id_str.c_str(), sizeof(device_id) - 1);
    }

    start_wifi_connect_task(ssid.c_str(), password.c_str());
}

// ===== 启动 WiFi 连接任务 =====
void start_wifi_connect_task(const char* ssid, const char* password) {
    is_connection_error = false;
    is_sta_connecting = true;
    is_sta_connected = false;

    wifi_connect_task_params_t *task_params = (wifi_connect_task_params_t *)malloc(sizeof(wifi_connect_task_params_t));
    if (task_params) {
        strcpy(task_params->ssid, ssid);
        strcpy(task_params->password, password);
        ESP_LOGI(TAG, "创建 WiFi 连接任务: %s", ssid);
        xTaskCreate(wifi_sta_connect_task, "wifi_connect_task", 4096, task_params, 5, NULL);
    } else {
        ESP_LOGE(TAG, "分配 WiFi 连接任务内存失败");
        is_sta_connecting = false;
    }
}

// ===== WiFi 事件处理器 =====
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data) {
    if (event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t* event = (wifi_event_ap_staconnected_t*) event_data;
        ESP_LOGI(TAG, "站点 " MACSTR " 加入, AID=%d", MAC2STR(event->mac), event->aid);
    } else if (event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t* event = (wifi_event_ap_stadisconnected_t*) event_data;
        ESP_LOGI(TAG, "站点 " MACSTR " 离开, AID=%d", MAC2STR(event->mac), event->aid);
    } else if (event_id == WIFI_EVENT_AP_START) {
        ESP_LOGI(TAG, "SoftAP 已启动");
    } else if (event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "STA 模式启动");
    } else if (event_id == WIFI_EVENT_STA_CONNECTED) {
        wifi_event_sta_connected_t* event = (wifi_event_sta_connected_t*) event_data;
        ESP_LOGI(TAG, "STA 连接成功, SSID: %s, 频道: %d", event->ssid, event->channel);
        wifi_manager_query_dhcp_status();
    } else if (event_id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t* event = (wifi_event_sta_disconnected_t*) event_data;
        ESP_LOGW(TAG, "STA 断开连接, 原因: %d, 重试次数: %d/%d",
                 event->reason, s_retry_count, MAX_WIFI_RETRY_COUNT);
        is_sta_connected = false;
        is_sta_connecting = false;

        if (s_retry_count < MAX_WIFI_RETRY_COUNT && event->reason != WIFI_REASON_ASSOC_LEAVE) {
            s_retry_count++;
            ESP_LOGI(TAG, "发起重连 (第%d次)...", s_retry_count);

            wifi_connect_task_params_t *retry_params = (wifi_connect_task_params_t*)malloc(sizeof(wifi_connect_task_params_t));
            if (retry_params) {
                wifi_config_t current_config;
                if (esp_wifi_get_config(WIFI_IF_STA, &current_config) == ESP_OK) {
                    strcpy(retry_params->ssid, (char*)current_config.sta.ssid);
                    strcpy(retry_params->password, (char*)current_config.sta.password);
                    xTaskCreate(wifi_retry_connect_task, "wifi_retry_task", 4096, retry_params, 4, NULL);
                } else {
                    free(retry_params);
                }
            }
        } else if (s_retry_count >= MAX_WIFI_RETRY_COUNT) {
            ESP_LOGE(TAG, "WiFi 连接失败，已达到最大重试次数 (%d)", MAX_WIFI_RETRY_COUNT);
            is_connection_error = true;
        } else {
            ESP_LOGI(TAG, "WiFi 断开连接 (手动断开，不重连)");
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;

        ESP_LOGI(TAG, "========================================");
        ESP_LOGI(TAG, "        DHCP IP 获取成功!");
        ESP_LOGI(TAG, "========================================");
        ESP_LOGI(TAG, "IP地址: " IPSTR, IP2STR(&event->ip_info.ip));
        ESP_LOGI(TAG, "子网掩码: " IPSTR, IP2STR(&event->ip_info.netmask));
        ESP_LOGI(TAG, "网关: " IPSTR, IP2STR(&event->ip_info.gw));
        ESP_LOGI(TAG, "========================================");

        is_sta_connected = true;
        is_sta_connecting = false;
        is_connection_error = false;
        s_retry_count = 0;

        start_mdns_service();

        // 保存当前连接的 WiFi 凭据
        wifi_config_t wifi_config;
        if (esp_wifi_get_config(WIFI_IF_STA, &wifi_config) == ESP_OK) {
            device_storage_set_connection_info((char*)wifi_config.sta.ssid,
                                               (char*)wifi_config.sta.password,
                                               device_id);
        }
    }
}

// ===== 初始化 SoftAP + STA 双模 WiFi =====
void wifi_init_softap_and_sta(void) {
    // 初始化 netif
    esp_netif_create_default_wifi_ap();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL, NULL));

    // 配置 SoftAP
    wifi_config_t wifi_config;
    memset(&wifi_config, 0, sizeof(wifi_config_t));

    strlcpy((char*)wifi_config.ap.ssid, AP_SSID_DEFAULT, sizeof(wifi_config.ap.ssid));
    strlcpy((char*)wifi_config.ap.password, AP_PASS_DEFAULT, sizeof(wifi_config.ap.password));
    wifi_config.ap.ssid_len = strlen(AP_SSID_DEFAULT);
    wifi_config.ap.channel = AP_CHANNEL_DEFAULT;
    wifi_config.ap.authmode = WIFI_AUTH_WPA_WPA2_PSK;
    wifi_config.ap.max_connection = AP_MAX_STA_CONN;

    if (strlen(AP_PASS_DEFAULT) == 0) {
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "SoftAP 已启动. SSID: %s, channel: %d",
             AP_SSID_DEFAULT, AP_CHANNEL_DEFAULT);

    // 延迟后尝试连接保存的 WiFi
    vTaskDelay(pdMS_TO_TICKS(2000));
    wifi_manager_auto_connect_saved();
}

// ===== 获取 STA IP 信息 =====
esp_netif_ip_info_t wifi_manager_get_sta_ip_info() {
    esp_netif_ip_info_t ip_info;
    memset(&ip_info, 0, sizeof(esp_netif_ip_info_t));
    if (is_sta_connected) {
        esp_netif_get_ip_info(esp_netif_get_handle_from_ifkey("WIFI_STA_DEF"), &ip_info);
    }
    return ip_info;
}

// ===== DHCP 状态查询 =====
static bool dhcp_has_valid_ip = false;
static uint32_t last_dhcp_query_time = 0;

void wifi_manager_query_dhcp_status() {
    uint32_t current_time = esp_log_timestamp();

    if (dhcp_has_valid_ip && (current_time - last_dhcp_query_time) < 30000) {
        return;
    }

    last_dhcp_query_time = current_time;

    // 检查 WiFi 连接状态
    wifi_ap_record_t ap_info;
    esp_err_t ret = esp_wifi_sta_get_ap_info(&ap_info);
    if (ret != ESP_OK) {
        dhcp_has_valid_ip = false;
        return;
    }

    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (!netif) {
        dhcp_has_valid_ip = false;
        return;
    }

    bool netif_up = esp_netif_is_netif_up(netif);
    if (netif_up) {
        esp_netif_ip_info_t ip_info;
        ret = esp_netif_get_ip_info(netif, &ip_info);
        if (ret == ESP_OK) {
            bool has_valid_ip_now = (ip_info.ip.addr != 0);

            if (has_valid_ip_now != dhcp_has_valid_ip) {
                ESP_LOGI(TAG, "IP 配置状态变化 - IP: " IPSTR, IP2STR(&ip_info.ip));
            } else if (!has_valid_ip_now) {
                ESP_LOGW(TAG, "DHCP 状态: 仍在等待 IP 地址分配...");
            }

            dhcp_has_valid_ip = has_valid_ip_now;
            is_sta_connected = has_valid_ip_now;
        } else {
            dhcp_has_valid_ip = false;
            is_sta_connected = false;
        }
    } else {
        dhcp_has_valid_ip = false;
        is_sta_connected = false;
    }
}
