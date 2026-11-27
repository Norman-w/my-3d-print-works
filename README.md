# 我的 3D 打印作品

收集自己设计、打印和验证过的 3D 打印作品。

## 目录

```text
works/<作品名>/      作品源文件、打印文件、预览和验证记录
templates/work/     新作品模板
scripts/             工具脚本
```

每个作品至少记录：用途、尺寸、配套实物、`.scad` 源文件、STL / 3MF、预览图、验证结果、打印参数和未完成项。

## 状态

`concept` → `digital-verified` → `sliced` → `printed` → `assembled` → `accepted`

数字模型通过、切片成功或网页预览，都不等于实物装配验收。

## 新建作品

```sh
sh scripts/new-work.sh my-object
```

作品索引：[`works/catalog.md`](works/catalog.md)
