# 修复 TruLens Dashboard Decimal 分位数错误

## 任务目标

修复 Windows 环境中 TruLens Dashboard Trends 页面计算延迟 P90/P99 时，由 PostgreSQL Decimal 与 NumPy 浮点插值不兼容引起的错误：

`	ext
TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
`

## 完成情况

- [x] 确认错误发生在 TruLens get_app_metric_trends 的延迟分位数计算。
- [x] 确认 PostgreSQL 延迟字段返回 Decimal，NumPy 分位数插值要求浮点类型。
- [x] 在项目侧 Dashboard 兼容启动器中增加 Decimal 到 float 的局部适配。
- [x] 保留此前 Windows 日期格式 %-d 到 %#d 的兼容处理。
- [x] 新增 Decimal 分位数回归测试。
- [x] 通过语法检查和评测层兼容测试。

## 验证结果

`	ext
15 passed, 1 warning
Decimal 分位数复现结果正常
`

## 使用方式

重启 Dashboard 后使用原命令：

`powershell
python RAG-assessment/run_trulens_dashboard.py
`

然后重新进入 Trends 页面。
