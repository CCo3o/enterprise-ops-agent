# 订单接口 500 故障复盘

历史上订单接口出现 500 时，常见模式是连接池使用数达到上限，同时日志出现 `database connection timeout` 或 `connection pool exhausted`。排查顺序应为连接池、数据库慢查询/锁等待、数据库网络，最后再检查应用重试配置。
