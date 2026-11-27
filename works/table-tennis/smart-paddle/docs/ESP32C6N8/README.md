# SGFK ESP32-C6-N8 模块资料（商品图整理）

本目录根据商家商品描述图整理，供 SmartPaddle PCB 封装、固件 GPIO、装配朝向核对使用。  
原始图在 [`images/`](images/)；文中引用稳定文件名副本。

## 校本脚位（改板入口）

| 路径 | 角色 |
|------|------|
| [`pcb/lib/esp32c6n8/pinmap.py`](../../pcb/lib/esp32c6n8/pinmap.py) | **唯一真理源**：顶视几何、pad→丝印、工程绑定、固件 GPIO（勿抄背面丝印） |
| `python3 pcb/scripts/generate_sgfk_esp32c6n8_mod.py` | 由 pinmap 生成 `.kicad_mod`（不改 `.kicad_pcb`） |
| `python3 pcb/scripts/validate_esp32c6n8_pinmap.py` | 校验 `main.ato` / mod / `config.h` / step3 与 pinmap 一致 |

板上实例在 KiCad 对 `SGFK_ESP32-C6-N8_CUTOUT`「从库更新封装」。网络由 ato → netlist → `step3_import_netlist.py` 分配。

| 文档 | 内容 |
|------|------|
| [`pinout-and-dimensions.md`](pinout-and-dimensions.md) | 外形尺寸、半孔编号、功能表（对照乐鑫 WROOM-1） |
| [`reverse-mount-and-reboot-audit.md`](reverse-mount-and-reboot-audit.md) | 反焊/长边对调、与 `main.ato` 对照、循环重启串口结论 |

## 图片索引

| 文件 | 内容 |
|------|------|
| [`images/pinout-dimensions.png`](images/pinout-dimensions.png) | 18×25.5 mm、节距 1.27、半孔丝印 |
| [`images/pinout-numbered.png`](images/pinout-numbered.png) | pin 1–28 编号 + BOOT 标注 |
| [`images/pin-function-table.png`](images/pin-function-table.png) | 引脚功能表（GPIO / USB / UART） |
| [`images/pinout-keepout.png`](images/pinout-keepout.png) | 顶视图 + Keepout Zone |
| [`images/module-schematic.png`](images/module-schematic.png) | 模块内部原理图摘录 |

> 模块与乐鑫 **ESP32-C6-WROOM-1** 半孔定义一致；商品为 SGFK 丝印的 C6-N8 成品模组。
