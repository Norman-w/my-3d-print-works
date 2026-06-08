#include "dns_server.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "lwip/sockets.h"
#include "esp_netif.h"

static const char *TAG = "dns_server";

// DNS 报头结构
typedef struct __attribute__((__packed__))
{
    uint16_t id;
    uint16_t flags;
    uint16_t qdcount;
    uint16_t ancount;
    uint16_t nscount;
    uint16_t arcount;
} DnsHeader;

// DNS 查询问题结构
typedef struct {
    uint16_t type;
    uint16_t qclass;
} DnsQuestion;

// 从DNS查询中提取域名
static char* parse_dns_name(uint8_t *buffer, int *offset) {
    static char name[128];
    int name_len = 0;
    int pos = *offset;
    while (buffer[pos] != 0) {
        if ((buffer[pos] & 0xC0) == 0xC0) { // 指针
            // 简单处理，不解析指针
             pos += 2;
             break;
        } else { // 标签
            int len = buffer[pos];
            pos++;
            if (name_len > 0) {
                name[name_len++] = '.';
            }
            memcpy(name + name_len, buffer + pos, len);
            name_len += len;
            pos += len;
        }
    }
    name[name_len] = '\0';
    *offset = pos + 1; // 跳过结尾的0
    return name;
}


static void dns_server_task(void *pvParameters) {
    uint8_t buffer[128];
    struct sockaddr_in client;
    socklen_t client_len = sizeof(client);

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGE(TAG, "无法创建 DNS socket");
        vTaskDelete(NULL);
        return;
    }

    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(53);

    if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "DNS socket 绑定失败");
        close(sock);
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "DNS 服务器已启动");

    while (1) {
        int len = recvfrom(sock, buffer, sizeof(buffer), 0, (struct sockaddr *)&client, &client_len);
        if (len > 0) {
            DnsHeader *header = (DnsHeader *)buffer;
            
            // 只响应标准查询
            if ((header->flags & 0x8000) == 0 && header->qdcount > 0) {
                int offset = sizeof(DnsHeader);
                char* domain_name = parse_dns_name(buffer, &offset);
                ESP_LOGI(TAG, "DNS 查询: %s", domain_name);

                esp_netif_ip_info_t ip_info;
                esp_netif_get_ip_info(esp_netif_get_handle_from_ifkey("WIFI_AP_DEF"), &ip_info);
                
                header->flags |= htons(0x8180); // 响应标志, 无错误
                header->ancount = htons(1); // 1个回答记录

                // 构建响应
                uint8_t *p = buffer + len;
                *p++ = 0xC0; // 名称指针
                *p++ = 0x0C; // 指向查询名称在原报文中的偏移量 (12)
                *p++ = 0x00; // 类型 A (Host Address)
                *p++ = 0x01;
                *p++ = 0x00; // Class IN
                *p++ = 0x01;
                *p++ = 0x00; // TTL (高位)
                *p++ = 0x00;
                *p++ = 0x00; 
                *p++ = 0x3C; // TTL (低位) -> 60秒
                *p++ = 0x00; // 数据长度 (高位)
                *p++ = 0x04; // 数据长度 (低位) -> 4字节
                
                uint32_t ip_addr = ip_info.ip.addr;
                *p++ = (ip_addr >> 0) & 0xFF;
                *p++ = (ip_addr >> 8) & 0xFF;
                *p++ = (ip_addr >> 16) & 0xFF;
                *p++ = (ip_addr >> 24) & 0xFF;
                
                sendto(sock, buffer, p - buffer, 0, (struct sockaddr *)&client, client_len);
            }
        }
    }
    close(sock);
    vTaskDelete(NULL);
}

void dns_server_start(void) {
    xTaskCreate(dns_server_task, "dns_server", 4096, NULL, 5, NULL);
} 