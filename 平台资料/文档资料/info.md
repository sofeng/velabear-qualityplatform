
## 测试服务器
测试服务器地址：172.31.119.49
账号：root
密码：Hkfgzbpa@@2025

前端平台首页：http://172.31.119.49:31080/
API 文档：http://172.31.119.49:31080/api/docs/
后端直连文档地址：http://172.31.119.49:38000/api/docs/

账号：admin
密码：Testhub@20260319

## 本地
前端入口是 http://127.0.0.1:3000/
后端是 http://127.0.0.1:8000/
Django 管理后台是 http://127.0.0.1:8000/admin/login/
我已经验证过后端管理页返回 200，前端首页可访问，前端代理到后端的 http://127.0.0.1:3000/api/schema/ 和 http://127.0.0.1:3000/api/docs/ 也都返回 200。

当前进程：

后端 python PID: 44676
前端 node PID: 18476
登录账号我也一并重置成了：

用户名：admin
密码：Testhub@20260319


### SQLite
  服务运行状态：
  - 后端服务: http://127.0.0.1:8000/ (Django)
  - 前端服务: http://localhost:3000/ (Vue + Vite)

  您现在可以：
  1. 访问 http://localhost:3000/ 使用前端界面
  2. 访问 http://127.0.0.1:8000/admin/ 访问Django管理后台（需先创建超级用户）
  3. 访问 http://127.0.0.1:8000/api/docs/ 查看API文档

  如需创建管理员账号，可运行：
  python manage.py createsuperuser

  注意：两个服务都在后台运行中，您可以随时通过 /tasks 命令查看运行状态。

✻ Worked for 1m 58s

> 登录账号密码是多少

● 当前数据库是全新的，还没有用户账号。我来帮您创建一个管理员账号。

● Bash(python manage.py shell -c "from apps.users.models import User; User.objects.create_superuser(username='admin', email='admin@example.com', password='admin123', p…)
  ⎿  (No content)

● 已为您创建管理员账号，登录信息如下：

  登录凭证：
  - 用户名：admin
  - 密码：admin123
  - 邮箱：admin@example.com

  您可以使用以上凭证登录：
  - 前端界面：http://localhost:3000/
  - Django管理后台：http://127.0.0.1:8000/admin/

  ## docker desktop mysql-testhub
  选项1：使用默认MySQL配置
  - 用户名: root
  - 密码: (空密码或您的root密码)
  - 数据库名: testhub
  - 主机: 127.0.0.1

  ## 自动模式
  完全授权模式（也叫 "YOLO 模式"）的参数是：

```
claude --dangerously-skip-permissions
```

如果你想用非交互式的命令模式（直接传入提示词一次性执行），再加上 `-p` 参数：

```
claude --dangerously-skip-permissions -p "你的任务描述"
```

**但请注意风险**：这个 flag 会让 Claude Code 在没有任何权限提示的情况下完全自主执行，包括文件修改、删除和系统命令。已经有开发者因此丢失了整个 home 目录。

**安全建议：**

1. 使用前先用 git 做一个快照：`git add -A && git commit -m "checkpoint"`
2. Anthropic 现在推出了更安全的 **auto mode**，作为 `--dangerously-skip-permissions` 的替代方案，它会用一个分类器模型在每个操作前自动判断是否安全。启动方式是 `claude --permission-mode auto`（不过目前需要 Team/Enterprise/API 计划，以及 Sonnet 4.6 或 Opus 4.6 模型）。
3. 如果一定要用完全跳过权限模式，最好在 Docker 容器里运行，而不是直接在本机。

