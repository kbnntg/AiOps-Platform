import time
import os
from collections import deque

import psutil
import AI
from aggregation import AlertAggregator
from load_config import load_config
from Prometheus_config import (
    cpu_use_gauge, free_use_gauge, disk_use_gauge,
    disk_read_gauge, disk_write_gauge,
    network_send_gauge, network_resv_gauge, port_num
)
from mysql_config import insert_data, insert_alert_history
from alter import log_alter, log_alter_aggregated
from history import get_history
# from logger import logger_alter


# 9-16新增滑动窗口触发告警
# 创建类：
class SildWindows:
    # 定义默认类属性，windo_size最多接受前10值，treshold告警权值，10个里有7个就会触发，下一个是CD
    def __init__(self, window_size=10, threshold_ratio=0.7, cooldown=60):
        self.window_size = window_size
        self.threshold_ratio = threshold_ratio
        self.cooldown = cooldown
        # 最多接受十个值，超过10个就会删除旧的
        self.values = deque(maxlen=window_size)
        self.last_alert_time = 0.0

    # 创建新采样点
    def add(self, values: float, threshold: float) -> bool:
        self.values.append(values)

        # 窗口不满就不告警
        if len(self.values) < self.window_size:
            return False, None

        over_count = sum(1 for v in self.values if v >= threshold)
        ratio = over_count / self.window_size
        stats = {
            "count": len(self.values),
            "avg": round(sum(self.values) / len(self.values), 1),
            "max": round(max(self.values), 1),
            "over": over_count,
        }

        # 判断条件\
        current_time = time.time()
        if ratio >= self.threshold_ratio and (current_time - self.last_alert_time) >= self.cooldown:
            self.last_alert_time = current_time
            # 清空告警窗口
            self.values.clear()
            return True, stats
        return False, None


