//
// Created by Norman Wang on 2025/12/31.
//

#include "utils.h"
#include "esp_random.h" // for esp_random

void replace_placeholder(std::string &body, const std::string &placeholder, const std::string &value) {
    size_t pos = 0;
    while ((pos = body.find(placeholder, pos)) != std::string::npos) {
        body.replace(pos, placeholder.length(), value);
        pos += value.length(); // Move past the replaced value
    }
}

void generate_fake_data(uint8_t *data, int *len) {
    *len = 10 + (esp_random() % 41); // 随机长度 10-50
    for (int i = 0; i < *len; i++) {
        data[i] = esp_random() % 256;
    }
}