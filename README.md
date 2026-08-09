# gas

Genshin Impact 圣遗物扫描工具。

[English](README_EN.md) | 中文

## 安装

```sh
uv sync
```

## 使用方法

1. 使用**管理员权限**打开控制台（否则可能无法控制原神窗口）。
2. 原神客户端窗口已打开，并停留在**圣遗物背包界面**。
3. 游戏需使用**窗口化**运行（不要全屏），否则无法获取窗口位置。
4. 游戏分辨率需为 **1920x1080**（当前 `assets/scan.toml` 仅支持该分辨率，如需其他分辨率请在此文件中添加对应配置）。

```sh
# 扫描，保存到默认文件 ./gas.toml（genshin-atool 格式）
uv run gas

# 扫描，保存到指定文件
uv run gas --file mybag.toml

# Append 模式：读取文件查重，遇到已扫描过的圣遗物即停止扫描，合并结果写回同一文件
uv run gas --file mybag.toml --append

# 指定 GOOD (Genshin Optimizer) JSON 格式
uv run gas --file good.json --format good

# 未指定 --format 时，自动从文件内容识别格式（genshin-atool 文件带 format 字段，GOOD 文件自带 format 标识）
uv run gas --file good.json --append
```
