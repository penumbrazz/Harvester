## 1. API Tests

- [x] 1.1 编写 `GET /recipes` 测试，覆盖认证、字段、approval status 筛选和 executor 筛选
- [x] 1.2 编写 `GET /schedules` 测试，覆盖认证、字段、source/topic/recipe/status 筛选
- [x] 1.3 补充 recipe 创建/审批和 schedule 创建的 API 回归测试，覆盖非法状态错误

## 2. Backend Implementation

- [x] 2.1 在 recipes router 中实现列表 read API，并复用 RecipeResponse 序列化逻辑
- [x] 2.2 在 schedules router 中实现列表 read API，返回 source/topic/recipe 关联字段和分页信息
- [x] 2.3 为 schedule 创建流程确认错误响应适合前端展示

## 3. Frontend Tests

- [x] 3.1 编写 Recipes 页面测试，覆盖列表、筛选、创建 recipe、审批 recipe
- [x] 3.2 编写 Schedules 页面测试，覆盖列表、筛选、创建 source schedule 和后端错误展示
- [x] 3.3 编写 selector 组件测试，覆盖 source、topic、approved recipe 可选/不可选状态
- [x] 3.4 编写真 HTTP E2E，覆盖创建 recipe、审批 recipe、创建 schedule

## 4. Frontend Implementation

- [x] 4.1 新增 recipe/schedule API 类型、client 方法和共享 selector 组件
- [x] 4.2 实现 Recipes 页面、创建表单、JSON config 输入、审批操作和错误反馈
- [x] 4.3 实现 Schedules 页面、创建表单、interval/priority/lane 输入和列表刷新
- [x] 4.4 在需要 recipe 的 crawl/schedule 流程中使用 approved recipe selector

## 5. Verification

- [x] 5.1 运行 recipes/schedules API 测试和相关 CLI 回归测试
- [x] 5.2 运行前端 lint、类型检查、单元/组件测试和真实 HTTP E2E
- [x] 5.3 手动验证 schedule 表单不会允许明显不合法的 source/recipe 状态绕过后端校验
