from flask import Flask, request, jsonify
import subprocess
import os
import logging
import json
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H%M%S'
)
logger = logging.getLogger(__name__)

# 存储已处理的告警信息
processed_alerts = {}
# 告警记录文件路径
ALERT_RECORD_FILE = 'tmpprocessed_alerts.json'
# 文件锁
file_lock = threading.Lock()

def load_processed_alerts()
    从文件加载已处理的告警记录
    try
        if os.path.exists(ALERT_RECORD_FILE)
            with open(ALERT_RECORD_FILE, 'r') as f
                data = json.load(f)
                # 将字符串时间转换回datetime对象
                for key, time_str in data.items()
                    processed_alerts[key] = datetime.fromisoformat(time_str)
                logger.info(f已加载 {len(processed_alerts)} 条告警处理记录)
    except Exception as e
        logger.error(f加载告警处理记录失败 {str(e)})

def save_processed_alerts()
    保存已处理的告警记录到文件
    try
        with file_lock
            # 将datetime对象转换为字符串
            data = {key time.isoformat() for key, time in processed_alerts.items()}
            with open(ALERT_RECORD_FILE, 'w') as f
                json.dump(data, f)
            logger.info(f已保存 {len(processed_alerts)} 条告警处理记录)
    except Exception as e
        logger.error(f保存告警处理记录失败 {str(e)})

def get_alert_key(alert)
    生成告警的唯一标识
    instance = alert.get('labels', {}).get('instance')
    if not instance
        return None
    return instance

def is_alert_processed(alert)
    检查告警是否已经处理过
    alert_key = get_alert_key(alert)
    if not alert_key
        logger.warning(告警缺少instance，无法进行去重检查)
        return False
    
    try
        current_time = datetime.utcnow()
        
        # 检查是否已经处理过这个告警
        if alert_key in processed_alerts
            last_processed = processed_alerts[alert_key]
            # 如果上次处理时间在1小时内，则跳过
            if current_time - last_processed  timedelta(hours=1)
                logger.info(f告警 {alert_key} 在1小时内已处理过，跳过处理)
                return True
            else
                logger.info(f告警 {alert_key} 上次处理时间已超过1小时，允许重新处理)
        else
            logger.info(f告警 {alert_key} 首次处理)
    except Exception as e
        logger.error(f检查告警时间时发生错误 {str(e)})
        return False
    
    return False

def mark_alert_processed(alert)
    标记告警为已处理
    alert_key = get_alert_key(alert)
    if alert_key
        processed_alerts[alert_key] = datetime.utcnow()
        logger.info(f标记告警 {alert_key} 为已处理，时间 {processed_alerts[alert_key]})
        # 保存到文件
        save_processed_alerts()

def get_container_name(instance)
    从实例名称中提取容器名称
    # 实例名称格式通常为 pod名称-随机字符串
    # 例如 iems-goeu-job-59cb8dbcd4-c68tb
    parts = instance.split('-')
    if len(parts) = 3 and parts[0] == 'iems' and parts[1] == 'goeu'
        return f{parts[0]}-{parts[1]}-{parts[2]}
    return None

@app.route('webhook', methods=['POST'])
def webhook()
    try
        data = request.json
        logger.info(f收到告警数据 {json.dumps(data, ensure_ascii=False)})
        
        # 获取告警列表
        alerts = []
        if isinstance(data, list)
            alerts = data
        elif isinstance(data, dict) and 'alerts' in data
            alerts = data['alerts']
        else
            logger.warning(f未知的告警数据格式 {type(data)})
            return jsonify({status error, message 未知的告警数据格式}), 400
        
        # 处理每个告警
        for alert in alerts
            # 只处理firing状态的告警
            if alert.get('status') != 'firing'
                logger.info(f跳过非firing状态的告警 {get_alert_key(alert)})
                continue
                
            if alert.get('labels', {}).get('alertname') == 'HeapMemoryHighUsage'
                instance = alert['labels'].get('instance')
                logger.info(f检测到堆内存告警 {instance})
                
                # 检查是否已经处理过这个告警
                if is_alert_processed(alert)
                    logger.info(f跳过已处理的告警 {get_alert_key(alert)})
                    continue
                
                # 获取容器名称
                container = get_container_name(instance)
                if not container
                    logger.warning(f无法从实例名称 {instance} 中提取容器名称，跳过处理)
                    continue
                    
                namespace = 'project'  # 根据您的配置设置
                
                logger.info(f开始处理告警，实例 {instance}, 命名空间 {namespace}, 容器 {container})
                
                # 执行堆转储脚本
                script_path = os.path.join(os.path.dirname(__file__), 'heap_dump.sh')
                result = subprocess.run(['bash', script_path, instance, namespace, container], 
                                     capture_output=True, text=True)
                
                if result.stdout
                    logger.info(f堆转储执行结果 {result.stdout})
                if result.stderr
                    logger.error(f堆转储执行错误 {result.stderr})
                else
                    # 只有在成功执行堆转储后才标记为已处理
                    mark_alert_processed(alert)
                    logger.info(f告警处理完成 {get_alert_key(alert)})
        
        return jsonify({status success})
    except Exception as e
        logger.error(f处理webhook请求时发生错误 {str(e)})
        return jsonify({status error, message str(e)}), 500

if __name__ == '__main__'
    # 启动时加载已处理的告警记录
    load_processed_alerts()
    app.run(host='0.0.0.0', port=8060) 