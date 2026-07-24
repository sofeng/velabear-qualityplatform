ARG BASE_IMAGE=local/testhub-platform-backend-bundle:20260424-1
FROM ${BASE_IMAGE}

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple docker==7.1.0
