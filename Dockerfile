# 使用官方Python运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器的/app目录
COPY . /app

# 安装requirements.txt中列出的任何所需包
RUN pip install --no-cache-dir -r requirements.txt

# 单独安装gunicorn
RUN pip install gunicorn==20.1.0

# 使端口80可供此容器外的环境使用
EXPOSE 80

# 定义环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 运行app.py
CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]
