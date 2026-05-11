## Context

Harvester 当前是 Python/FastAPI + Typer CLI 项目，没有前端工程。用户提供的静态 HTML 原型定义了管理控制台的信息架构，但视觉必须改为根目录 `DESIGN.md` 的 Notion 风格：温暖中性色、轻边框、低饱和状态、单一蓝色主操作。

这个 change 是后续所有 admin 页面的小前置切片。它只建立前端基础设施和真实 API 连接，不实现业务列表页，避免第一个 change 过大。

## Goals / Non-Goals

**Goals:**

- 建立 `frontend/` 工程，使用 React、TypeScript、Vite、ESLint、Prettier 和测试工具。
- 建立共享 design tokens、基础布局、导航、空页面、健康检查和 API client。
- 支持 API base URL 和 API token 配置，后续页面统一通过 API client 调用后端。
- 建立 E2E 测试基座，明确前端测试必须访问真实 Harvester API。

**Non-Goals:**

- 不实现 source、recipe、schedule、crawl、job、content、audit 的业务数据页面。
- 不引入用户登录、多租户、服务端 session 或权限模型。
- 不改变 Harvester 核心 raw/content 分层，不新增业务数据库表。

## Decisions

1. **选择 Vite + React + TypeScript。**
   - 原因：后续页面需要表格、筛选、表单、状态反馈和 E2E，SPA 工程比静态 HTML 更可维护。
   - 替代方案：FastAPI Jinja/HTMX。部署简单，但多页面状态和后续组件复用会变复杂。

2. **前端放在独立 `frontend/`。**
   - 原因：避免污染 Python package，并让 Node 脚本、类型和测试边界清晰。
   - 替代方案：放在 `harvester/api/static`。适合构建产物，不适合作为源码根。

3. **视觉 token 从 `DESIGN.md` 抽象为 CSS variables。**
   - 原因：后续 GLM/Codex 实现页面时有稳定约束，不会回到参考 HTML 的厚边框游戏化风格。
   - 替代方案：直接复制参考 HTML CSS。速度快，但与用户指定视觉方向冲突。

4. **API token 先以本地配置方式输入和保存。**
   - 原因：当前后端只有 Bearer token，没有登录态；前端不应发明 auth 模型。
   - 替代方案：新增登录页和 session。超出当前项目阶段。

5. **应用壳先提供全部导航，但未实现页面显示空状态。**
   - 原因：信息架构可以稳定下来，后续 change 只填充各自页面。
   - 替代方案：只做 health 页面。切片更小，但后续页面会反复修改导航。

## Risks / Trade-offs

- [Risk] 引入 Node 工具链增加开发复杂度。→ Mitigation: 只选择 Vite 标准栈，脚本保持少而明确。
- [Risk] API token 存在浏览器本地存储风险。→ Mitigation: 文档明确这是 home lab 管理控制台第一版，后续登录态另立 change。
- [Risk] 空页面导航可能被误认为功能已完成。→ Mitigation: 页面文案使用清晰空状态，并在后续 change 中逐步替换。
- [Risk] 前端跨域配置不一致。→ Mitigation: API client 使用可配置 base URL，开发文档写明 API/frontend 启动方式。
