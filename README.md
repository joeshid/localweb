# 音视频转录系统

这是一个基于 Flask 和 FunASR 的音视频转录系统，支持音频和视频文件的语音识别转录功能。

## 功能特点

- 支持多种音频格式（WAV、MP3等）和视频格式的上传
- 自动提取视频中的音频内容
- 支持长音频分片处理，提高转录效率
- 实时显示转录进度
- 支持转录结果缓存，避免重复处理
- 支持最近文件列表管理
- 支持中文文件名

## 系统要求

- Python 3.8 或更高版本
- FFmpeg（用于音频处理）
- 足够的磁盘空间用于存储上传的文件和转录结果

## 安装说明

1. 克隆项目并创建虚拟环境：
```bash
git clone [项目地址]
cd localweb
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装 FFmpeg（如果尚未安装）：
- macOS：`brew install ffmpeg`
- Linux：`sudo apt-get install ffmpeg`
- Windows：从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载并添加到系统路径

## 使用说明

1. 启动服务器：
```bash
python app.py
```

2. 访问网页界面：
打开浏览器访问 `http://localhost:5001`

3. 上传文件：
- 点击"选择文件"按钮选择要转录的音频或视频文件
- 等待文件上传完成
- 系统会自动开始转录处理
- 转录完成后可以查看结果

## 目录结构

- `app.py`：主应用程序文件
- `templates/`：HTML 模板文件
- `static/`：静态资源文件（CSS、JavaScript等）
- `uploads/`：上传文件存储目录
- `audio_output/`：音频文件输出目录
- `txt_output/`：转录文本输出目录

## 性能优化

系统包含多项性能优化措施：
- 音频分片处理：自动将长音频分割成小片段并行处理
- 批处理优化：使用批处理提高模型推理效率
- 缓存机制：避免重复处理相同文件
- 文件清理：自动清理临时文件

## 注意事项

- 默认最大文件大小限制为 500MB
- 支持的音频格式：WAV、MP3、M4A 等
- 支持的视频格式：MP4、AVI、MOV 等
- 建议使用 16kHz 采样率的音频以获得最佳识别效果

## Docker 支持

项目提供了 Docker 支持，详细部署说明请参考 `DEPLOY_GUIDE.md`。

## 许可证

[添加许可证信息]

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。
