FROM python:3.9-slim

WORKDIR /app

# 安装必要的工具
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN chmod +x heap_dump.sh

# 创建必要的目录
RUN mkdir -p /tmp/heapdumps /root/.ssh

# 设置SSH密钥权限
RUN chmod 700 /root/.ssh

EXPOSE 8060

CMD ["python", "webhook_server.py"] 