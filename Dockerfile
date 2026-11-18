FROM python:3.12-slim

# 容器里没有本机的镜像配置，显式指定 PyPI 镜像；否则 build 依赖会去 pypi.org 超时
ENV UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/ \
    UV_HTTP_TIMEOUT=120

# uv 的官方镜像里带着可执行文件，直接拷过来；上线时把 latest 换成固定版本
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
# 先只拷依赖清单：代码改了而依赖没变时，这一层能用缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "quarry.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]