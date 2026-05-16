# YOU TIME 数据库管理脚本

## 前置条件

1. Docker 中已运行 PostgreSQL (端口 5432)
2. Docker 中已运行 Redis (端口 6379)
3. 已安装 Python 依赖: `pip install -r requirements.txt`

## 脚本说明

### 1. init_db.py - 初始化数据库

创建数据库、表结构和测试数据。

```bash
python scripts/init_db.py
```

功能：
- 创建数据库 `you_time`（如果不存在）
- 创建所有表：users, memories, media, generations, outputs
- 插入测试用户（ID: 00000000-0000-0000-0000-000000000001）

### 2. reset_db.py - 重置数据库

删除所有表并重新创建。

```bash
python scripts/reset_db.py
```

⚠️ **警告：此操作会删除所有数据！**

### 3. check_db.py - 检查数据库状态

显示数据库连接状态、表结构和数据统计。

```bash
python scripts/check_db.py
```

### 4. init_db.sql - SQL 初始化脚本

纯 SQL 版本的初始化脚本，可直接使用 psql 执行。

```bash
# 创建数据库
psql -U postgres -c "CREATE DATABASE you_time"

# 执行初始化脚本
psql -U postgres -d you_time -f scripts/init_db.sql
```

## 数据库配置

默认配置（可在 `.env` 文件中修改）：

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/you_time
REDIS_URL=redis://localhost:6379/0
```

## 表结构

### users - 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| openid | VARCHAR(128) | 微信 OpenID |
| unionid | VARCHAR(128) | 微信 UnionID |
| nickname | VARCHAR(64) | 昵称 |
| avatar | VARCHAR(512) | 头像 URL |
| phone | VARCHAR(20) | 手机号 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### memories - 记忆表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户 ID |
| content_text | TEXT | 文字内容 |
| memory_date | DATE | 记忆日期 |
| mood_tag | VARCHAR(32) | 情绪标签 |
| metadata_json | JSONB | 元数据 |
| created_at | TIMESTAMP | 创建时间 |

### media - 媒体表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| memory_id | UUID | 记忆 ID |
| file_path | VARCHAR(512) | 文件路径 |
| file_type | VARCHAR(16) | 文件类型 (image/audio) |
| original_filename | VARCHAR(256) | 原始文件名 |
| created_at | TIMESTAMP | 创建时间 |

### generations - 生成任务表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户 ID |
| memory_ids | JSONB | 记忆 ID 列表 |
| type | VARCHAR(16) | 类型 (diary/comic) |
| style_key | VARCHAR(32) | 风格标识 |
| status | VARCHAR(32) | 状态 |
| progress | INTEGER | 进度 (0-100) |
| current_step | VARCHAR(32) | 当前步骤 |
| error_message | TEXT | 错误信息 |
| stage | VARCHAR(32) | 工作流阶段 |
| vlm_raw_metadata | JSONB | VLM 原始结果 |
| user_edited_prompt | TEXT | 用户编辑的提示词 |
| llm_polished_prompt | TEXT | LLM 润色的提示词 |
| final_prompt | TEXT | 最终提示词 |
| prompt_confirmed | BOOLEAN | 是否确认 |
| created_at | TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP | 完成时间 |

### outputs - 输出表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| generation_id | UUID | 生成任务 ID |
| file_path | VARCHAR(512) | 文件路径 |
| file_type | VARCHAR(16) | 文件类型 (image/audio/video) |
| metadata | JSONB | 元数据 |
| created_at | TIMESTAMP | 创建时间 |

## 故障排除

### 连接失败

1. 检查 PostgreSQL 是否运行：`docker ps | grep postgres`
2. 检查端口是否正确：`netstat -an | grep 5432`
3. 检查用户名密码是否正确

### 表已存在

如果提示表已存在，可以使用 reset_db.py 重置：

```bash
python scripts/reset_db.py
```

### 权限不足

确保 PostgreSQL 用户有创建数据库的权限，或手动创建数据库：

```bash
psql -U postgres -c "CREATE DATABASE you_time"
```
