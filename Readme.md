# 整体工作流程

- 监控系统（如 Prometheus）检测到 Java 应用堆内存使用率过高，触发 HeapMemoryHighUsage 告警；
- Alertmanager 根据 config.yml 配置，将告警通过 webhook 发送到 webhook_server.py（运行在 8060 端口）；
- webhook_server.py 验证告警状态，检查是否为 1 小时内首次处理该实例的告警；
- 若符合处理条件，提取 Pod / 容器信息，调用 heap_dump.sh；
- heap_dump.sh 通过 kubectl 在目标容器中生成堆转储文件，并复制到本地存储，完成后清理容器内临时文件；
- webhook_server.py 记录告警处理状态，避免短时间内重复处理。

# 运行
```bash
docker run -d \
  --name heap-dump-webhook \
  -p 8060:8060 \
  -v /data/java-heap:/app \
  -e TZ=Asia/Shanghai \
  heap-dump-webhook:latest \
  python webhook_server.py
```