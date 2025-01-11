# Windows 10 部署指南

## 1. 环境准备

### 安装 Python
1. 下载并安装 Python 3.8+ (https://www.python.org/downloads/)
2. 安装时勾选 "Add Python to PATH"

### 安装 FFmpeg
1. 下载 FFmpeg (https://www.gyan.dev/ffmpeg/builds/)
2. 解压到指定目录 (如 C:\ffmpeg)
3. 添加到系统环境变量:
   - 打开系统属性 -> 环境变量
   - 在 Path 中添加 FFmpeg 的 bin 目录 (如 C:\ffmpeg\bin)

## 2. 安装项目

1. 下载项目文件到本地目录
2. 打开命令提示符 (CMD)，进入项目目录
3. 创建虚拟环境:
```bash
python -m venv venv
venv\Scripts\activate
```

4. 安装依赖:
```bash
pip install -r requirements.txt
```

## 3. 启动应用

1. 在项目目录下启动应用:
```bash
python app.py
```

2. 访问应用:
   - 本机访问: http://localhost:5001
   - 局域网访问: http://[本机IP]:5001
   
## 4. 查看本机 IP

1. 打开命令提示符
2. 输入命令:
```bash
ipconfig
```
3. 查看 "IPv4 地址" 项 (通常形如 192.168.x.x)

## 注意事项

1. 确保 Windows 防火墙允许 Python 和端口 5001
2. 如遇到权限问题，请以管理员身份运行命令提示符
3. 确保局域网内的电脑能够相互访问
