-- YOU TIME 数据库初始化脚本
-- 使用方法: psql -U betterway -f scripts/init_db.sql

-- 创建数据库（如果不存在）
-- 注意：需要先连接到 postgres 数据库执行
-- CREATE DATABASE you_time;

-- 连接到 you_time 数据库后执行以下内容

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    openid VARCHAR(128) UNIQUE NOT NULL,
    unionid VARCHAR(128),
    nickname VARCHAR(64),
    avatar VARCHAR(512),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid);

-- 记忆表
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_text TEXT,
    memory_date DATE NOT NULL,
    mood_tag VARCHAR(32),
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);

-- 媒体表
CREATE TABLE IF NOT EXISTS media (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(16) NOT NULL,
    original_filename VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_memory_id ON media(memory_id);

-- 生成任务表
CREATE TABLE IF NOT EXISTS generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_ids JSONB NOT NULL,
    type VARCHAR(16) NOT NULL,
    style_key VARCHAR(32) NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(32),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    -- 两阶段工作流字段
    stage VARCHAR(32) DEFAULT 'vlm_parse',
    vlm_raw_metadata JSONB,
    user_edited_prompt TEXT,
    llm_polished_prompt TEXT,
    final_prompt TEXT,
    prompt_confirmed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_generations_user_id ON generations(user_id);
CREATE INDEX IF NOT EXISTS idx_generations_status ON generations(status);

-- 输出表
CREATE TABLE IF NOT EXISTS outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generation_id UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(16) NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outputs_generation_id ON outputs(generation_id);

-- 创建测试用户（用于开发）
INSERT INTO users (id, openid, nickname) VALUES
    ('00000000-0000-0000-0000-000000000001', 'test_openid_001', '测试用户')
ON CONFLICT (openid) DO NOTHING;

-- 完成提示
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成！';
END $$;
