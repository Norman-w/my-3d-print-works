//
// Created by Norman Wang on 2025/12/31.
//

#ifndef UTILS_H
#define UTILS_H

#include <string>
#include <cstdint>

// 字符串处理函数
void replace_placeholder(std::string &body, const std::string &placeholder, const std::string &value);

// 数据生成函数
void generate_fake_data(uint8_t *data, int *len);

#endif //UTILS_H
