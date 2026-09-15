import prometheus_client

cpu_use_gauge = prometheus_client.Gauge("CPU_use_percent", "CPU的使用率")
free_use_gauge = prometheus_client.Gauge("Free_use_percent", "内存使用率")
disk_use_gauge = prometheus_client.Gauge("Disk_use_percent", "磁盘使用率")
disk_read_gauge = prometheus_client.Gauge("Disk_read_MB", "磁盘读取数")
disk_write_gauge = prometheus_client.Gauge("Disk_write_MB", "磁盘写入数")
network_send_gauge = prometheus_client.Gauge("Network_send_Mb", "网络发送字节数")
network_resv_gauge = prometheus_client.Gauge("Network_resv_Mb", "网络接受字节数")


def port_num(port=8000):
    prometheus_client.start_http_server(port)
    print(f"Prometheus used port{port}")
