#!/bin/bash
# 构建AI开发Docker镜像的脚本

set -e

IMAGE_NAME="testhub/ai-dev"
IMAGE_TAG="latest"

echo "开始构建AI开发Docker镜像..."
echo "镜像名称: ${IMAGE_NAME}:${IMAGE_TAG}"

# 构建镜像
docker build \
    -f deploy/Dockerfile.ai-dev \
    -t ${IMAGE_NAME}:${IMAGE_TAG} \
    .

echo "镜像构建完成!"
echo ""
echo "验证镜像..."
docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} git --version
docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} node --version
docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} python --version
docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} python -c "import anthropic; print('anthropic', anthropic.__version__)"
docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} playwright --version

echo ""
echo "镜像构建并验证成功!"
echo "可以使用以下命令运行容器:"
echo "  docker run -it --rm ${IMAGE_NAME}:${IMAGE_TAG}"
