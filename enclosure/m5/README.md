# SmartPaddle M5 外壳（工程样机预览）

> 状态：**M5.1/M5.2 视觉样机** — 未实测、未打印、未冻结尾板接口。配套 `M5.C5`。
> 不得覆盖 M4 STL / SCAD。

## 目标

拍尾固定窄尾板（X−）+ 抽屉式 14500 电池匣（X+，Y−→Y+ 插入）+ X+ 侧横向机械滑扣。

## 看模型（真实拍柄合壳）

```bash
# Step 1–5 等价：合壳挖电池仓/滑扣/螺丝迁移（不依赖尾板布局）
./scripts/export-m5-preview.sh
# → enclosure/m5/build/m5_handle_tail_pre_board.stl

# Step 6（尾板布局就绪后）：用 pcb-tail Edge.Cuts + J1/SW1/D1/LED1 干涉拍柄
python3 scripts/step6_tail_board_interfere_handle.py
# → m5_handle_tail.stl + m5_tail_interference.stl

./scripts/preview-m5.sh          # HTTP 托管 http://127.0.0.1:8765/preview.html
```

- 外形：`enclosure/stl/paddle_handle_{front,back}.stl` 合模后裁切尾段 70mm  
- Step 6 前可先做电池匣预览；尾板未摆好时不要跑 Step 6  
- 滑扣：**拍尾端面**横向拨动（不在左右握持边）  
- 不要用 `file://` 直接打开 HTML
## 文件

| 文件 | 职责 |
|------|------|
| `parameters_m5.scad` | M5 专有参数与可行性公式 |
| `battery_cartridge_m5.scad` | 电池匣 / 电芯 / 保护板 / 触点 |
| `latch_m5.scad` | 滑块 / 锁舌 / 弹簧包络 |
| `tail_housing_m5.scad` | 尾段壳、仓、导轨、分隔墙 |
| `interface_envelopes_m5.scad` | 尾板/USB/按键/LED/线束禁布 |
| `assembly_m5.scad` | 装配状态入口 |
| `paddle_shell_m5.scad` | M5 入口 |

## 首轮尺寸（全部 TARGET/DATASHEET）

| 项 | 值 | 状态 |
|---|---:|---|
| 尾段外包络 | 40 × 30 mm | MODEL_TARGET（相对 M4 局部加宽） |
| 电池匣外截面 | 16 × 16 mm | TARGET |
| 电池匣总长 | 57 mm | TARGET |
| 尾板包络 | 10 × 21 × 1 mm | TARGET |
| 锁扣行程 | 1.8 mm | TARGET |
| 顶出量 | 4 mm | TARGET |

## 实测表（待填）

| 对象 | 日期 | 值 | 备注 |
|---|---|---|---|
| 14500 批次最大 Ø/L | — | TBD | |
| 保护板包络 | — | TBD | |
| C5 尾板器件高度 | — | TBD | 尚未画板 |

## 下一步（服务尾板设计）

冻结前请从预览确认：

1. 尾板在 X−，USB/按键/双灯在尾端面
2. 电池匣行程与触点座不干涉尾板
3. 8P 线束从尾板 +Y 走出的弯曲空间
4. `m5_tail_interface.json`（尚未生成）再交给 C5 PCB
