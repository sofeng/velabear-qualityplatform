# AI开发服务访问问题排查指南

## 问题描述
AI开发完成后，部署的服务地址（如 http://192.168.124.10:8081）无法访问。

## 可能原因及解决方案

### 1. Docker容器未正常运行

**排查命令**:
```bash
# 查看所有AI开发相关的容器
docker ps -a | findstr aidev

# 查看容器详细信息
docker inspect <container_id>

# 查看容器日志
docker logs <container_id>
```

**解决方案**:
如果容器已停止，需要重启容器：
```bash
docker start <container_id>
```

### 2. 服务未在容器内启动

**排查步骤**:
```bash
# 进入容器
docker exec -it <container_id> bash

# 检查服务进程
ps aux | grep node  # 或其他服务进程名
ps aux | grep python
ps aux | grep java

# 检查端口监听
netstat -tlnp | grep 8081  # 替换为实际端口

# 手动启动服务（在容器内）
cd /workspace/code
npm run dev  # 或其他启动命令
```

### 3. Docker端口映射问题

**问题**: Docker容器端口未正确映射到主机

**排查**:
```bash
# 查看容器端口映射
docker port <container_id>
```

**解决方案**:
如果端口映射不正确，需要重新创建容器并指定正确的端口映射：
```bash
docker run -d -p 8081:8080 <image_name>
```

### 4. 防火墙阻止访问

**Windows防火墙排查**:
```powershell
# 检查防火墙规则
netsh advfirewall firewall show rule name=all | findstr 8081

# 添加防火墙规则允许8081端口
netsh advfirewall firewall add rule name="AI Dev Service" dir=in action=allow protocol=TCP localport=8081
```

**Linux防火墙排查**:
```bash
# 检查firewalld
sudo firewall-cmd --list-ports

# 添加端口
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --reload
```

### 5. 网络IP地址不正确

**问题**: 生成的服务URL使用了错误的IP地址

**当前代码修复**: 已更新 `get_docker_host_ip()` 函数，优先使用实际的网络IP（192.168.x.x 或 10.x.x.x）

**手动检查本机IP**:
```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
ip addr show
```

### 6. Docker Desktop for Windows网络问题

**问题**: Docker Desktop for Windows使用NAT网络，可能导致容器服务无法从主机访问

**解决方案**:
1. 确保Docker Desktop正在运行
2. 使用 `localhost` 或 `127.0.0.1` 而不是主机IP访问服务：
   ```
   http://localhost:8081
   ```

3. 或者配置Docker使用桥接网络

### 7. 服务启动延迟

**问题**: 服务需要较长时间启动，但代码只等待5秒

**排查**:
```bash
# 进入容器查看服务日志
docker exec -it <container_id> cat /workspace/service.log

# 或实时查看日志
docker exec -it <container_id> tail -f /workspace/service.log
```

**临时解决方案**: 等待更长时间后再访问服务

**代码已优化**: 添加了服务可用性检查

## 完整排查流程

### 步骤1: 获取容器信息
```bash
# 从数据库获取容器ID
python manage.py shell
>>> from apps.ai_development.models import AIDevelopmentTask
>>> task = AIDevelopmentTask.objects.filter(status='completed').last()
>>> print(f"容器ID: {task.container_id}")
>>> print(f"服务URL: {task.service_url}")
```

### 步骤2: 检查容器状态
```bash
docker ps -a | findstr <container_id前4位>
```

### 步骤3: 检查容器内服务
```bash
docker exec -it <container_id> bash
cd /workspace/code
ls -la
cat /workspace/service.log
```

### 步骤4: 测试端口连通性
```bash
# Windows
Test-NetConnection -ComputerName 192.168.124.10 -Port 8081

# Linux/Mac
telnet 192.168.124.10 8081
nc -zv 192.168.124.10 8081
```

### 步骤5: 查看容器日志
```bash
docker logs <container_id> --tail 100
```

## 建议的修复措施

### 修复1: 确保容器不会被自动删除
当前代码已修改为：失败的容器会被清理，成功的容器会保留以供审计。

### 修复2: 使用Docker Compose管理服务
创建 `docker-compose.yml`:
```yaml
version: '3.8'
services:
  ai-dev-service:
    image: testhub/ai-dev:latest
    ports:
      - "8081:8080"
    volumes:
      - aidev_volume:/workspace
    restart: unless-stopped
```

### 修复3: 使用专用的服务管理进程
在容器内使用 `supervisord` 或 `pm2` 管理服务进程，确保服务持续运行。

## 最佳实践

1. **持久化容器**: 成功的开发任务容器应该保持运行状态
2. **健康检查**: 定期检查服务是否可访问
3. **日志记录**: 保存完整的服务启动日志
4. **端口管理**: 避免端口冲突，使用动态端口分配
5. **网络配置**: 使用Docker网络而不是主机网络

## 代码改进清单

- [x] 优化 `get_docker_host_ip()` 函数，正确获取Windows主机IP
- [x] 添加服务可用性检查
- [x] 记录服务访问测试结果
- [ ] 添加服务健康检查端点
- [ ] 实现服务自动重启机制
- [ ] 添加端口冲突检测
- [ ] 支持自定义服务URL

## 快速诊断命令

```bash
# 一键诊断脚本
echo "=== Docker容器检查 ==="
docker ps -a | grep aidev

echo "=== 端口监听检查 ==="
netstat -ano | findstr :8081

echo "=== 防火墙检查 ==="
netsh advfirewall firewall show rule name=all | findstr 8081

echo "=== 本机IP地址 ==="
ipconfig | findstr IPv4
```

## 联系支持

如果以上方法都无法解决问题，请提供以下信息：
1. 容器ID和状态 (`docker ps -a`)
2. 容器日志 (`docker logs <container_id>`)
3. 服务日志 (`docker exec <container_id> cat /workspace/service.log`)
4. 网络配置 (`ipconfig` / `ifconfig`)
5. 任务详细信息（从AI开发任务详情页面）
