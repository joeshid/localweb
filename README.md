# 音视频文本提取工具

这是一个基于 Flask 的本地 Web 应用程序，用于从音视频文件中提取文本内容。

## 功能特点

- 支持多种音视频格式（MP3、MP4、WAV、MOV 等）
- 文件大小限制：500MB
- 自动添加标点符号
- 支持批量处理
- 实时显示处理进度
- 最近文件列表功能

## 目录结构

```
localweb/
├── app.py                 # 主应用程序
├── static/               # 静态文件
│   ├── css/             # CSS 样式
│   └── js/              # JavaScript 文件
├── templates/           # HTML 模板
├── uploads/            # 上传文件临时存储
├── audio_output/       # 音频文件输出目录
├── txt_output/         # 文本文件输出目录
└── recent_files.json   # 最近文件列表
```

## 技术栈

- 后端：Python Flask
- 前端：Bootstrap 5
- 音视频处理：moviepy
- 语音识别：FunASR (ModelScope)

## 主要功能

1. 文件上传
   - 支持拖拽上传
   - 支持多种音视频格式
   - 自动格式验证

2. 音视频处理
   - 自动提取音频
   - 转换为标准格式（WAV，16kHz）
   - 智能清理临时文件

3. 语音识别
   - 使用 FunASR 进行语音识别
   - 自动添加标点符号
   - 高准确度转录

4. 文件管理
   - 最近文件列表
   - 一键清空缓存
   - 文件下载功能

## 使用说明

1. 启动服务
   ```bash
   python app.py
   ```

2. 访问应用
   - 打开浏览器
   - 访问 http://localhost:5001

3. 上传文件
   - 点击上传按钮或拖拽文件
   - 等待处理完成
   - 下载转录文本

## 注意事项

- 确保有足够的磁盘空间
- 处理大文件时可能需要较长时间
- 定期清理缓存文件

## 系统要求

- Python 3.8+
- Flask
- ModelScope
- FFmpeg（用于音视频处理）
