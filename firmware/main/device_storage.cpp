#include "device_storage.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_random.h"
#include <string.h>
#include <inttypes.h>
#include <string>

#define NVS_NAMESPACE "storage"
#define SSID_KEY "ssid"
#define PASSWORD_KEY "password"
#define DEVICE_ID_KEY "device_id"

static const char *TAG = "device_storage";

void device_storage_set_connection_info(const char *ssid, const char *password, const char *device_id) {
    nvs_handle_t nvs_handle;
    ESP_ERROR_CHECK(nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle));

    ESP_ERROR_CHECK(nvs_set_str(nvs_handle, SSID_KEY, ssid));
    ESP_ERROR_CHECK(nvs_set_str(nvs_handle, PASSWORD_KEY, password));
    ESP_ERROR_CHECK(nvs_set_str(nvs_handle, DEVICE_ID_KEY, device_id));

    ESP_ERROR_CHECK(nvs_commit(nvs_handle));
    nvs_close(nvs_handle);

    ESP_LOGI(TAG, "连接信息已保存: SSID=%s, device id=%s", ssid, device_id);
}
void device_storage_get_connection_info(std::string &ssid, std::string &password, std::string &device_id) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "打开 NVS 句柄失败: %s", esp_err_to_name(err));
        return;
    }

    auto get_value = [&](const char *key, std::string &value) {
        size_t required_size = 0;
        err = nvs_get_str(nvs_handle, key, nullptr, &required_size);
        if (err == ESP_OK) {
            value.resize(required_size);
            err = nvs_get_str(nvs_handle, key, &value[0], &required_size);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "读取键 [%s] 的值失败: %s", key, esp_err_to_name(err));
                value.clear();
            }
        } else {
            ESP_LOGE(TAG, "获取键 [%s] 的大小失败: %s", key, esp_err_to_name(err));
            value.clear();
        }
    };

    get_value(SSID_KEY, ssid);
    get_value(PASSWORD_KEY, password);
    get_value(DEVICE_ID_KEY, device_id);

    nvs_close(nvs_handle);
}

void device_storage_clear_all(void) {
    nvs_handle_t nvs_handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "打开 NVS 句柄失败，无法清空数据: %s", esp_err_to_name(err));
        return;
    }

    // 删除所有存储的键
    err = nvs_erase_key(nvs_handle, SSID_KEY);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGW(TAG, "删除 SSID 键失败: %s", esp_err_to_name(err));
    }

    err = nvs_erase_key(nvs_handle, PASSWORD_KEY);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGW(TAG, "删除密码键失败: %s", esp_err_to_name(err));
    }

    err = nvs_erase_key(nvs_handle, DEVICE_ID_KEY);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGW(TAG, "删除设备ID键失败: %s", esp_err_to_name(err));
    }

    // 提交更改
    err = nvs_commit(nvs_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "提交清空操作失败: %s", esp_err_to_name(err));
    } else {
        ESP_LOGI(TAG, "设备存储数据已清空，设备将恢复为新设备状态");
    }

    nvs_close(nvs_handle);
}