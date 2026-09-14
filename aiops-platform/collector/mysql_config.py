def insert_data(cursor, conn, data):
    sql = """
        INSERT INTO metrics
        (timestamp, cpu_usage, memory_usage, disk_usage, disk_read_mb, disk_write_mb,
         disk_read_count, disk_write_count, net_send_mb, net_resv_mb)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(sql, (
            data['timestamp'], data['cpu_use'], data['free_use'], data['disk_use'],
            data['disk_io_read'], data['disk_io_write'],
            data['disk_io_read_count'], data['disk_io_write_count'],
            data['network_send_b'], data['network_resv_b']
        ))
        conn.commit()
    except Exception as e:
        print(f"写入 metrics 失败: {e}")


def insert_alert_history(cursor, conn, data):
    """告警历史写入，供 Web 平台展示"""
    sql = """
        INSERT INTO alert_history (resource, value, threshold, node, ai_advice)
        VALUES (%s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(sql, (
            data['resource'], data['value'], data['threshold'],
            data['node'], data['ai_advice']
        ))
        conn.commit()
    except Exception as e:
        print(f"写入 alert_history 失败: {e}")
