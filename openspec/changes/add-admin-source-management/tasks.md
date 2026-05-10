## 1. API Tests

- [x] 1.1 编写 `GET /sources` API 测试，覆盖字段、认证、空列表和排序
- [x] 1.2 编写 source 状态筛选和类型筛选测试
- [x] 1.3 编写 resume/archive API 测试，覆盖合法 transition、非法 transition 和 audit event

## 2. Backend Implementation

- [x] 2.1 在 source router 中实现 source 列表 read API，返回前端所需字段且不暴露 raw payload
- [x] 2.2 通过 `SOURCE_TRANSITIONS` 实现 resume/archive endpoints，并保持 audit 写入
- [x] 2.3 复用或提取 SourceResponse/列表序列化逻辑，避免重复字段映射

## 3. Frontend Tests

- [x] 3.1 编写信息源页面组件测试，覆盖列表、搜索、状态 pill、空状态和错误状态
- [x] 3.2 编写 propose source 表单测试，覆盖成功、校验失败和后端冲突
- [x] 3.3 编写真实 HTTP E2E，覆盖创建 source、提升状态和暂停状态

## 4. Frontend Implementation

- [x] 4.1 新增 source API 类型和 client 方法
- [x] 4.2 实现信息源页面、筛选栏、生命周期提示和表格
- [x] 4.3 实现 propose source 表单和提交反馈
- [x] 4.4 实现 promote、pause、resume、archive 操作按钮、确认/错误状态和列表刷新

## 5. Verification

- [x] 5.1 运行 `uv run pytest` 中 source API 相关测试
- [x] 5.2 运行前端 lint、类型检查、单元/组件测试和 E2E
- [ ] 5.3 手动检查 UI 是否遵循 `DESIGN.md`，没有回退到参考 HTML 的厚边框游戏化风格
