## 1. API Tests

- [x] 1.1 编写 content item list API 测试，覆盖认证、字段、分页和空列表
- [x] 1.2 编写 source/topic/type/status 筛选测试
- [x] 1.3 扩展搜索 API 回归测试，确认 keyword/vector 响应字段适合前端展示且不返回 raw payload

## 2. Backend Implementation

- [x] 2.1 新增 content item list endpoint，返回 item、source、topic 和 latest version 摘要字段
- [x] 2.2 为列表 endpoint 添加分页、筛选和稳定排序
- [x] 2.3 确认 search API 错误响应和 vector 503 响应可被前端清晰展示

## 3. Frontend Tests

- [x] 3.1 编写内容库页面测试，覆盖列表加载、空状态、过滤和错误状态
- [x] 3.2 编写 keyword/vector 搜索测试，覆盖结果字段、distance、embedding unavailable 错误
- [x] 3.3 编写 grid/list 切换测试，确认使用同一批真实数据
- [x] 3.4 编写真 HTTP E2E，通过 fixture 数据验证内容可浏览和可搜索

## 4. Frontend Implementation

- [x] 4.1 新增 content item/search API 类型和 client 方法
- [x] 4.2 实现内容库页面、搜索栏、过滤器、grid/list 切换和分页
- [x] 4.3 实现 keyword/vector 模式切换、结果卡片/表格和错误反馈
- [x] 4.4 确保 UI 只展示 content/version/chunk 层字段，不展示 raw payload

## 5. Verification

- [x] 5.1 运行 content/search API 测试和现有 search 集成测试
- [x] 5.2 运行前端 lint、类型检查、单元/组件测试和真实 HTTP E2E
- [x] 5.3 手动验证内容库页面符合 raw/content 分层和 `DESIGN.md` 视觉约束