def main():
    cfg = load_config()
    port_num(8000)

    # 告警聚合配置
    AGGREGATE_WINDOW = int(os.getenv('AGGREGATE_WINDOW', '300'))    # 5分钟
    aggregator = AlertAggregator(window_size=AGGREGATE_WINDOW)
    print(f'[启动]告警聚合窗口：{AGGREGATE_WINDOW}秒')

    # 滑动窗口配置
    WINDOW_SIZE = int(os.getenv('ALERT_WINDOW_SIZE', '10'))
    # 超过阈值占比70%才告警
    THRESHOLD_RATIO = float(os.getenv('ALERT_THRESHOLD_RATIO', '0.7'))
    # 告警CD
    ALERT_COOLDOWN = int(os.getenv('ALERT_COOLDOWN', '60'))

    # 为指标创建独立窗口
    cpu_window = SildWindows(WINDOW_SIZE, THRESHOLD_RATIO, ALERT_COOLDOWN)
    mem_window = SildWindows(WINDOW_SIZE, THRESHOLD_RATIO, ALERT_COOLDOWN)
    disk_window = SildWindows(WINDOW_SIZE, THRESHOLD_RATIO, ALERT_COOLDOWN)

    # last_alert_time = {'cpu': 0.0, 'free': 0.0, 'disk': 0.0}
    node_name = os.getenv('HOSTNAME', 'unknown')

    try:
        while True:
            # current_time = time.time()
            system_time = time.strftime('%Y-%m-%d %H:%M:%S')

            # 采集指标
            cpu_use = psutil.cpu_percent(interval=1)
            free_use = psutil.virtual_memory().percent
            disk_use = psutil.disk_usage(cfg['DISK_PATH']).percent

            # 磁盘 I/O
            disk1 = psutil.disk_io_counters()
            time.sleep(1)
            disk2 = psutil.disk_io_counters()
            disk_io_write = (disk2.write_bytes - disk1.write_bytes) // (1000 ** 2)
            disk_io_write_count = disk2.write_count - disk1.write_count
            disk_io_read = (disk2.read_bytes - disk1.read_bytes) // (1000 ** 2)
            disk_io_read_count = disk2.read_count - disk1.read_count

            # 网络 I/O
            net1 = psutil.net_io_counters()
            time.sleep(1)
            net2 = psutil.net_io_counters()
            network_resv_b = (net2.bytes_recv - net1.bytes_recv) // (1000 ** 2)
            network_send_b = (net2.bytes_sent - net1.bytes_sent) // (1000 ** 2)

            # 输出控制台
            print(
                f'当前时间{system_time}       CPU使用率{cpu_use}%    内存使用率{free_use}%     '
                f'磁盘使用率{disk_use}%       磁盘读写{disk_io_read:.1f}MB/s {disk_io_write:.1f}MB/s    '
                f'次数{disk_io_read_count}  {disk_io_write_count}    '
                f'网络发送字节为{network_send_b}Mb/s 接受字节为{network_resv_b}Mb/s'
            )

            # 日志
            # logger_alter(None, system_time, cpu_use, free_use, disk_use)

            # Prometheus 指标
            cpu_use_gauge.set(cpu_use)
            free_use_gauge.set(free_use)
            disk_use_gauge.set(disk_use)
            disk_read_gauge.set(disk_io_read)
            disk_write_gauge.set(disk_io_write)
            network_send_gauge.set(network_send_b)
            network_resv_gauge.set(network_resv_b)

            # MySQL 写入
            if cfg['cursor']:
                insert_data(cfg['cursor'], cfg['conn'], {
                    'timestamp': system_time,
                    'cpu_use': cpu_use, 'free_use': free_use, 'disk_use': disk_use,
                    'disk_io_read': disk_io_read, 'disk_io_write': disk_io_write,
                    'disk_io_read_count': disk_io_read_count,
                    'disk_io_write_count': disk_io_write_count,
                    'network_send_b': network_send_b,
                    'network_resv_b': network_resv_b
                })

            # ========== 告警判断 ==========

            # 创建告警判断
            cpu_alert, cpu_stats = cpu_window.add(cpu_use, cfg['CPU_MAXUSE'])
            mem_alert, mem_stats = mem_window.add(free_use, cfg['MEMORY_MAXUSE'])
            disk_alert, disk_stats = disk_window.add(disk_use, cfg['DISK_MAXUSE'])

            # CPU告警
            if cpu_alert:
                history = get_history(cfg['cursor'], 'cpu_usage')
                advice = AI.ai_monitor('CPU', cpu_use, cfg['CPU_MAXUSE'], history)
                print(f'[告警] CPU持续超过阈值{cfg["CPU_MAXUSE"]}%，当前{cpu_use}%，'
                      f'窗口内超阈值 {cpu_stats["over"]}/{cpu_stats["count"]} 次')

                # 加入聚合器，不直接发送
                full_alert = aggregator.add_alert(
                    node=node_name, resource='CPU', value=cpu_use, threshold=cfg['CPU_MAXUSE'], timestamp=system_time
                )
                # log_alter(cfg['URL'], system_time, 'CPU', cfg['CPU_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': 'CPU', 'value': cpu_use,
                        'threshold': cfg['CPU_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })

            if mem_alert:
                history = get_history(cfg['cursor'], 'memory_usage')
                advice = AI.ai_monitor('内存', free_use, cfg['MEMORY_MAXUSE'], history)
                print(f'[告警] 内存持续超过阈值{cfg["MEMORY_MAXUSE"]}%，当前{free_use}%，'
                      f'窗口内超阈值 {mem_stats["over"]}/{mem_stats["count"]} 次')

                aggregator.add_alert(
                    node=node_name, resource='内存',
                    value=free_use, threshold=cfg['MEMORY_MAXUSE'],
                    timestamp=system_time
                )

                # log_alter(cfg['URL'], system_time, '内存', cfg['MEMORY_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': '内存', 'value': free_use,
                        'threshold': cfg['MEMORY_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })

            if disk_alert:
                history = get_history(cfg['cursor'], 'disk_usage')
                advice = AI.ai_monitor('磁盘', disk_use, cfg['DISK_MAXUSE'], history)
                print(f'[告警] 磁盘持续超过阈值{cfg["DISK_MAXUSE"]}%，当前{disk_use}%，'
                      f'窗口内超阈值 {disk_stats["over"]}/{disk_stats["count"]} 次')

                aggregator.add_alert(
                    node=node_name, resource='磁盘',
                    value=disk_use, threshold=cfg['DISK_MAXUSE'],
                    timestamp=system_time
                )

                # log_alter(cfg['URL'], system_time, '磁盘', cfg['DISK_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': '磁盘', 'value': disk_use,
                        'threshold': cfg['DISK_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })
            # 调用AI进行分析处理，alerts就是汇聚告警参数
            if aggregator.should_flush():
                alerts = aggregator.flush()
                print(f'[聚合] 窗口到期，聚合 {len(alerts)} 条告警')

                if alerts:
                    # AI模块获取参数进行分析
                    aggregate_advice = AI.ai_aggregate(alerts)
                    # 发送URL请求
                    log_alter_aggregated(cfg['URL'], alerts, aggregate_advice)

            time.sleep(cfg['INTERVAL'])

    except KeyboardInterrupt:
        print('采集结束')
        if cfg['conn']:
            cfg['conn'].close()


if __name__ == '__main__':
    main()
