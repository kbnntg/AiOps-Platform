import time
import os
import psutil
import AI
from load_config import load_config
from Prometheus_config import (
    cpu_use_gauge, free_use_gauge, disk_use_gauge,
    disk_read_gauge, disk_write_gauge,
    network_send_gauge, network_resv_gauge, port_num
)
from mysql_config import insert_data, insert_alert_history
from alter import log_alter
from history import get_history
from logger import logger_alter


def main():
    cfg = load_config()
    port_num(8000)

    last_alert_time = {'cpu': 0.0, 'free': 0.0, 'disk': 0.0}
    node_name = os.getenv('HOSTNAME', 'unknown')

    try:
        while True:
            current_time = time.time()
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
            logger_alter(None, system_time, cpu_use, free_use, disk_use)

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
            if cpu_use >= cfg['CPU_MAXUSE'] and (current_time - last_alert_time['cpu']) >= cfg['ALTER_INTERVAL']:
                history = get_history(cfg['cursor'], 'cpu_usage')
                advice = AI.ai_monitor('CPU', cpu_use, cfg['CPU_MAXUSE'], history)
                print(f'CPU使用率超过阈值{cfg["CPU_MAXUSE"]}%,当前使用率{cpu_use}%')
                log_alter(cfg['URL'], system_time, 'CPU', cfg['CPU_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': 'CPU', 'value': cpu_use,
                        'threshold': cfg['CPU_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })
                last_alert_time['cpu'] = current_time

            if free_use >= cfg['MEMORY_MAXUSE'] and (current_time - last_alert_time['free']) >= cfg['ALTER_INTERVAL']:
                history = get_history(cfg['cursor'], 'memory_usage')
                advice = AI.ai_monitor('内存', free_use, cfg['MEMORY_MAXUSE'], history)
                print(f'内存使用率超过阈值{cfg["MEMORY_MAXUSE"]}%,当前使用率{free_use}%')
                log_alter(cfg['URL'], system_time, '内存', cfg['MEMORY_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': '内存', 'value': free_use,
                        'threshold': cfg['MEMORY_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })
                last_alert_time['free'] = current_time

            if disk_use >= cfg['DISK_MAXUSE'] and (current_time - last_alert_time['disk']) >= cfg['ALTER_INTERVAL']:
                history = get_history(cfg['cursor'], 'disk_usage')
                advice = AI.ai_monitor('磁盘', disk_use, cfg['DISK_MAXUSE'], history)
                print(f'磁盘使用率超过阈值{cfg["DISK_MAXUSE"]}%,当前使用率{disk_use}%')
                log_alter(cfg['URL'], system_time, '磁盘', cfg['DISK_MAXUSE'], advice)
                if cfg['cursor']:
                    insert_alert_history(cfg['cursor'], cfg['conn'], {
                        'resource': '磁盘', 'value': disk_use,
                        'threshold': cfg['DISK_MAXUSE'],
                        'node': node_name, 'ai_advice': advice
                    })
                last_alert_time['disk'] = current_time

            time.sleep(cfg['INTERVAL'])

    except KeyboardInterrupt:
        print('采集结束')
        if cfg['conn']:
            cfg['conn'].close()


if __name__ == '__main__':
    main()
