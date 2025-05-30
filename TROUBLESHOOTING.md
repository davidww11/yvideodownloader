# 故障排除指南 / Troubleshooting Guide

## 本地开发环境问题

### 问题：前端显示"Failed to fetch"错误

这个错误通常表示前端无法连接到后端API服务器。

#### 解决步骤：

1. **检查服务器是否运行**
   ```bash
   # 启动服务器（使用8000端口避免冲突）
   PORT=8000 python3 run.py
   ```

2. **验证API端点**
   ```bash
   # 测试健康检查端点
   curl http://localhost:8000/api/health
   
   # 预期响应：
   # {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}
   ```

3. **测试完整API**
   ```bash
   # 测试下载端点
   curl -X POST http://localhost:8000/api/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://x.com/username/status/123456789", "format": "mp4"}'
   ```

4. **使用调试页面**
   - 访问：`http://localhost:8000/debug`
   - 点击"Test Health API"按钮
   - 检查网络信息和错误详情

### 问题：端口冲突

```
Address already in use
Port 5000 is in use by another program
```

#### 解决方案：

1. **使用不同端口**
   ```bash
   PORT=8000 python3 run.py
   ```

2. **macOS用户：禁用AirPlay Receiver**
   - 系统偏好设置 > 共享
   - 取消勾选"AirPlay接收器"

### 问题：缺少依赖

```
Missing dependency: No module named 'flask'
```

#### 解决方案：

1. **安装开发依赖**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **或手动安装**
   ```bash
   pip install Flask Flask-CORS yt-dlp requests Werkzeug
   ```

### 问题：CORS错误

在浏览器控制台看到：
```
Access to fetch at 'http://localhost:8000/api/download' from origin 'http://localhost:8000' has been blocked by CORS policy
```

#### 解决方案：

这个问题在我们的代码中应该不会出现，因为已经配置了Flask-CORS。如果遇到：

1. **检查Flask-CORS是否安装**
   ```bash
   pip show flask-cors
   ```

2. **重启服务器**
   ```bash
   # 停止服务器 (Ctrl+C)
   # 重新启动
   PORT=8000 python3 run.py
   ```

## 网络和URL问题

### 问题：无法下载特定视频

```
No video could be found in this content
```

#### 可能原因：

1. **URL格式错误**
   - ✅ 正确：`https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - ✅ 正确：`https://youtu.be/dQw4w9WgXcQ`
   - ❌ 错误：`https://www.youtube.com/` (不包含视频ID)

2. **视频不存在或已删除**
   - 视频可能已被删除
   - 请确认视频确实存在且可访问

3. **私人视频或受限制的视频**
   - 无法访问私人视频的媒体内容
   - 某些地区限制的视频无法下载

### 问题：视频质量选项为空

```