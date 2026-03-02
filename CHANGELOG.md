# SSL Monitor — 开发成果总结

## 本次新增功能

### 1. 公开探针大屏 `/status`
- 无需登录即可访问的监控状态页
- 表格布局 + 亮色/暗色主题切换
- 域名脱敏显示（每段只留首尾字符）
- 按标签筛选 + 到期天数筛选（≤7天/≤15天/≤30天）
- 60秒自动刷新

**涉及文件**:
- [public.py](file:///c:/workspace/ssl-monitor/backend/routers/public.py) — 后端 API
- [PublicStatus.vue](file:///c:/workspace/ssl-monitor/frontend/src/views/PublicStatus.vue) — 前端页面

### 2. 域名站点名称（Name Alias）
- 数据库新增 `name` 列
- 添加域名时可填写站点名称（如"公司官网"）
- 域名卡片优先显示站点名称
- 探针大屏展示站点名称列

**涉及文件**: `models.py`, `schemas.py`, `domains.py`, `api.ts`, `Dashboard.vue`

### 3. 域名编辑功能
- 新增 `PUT /api/domains/{id}` 编辑接口
- Dashboard 域名卡片新增编辑按钮（铅笔图标）
- 可修改站点名称、标签、备注

### 4. 标签联想/自动补全
- 标签输入从 `a-input-tag` 升级为 `a-select` (multiple + allow-create + allow-search)
- 输入时自动联想已有标签，也可直接创建新标签

### 5. 批量操作
- 勾选多个域名后可执行批量检测、批量删除、批量配置告警
- 底部悬浮操作栏

## Bug 修复
- 修复 `check-one` 接口返回原始 dict 导致缺少 `id` 字段的问题
- 修复 `CertResultOut` 中 `san` 字段未自动解析 JSON 字符串的问题
- 修复 `DomainIn` 被误改名为 `DomainBase` 导致 ImportError
- 修复数据库迁移脚本使用错误的数据库文件路径

## 项目清理
- 删除临时文件：`test_public.py`, `add_name_col.py`
- 删除废弃的 `venv_old` 目录
- 重写 `README.md`，更新项目结构和功能说明
