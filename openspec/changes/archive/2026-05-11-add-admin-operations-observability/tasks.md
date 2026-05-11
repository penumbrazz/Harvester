## 1. API Tests

- [x] 1.1 编写 dashboard summary API 测试，覆盖关键计数和不返回 raw payload
- [x] 1.2 编写 crawl run 列表 API 测试，覆盖分页、状态筛选、source 筛选和错误字段
- [x] 1.3 编写 job 列表 API 测试，覆盖 job_type、status、lane、source 筛选和 attempts/lock 字段

## 2. Backend Implementation

- [x] 2.1 新增 dashboard summary router 或 endpoint，聚合 source、crawl、job、content、failure、audit 指标
- [x] 2.2 新增 crawl run list endpoint，返回前端表格字段并限制分页
- [x] 2.3 扩展 queue router，新增 job list endpoint，同时保留现有 `/queue/status`
- [x] 2.4 确认所有 read API 都需要 API token 且不返回 raw payload

## 3. Frontend Tests

- [x] 3.1 编写 dashboard 页面测试，覆盖统计卡、最近失败、连接错误和空状态
- [x] 3.2 编写 crawl runs 页面测试，覆盖筛选、列表、手动触发 crawl 成功/失败
- [x] 3.3 编写 jobs 页面测试，覆盖聚合计数、列表筛选和 dead/failed 状态
- [x] 3.4 编写真实 HTTP E2E，覆盖 dashboard 加载、查看 runs/jobs、触发 crawl

## 4. Frontend Implementation

- [x] 4.1 新增 dashboard、crawl run、job queue API 类型和 client 方法
- [x] 4.2 实现 dashboard 页面、统计摘要、source 状态分布和最近失败区域
- [x] 4.3 实现爬取任务页面、筛选栏、crawl run 表格和新建 crawl 表单
- [x] 4.4 实现作业队列页面、聚合统计、job 表格和筛选

## 5. Verification

- [x] 5.1 运行相关 API 测试和队列/抓取现有回归测试
- [x] 5.2 运行前端 lint、类型检查、单元/组件测试和真实 HTTP E2E
- [x] 5.3 手动验证 dashboard/runs/jobs 不展示 raw payload
