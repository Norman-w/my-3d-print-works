#pragma once

#include <cstdint>

// ===== 分区：常量/配置 =====

// IM948 传输比例因子（对应 16g / 2000dps 量程）
constexpr float IM948_SCALE_ACCEL         = 0.00478515625f;    // 加速度 [-16g~+16g]    9.8*16/32768
constexpr float IM948_SCALE_QUAT          = 0.000030517578125f; // 四元数 [-1~+1]         1/32768
constexpr float IM948_SCALE_ANGLE         = 0.0054931640625f;   // 角度   [-180~+180]     180/32768
constexpr float IM948_SCALE_ANGLE_SPEED   = 0.06103515625f;     // 角速度 [-2000~+2000]    2000/32768
constexpr float IM948_SCALE_MAG           = 0.15106201171875f;  // 磁场 [-4950~+4950]   4950/32768
constexpr float IM948_SCALE_TEMPERATURE   = 0.01f;              // 温度
constexpr float IM948_SCALE_AIR_PRESSURE  = 0.0002384185791f;   // 气压 [-2000~+2000]    2000/8388608
constexpr float IM948_SCALE_HEIGHT        = 0.0010728836f;       // 高度 [-9000~+9000]    9000/8388608

// 协议帧定界符
constexpr uint8_t IM948_PKT_BEGIN = 0x49;
constexpr uint8_t IM948_PKT_END   = 0x4D;

// 协议帧最大长度
constexpr uint8_t IM948_PKT_MAX_RX_DATA = 73;
constexpr uint8_t IM948_PKT_MAX_TX_DATA = 31;

// ===== 分区：模型/类型 =====

// 量程配置
enum class Im948AccelRange : uint8_t {
    G2  = 0,
    G4  = 1,
    G8  = 2,
    G16 = 3,
};

enum class Im948GyroRange : uint8_t {
    DPS256  = 0,
    DPS512  = 1,
    DPS1024 = 2,
    DPS2048 = 3,
};

enum class Im948BaudRate : uint8_t {
    B9600   = 0,
    B115200 = 1,
    B230400 = 2,
    B460800 = 3,
};

// 订阅标识位掩码
enum Im948ReportTag : uint16_t {
    TAG_ACCEL_NO_GRAVITY      = 0x0001,  // 加速度（去重力）
    TAG_ACCEL_WITH_GRAVITY    = 0x0002,  // 加速度（含重力）
    TAG_ANGULAR_VELOCITY      = 0x0004,  // 角速度
    TAG_MAGNETIC              = 0x0008,  // 磁场
    TAG_TEMP_PRESSURE_HEIGHT  = 0x0010,  // 温度/气压/高度
    TAG_QUATERNION            = 0x0020,  // 四元数
    TAG_EULER_ANGLES          = 0x0040,  // 欧拉角
    TAG_DISPLACEMENT          = 0x0080,  // 空间位移
    TAG_ACTIVITY              = 0x0100,  // 活动检测
    TAG_ACCEL_NAV_FRAME       = 0x0200,  // 加速度（导航系，去重力）
    TAG_ADC                   = 0x0400,  // ADC 电压
    TAG_GPIO1                 = 0x0800,  // GPIO1 状态
    TAG_ALL                   = 0x0FFF,  // 订阅全部
};

// 单帧完整 IMU 数据
struct ImuFrame {
    uint32_t timestamp_ms;    // 模块开机毫秒

    // 加速度（含重力）m/s^2
    float accel_gx;
    float accel_gy;
    float accel_gz;

    // 加速度（去重力）m/s^2
    float accel_lx;
    float accel_ly;
    float accel_lz;

    // 角速度 °/s
    float gyro_x;
    float gyro_y;
    float gyro_z;

    // 欧拉角 °
    float euler_roll;
    float euler_pitch;
    float euler_yaw;

    // 四元数
    float quat_w;
    float quat_x;
    float quat_y;
    float quat_z;

    // 磁场 uT
    float mag_x;
    float mag_y;
    float mag_z;

    // 辅助
    float temperature;    // °C
    float air_pressure;   // hPa
    float height;         // m

    // 空间位移 mm
    float offset_x;
    float offset_y;
    float offset_z;

    // 导航系加速度 m/s^2
    float accel_nav_x;
    float accel_nav_y;
    float accel_nav_z;

    // 标记
    bool is_valid;
    uint16_t subscribe_tags;  // 当前帧实际包含哪些字段
};
