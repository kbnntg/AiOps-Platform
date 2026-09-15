def get_history(cursor, resource, mi=10):
    if not cursor:
        return "无历史数据"
    try:
        sql = f"SELECT timestamp, {resource} FROM metrics WHERE timestamp > NOW() - INTERVAL %s MINUTE ORDER BY timestamp DESC LIMIT 10"
        cursor.execute(sql, (mi,))
        rows = cursor.fetchall()
        if not rows:
            return "历史数据为空"
        return "\n".join([f"{r[0]} : {r[1]}%" for r in rows])
    except Exception as e:
        print(f"查询历史数据失败: {e}")
        return "历史数据查询失败"
