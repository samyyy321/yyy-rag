# 修复 TruLens Dashboard Windows 趋势页日期格式错误

## 任务目标

修复 Windows 环境点击 TruLens Dashboard 的 Trends 页面时，由 Unix 专用日期格式 %-d 引起的 ValueError: Invalid format string。

## 完成情况

- [x] 确认错误来自 	rulens-dashboard==2.14.0 的 Trends 页面。
- [x] 新增项目侧兼容启动器，不直接修改 Python 环境中的第三方包。
- [x] 在运行时复制官方 Trends 页面，并将 %-d 替换为 Windows 支持的 %#d。
- [x] 修改 Dashboard 启动命令，使其使用兼容启动器。
- [x] 新增 Windows 日期格式回归测试。
- [x] 完成 Dashboard HTTP 启动冒烟测试。
- [x] 将兼容运行目录加入 .gitignore。

## 验证结果

`	ext
14 passed, 1 warning
Dashboard 临时启动 HTTP 状态：200
兼容页面：不包含 %-d，包含 %#d
`

## 使用方式

继续使用原来的命令启动 Dashboard：

`powershell
python RAG-assessment/run_trulens_dashboard.py
`

启动后进入 Trends 页面即可使用。
