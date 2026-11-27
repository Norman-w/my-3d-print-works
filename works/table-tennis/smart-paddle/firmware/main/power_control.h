#ifndef POWER_CONTROL_H
#define POWER_CONTROL_H

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Pull C4 PWR_LATCH (GPIO47) high before the user releases the key. */
esp_err_t power_control_init(void);

/** 拉低锁存，整机断电（调用后不再返回有效执行）。 */
void power_control_shutdown(void);

#ifdef __cplusplus
}
#endif

#endif // POWER_CONTROL_H
