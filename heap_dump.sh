#!/bin/bash

# 设置错误时退出
set -e

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 获取pod名称、命名空间和容器名称
POD_NAME=$1
NAMESPACE=$2
CONTAINER_NAME=$3

if [ -z "$POD_NAME" ] || [ -z "$NAMESPACE" ] || [ -z "$CONTAINER_NAME" ]; then
    log "错误: 缺少必要参数"
    log "用法: $0 <pod_name> <namespace> <container_name>"
    exit 1
fi

# 设置堆转储文件保存路径
DUMP_DIR="/tmp/heapdumps"
mkdir -p $DUMP_DIR

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 生成文件名（包含实例信息）
FILENAME="heap_${POD_NAME}_${TIMESTAMP}.hprof"

# 检查kubectl配置
if ! kubectl config view &>/dev/null; then
    log "错误: 无法找到有效的kubectl配置，请确保已正确配置kubectl"
    exit 1
fi

# 验证是否可以访问指定的Pod
if ! kubectl -n $NAMESPACE get pod $POD_NAME &>/dev/null; then
    log "错误: 无法访问Pod $POD_NAME 在命名空间 $NAMESPACE 中"
    exit 1
fi

# 执行jmap命令
log "开始执行jmap命令..."
if ! kubectl exec -n $NAMESPACE $POD_NAME -c $CONTAINER_NAME -- jmap -dump:format=b,file=/tmp/$FILENAME 1; then
    log "错误: jmap命令执行失败"
    exit 1
fi
log "jmap命令执行完成"

# 等待文件生成
log "等待文件生成..."
sleep 5

# 将堆转储文件从pod复制到本地
log "开始将文件从pod复制到本地..."
if ! kubectl cp $NAMESPACE/$POD_NAME:/tmp/$FILENAME $DUMP_DIR/$FILENAME; then
    log "错误: 文件从pod复制到本地失败"
    exit 1
fi
log "文件已复制到本地"

# 清理pod中的临时文件
log "清理pod中的临时文件..."
if ! kubectl exec -n $NAMESPACE $POD_NAME -c $CONTAINER_NAME -- rm -f /tmp/$FILENAME; then
    log "警告: pod中的临时文件清理失败"
fi

# 检查文件大小
#FILE_SIZE=$(du -h $DUMP_DIR/$FILENAME | cut -f1)
log "堆转储完成，文件保存在: $DUMP_DIR/$FILENAME"
#log "文件大小: $FILE_SIZE" 