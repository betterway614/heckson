# YOU TIME 数据库快速开始

## 环境要求

- Docker 中运行 PostgreSQL (端口 5432)
- Docker 中运行 Redis (端口 6379)
- Python 3.11+

## 快速初始化

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据库初始化
python scripts/init_db.py
```

## 验证安装

```bash
# 检查数据库状态
python scripts/check_db.py
```

预期输出：
- 数据库连接成功
- 5 个表全部存在
- users 表有 1 条测试记录

## 启动应用

```bash
# 启动 FastAPI 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档: http://localhost:8000/docs

## 测试 API

```bash
# 创建记忆
curl -X POST "http://localhost:8000/api/memories/" \
  -H "Content-Type: application/json" \
  -d '{"content_text": "今天天气真好", "memory_date": "2025-01-16", "mood_tag": "happy"}'

# 获取记忆列表
curl "http://localhost:8000/api/memories/"
```

## 数据库管理

```bash
# 检查状态
python scripts/check_db.py

# 重置数据库（删除所有数据）
python scripts/reset_db.py

# 使用 SQL 脚本
psql -U betterway -d you_time -f scripts/init_db.sql
```

## 故障排除

### 连接失败

检查 Docker 容器：
```bash
docker ps | grep postgresql
docker ps | grep redis
```

### 表不存在

重新运行初始化：
```bash
python scripts/init_db.py
```

### 数据清空

重置数据库：
```bash
python scripts/reset_db.py
```
