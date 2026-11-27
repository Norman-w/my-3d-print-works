# 局域网预览

当前地址：[http://192.168.7.187:8877/](http://192.168.7.187:8877/)。手机或电脑连接同一局域网后可打开；Mac 须保持开机联网。DHCP 地址变化后，以启动脚本输出为准。

服务绑定 `0.0.0.0:8877`，仅托管 `output/revision-review/`。macOS 当前登录会话的 launchd 管理该进程，终端任务结束不会停止服务。注销或重启后需重新启动；没有安装开机启动项。

在项目目录执行：

```sh
python3 scripts/preview_lan.py start
python3 scripts/preview_lan.py status
python3 scripts/preview_lan.py stop
```

服务脚本不重建或覆盖预览页面，不停止其他端口的服务。需要更新模型时运行 `python3 scripts/build_launcher_review.py`；它先检查当前总装、旋转头、网格及五金报告的文件身份，再发布。旧版发布器和旧预览保留用于追溯。

当前发布48项：送料总成36项、旋转头工作档11项、退出保持叉1项。其中43项是打印实例，5项是管材、弹簧或金属五金参考。浏览器已实际加载送料36项和旋转头11项，并查看了两组爆炸图。Three.js依赖随页面本地托管，无须从CDN加载。

项目服务包装器为静态页面、模型和下载设置`Cache-Control: no-store`，避免清单已更新而首页仍显示旧版。此前已打开过旧页面的浏览器首次使用需刷新一次。

运行 `python3 scripts/verify_launcher_lan.py` 可从本机经LAN地址核对清单、页面、模型、说明及ZIP下载的实际字节，并核实监听进程及服务目录。记录在 `output/preview-service/lan-verification.json`。本机经LAN IP访问不等于第二台设备验证；当前没有第二台设备的访问记录。

页面提供数字制作候选包下载，包含STL、离线3MF和装配说明。预览与候选包均未声明实物首机验收完成。
