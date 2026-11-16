-- 容器第一次初始化时执行，只做一件事：装扩展。建表交给 Alembic。
CREATE EXTENSION IF NOT EXISTS vector;