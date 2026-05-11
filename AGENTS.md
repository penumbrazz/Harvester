# AGENTS.md

总是用中文回复用户、编写文档及注释。

## 项目目标

Harvester 是个人 home lab 信息采集控制平面。第一版目标是公开网页抓取、raw evidence 保存、content item 抽取、去重、索引、搜索、审计和可部署基座。

## 端口约定

- **Harvester API（后端）**：`8001`（所有文档、脚本、配置统一使用此端口）
- **Frontend（Vite dev server）**：`5173`
- **omlx（LLM 服务）**：`8000`（外部服务，非 Harvester）

启动：`./start.sh`（同时启动前后端，Ctrl+C 停止）

## 工作方式

- 按 OpenSpec change 工作。实现前先读对应 `openspec/changes/<change>/proposal.md`、`design.md`、`specs/**/spec.md`、`tasks.md`。
- 涉及前端视觉、布局、组件样式或交互状态时，必须先读根目录 `DESIGN.md`，并以其中的 Notion 风格设计系统为准。
- 一次只实现一个 change，除非用户明确要求跨 change 协作。
- 任务完成后立刻把 `tasks.md` 中对应 `- [ ]` 改成 `- [x]`。
- 采用 TDD。先写或更新测试，再实现，再运行相关测试。
- 不要绕过 Harvester API 直接写生产数据库。迁移和测试 fixture 例外。
- CLI 的状态变更必须通过 HTTP API，不直接创建数据库 session。
- 保持最小 diff，不做未在当前 OpenSpec change 中定义的顺手重构。

## 核心架构约束

```text
raw_object 只回答：这次抓取看到了什么。
content_item / item_version / chunk 才是资料库和搜索层。
```

- `raw_object` 是短保留 evidence cache，不是长期语料库。
- 默认 raw HTML/API payload 可按约 7 天保留；提取成功后可压缩或删除 payload。
- 长期保留的是 metadata、hash、audit、`content_item`、`item_observation`、`item_version`、`chunk`。
- embedding 只能从 `item_version -> chunk` 开始，不能对 raw HTML/API payload 做 embedding。
- 瀑布流、时间线、搜索结果页不能整体当成一篇文档。必须抽取独立 `content_item`。
- 高频源必须用 frontier + rewind window + dedup，不能只依赖游标。
- pipeline stage 必须定义事务边界、唯一 upsert key 和下游 job 创建规则。



## 🧪 测试

**提交前务必运行测试。** 目标覆盖率：最低 40-60%。

**⚠️ Python 模块使用 [uv](https://docs.astral.sh/uv/) 管理依赖。始终使用 `uv run` 执行 Python 命令。**


**测试原则：**
- 遵循 AAA 模式：Arrange（准备）、Act（执行）、Assert（断言）
- Mock 外部服务（Anthropic、OpenAI、Docker、API）
- 测试边缘情况和错误条件
- 保持测试独立和隔离

**E2E 测试规则：**
- ⚠️ E2E 测试不允许优雅失败——禁止 `test.skip()`，禁止静默失败
- ⚠️ 前端禁止 Mock 后端 API——必须发送真实 HTTP 请求
- 如果测试失败，修复问题——绝不能为了通过 CI 而跳过

---

## 💻 代码风格

**⚠️ 所有代码注释必须使用英文编写。**

### 通用原则

- **高内聚，低耦合**：每个模块/类应有单一职责
- **文件大小限制**：如果文件超过 **1000 行**，应拆分为多个子模块
- **函数长度**：每个函数最多 50 行（推荐）

### 代码设计准则

⚠️ **实现新功能或修改现有代码时请遵循以下准则：**

1. **长期可维护性优于短期简洁性**：当存在多种实现方案时，避免那些现在实现简单但长期增加维护成本的方案。选择平衡实现成本和长期可持续性的方案。

2. **使用设计模式进行解耦**：积极考虑应用设计模式（如策略模式、工厂模式、观察者模式、适配器模式）来解耦模块并提高代码灵活性。这使代码库更易于扩展和测试。

3. **通过提取管理复杂性**：如果模块已经很复杂，优先将公共逻辑提取到工具模块或创建新模块，而不是在现有模块上增加更多复杂性。有疑问时，拆分而非扩展。

4. **先参考，再提取，然后复用**：实现新功能之前，务必：
   - 搜索解决类似问题的现有实现
   - 如有发现，从现有代码中提取可复用的模式
   - 创建可在代码库中复用的共享工具
   - 绝不复制粘贴代码或编写重复逻辑

5. **先重构再扩展**：分析代码时，识别与新功能相关的特性。如果存在相关代码，在添加新功能之前先使用设计模式重构并提取公共方法——绝不重新实现已有逻辑。

6. **修复所有发现的问题**：在开发过程中发现问题时，必须立即修复。绝不能因为问题看似"不相关"而忽略——发现的所有 bug 都必须处理。**主动审查**代码和文档中的问题——不要等待用户指出。

7. **优先采用行业标准而非项目惯例**：如果项目有不符行业标准的实践，应采用标准方法而非扩展非标准模式。这提高了代码的可维护性，减少了新开发者的上手难度。

8. **积极删除死代码**：无论需要多大努力，确保删除已废弃、未使用或过时的代码。死代码降低可维护性并造成混乱——保持代码库整洁是不可商量的。

9. **从所有代码中提取公共逻辑**：在进行更改时，如果发现应提取到共享工具的逻辑，立即执行。这适用于所有代码——不仅是"新代码复用旧代码"，也包括从现有代码段之间提取共性。每个复用机会都必须抓住。

10. **避免向后兼容——为理想状态设计**：实现更改时，就像没有遗留负担一样设计——考虑"如果从零开始，最好的方法是什么"。避免为旧逻辑编写兼容性垫片或变通方案。如果向后兼容绝对不可避免，在继续之前先与用户协商。

### Python（Backend、Executor、Shared）

**标准：** PEP 8、Black 格式化（行长度：88）、isort、必须使用类型提示

```bash
black . && isort .
```

**准则：**
- 使用描述性命名，公共函数/类必须有 docstring
- 将魔法数字提取为常量

### TypeScript/React（Frontend）

**标准：** TypeScript 严格模式、函数式组件、Prettier、ESLint、单引号、无分号

```bash
npm run format && npm run lint
```

**准则：**
- 优先使用 `const` 而非 `let`，禁止使用 `var`
- 组件名：PascalCase，文件名：kebab-case
- 类型定义放在 `src/types/`

### 组件复用

⚠️ **创建新组件前务必检查现有组件**

1. 在 `src/components/ui/`、`src/components/common/`、`src/features/*/components/` 中搜索现有组件
2. 如果多次实现类似的 UI 模式，提取可复用逻辑

### 测试属性（data-testid）

⚠️ **保留并添加 `data-testid` 属性用于 E2E 测试**

**修改现有代码时：**
- ✅ **始终保留**现有的 `data-testid` 属性——它们被 E2E 测试使用
- ❌ 不要重命名或删除 `data-testid`，除非同时更新对应的 E2E 测试

**创建新的交互组件时：**
- ✅ **必须添加** `data-testid` 属性到交互元素（按钮、输入框、链接、选择框等）
- ✅ 使用描述性的、一致的命名：`{动作}-{元素类型}`（例如 `save-button`、`cancel-link`、`search-input`）
- ❌ 不要在交互元素上省略 `data-testid`

---

## 🔄 Git 工作流

### 分支命名与提交

**分支模式：** `<类型>/<描述>`（feature/、fix/、refactor/、docs/、test/、chore/）

**提交格式：** [约定式提交](https://www.conventionalcommits.org/)
```
<type>[scope]: <description>
# 类型：feat | fix | docs | style | refactor | test | chore
# 示例：feat(backend): add Ghost YAML import API
```

### Git 钩子（Husky）

| 钩子 | 用途 |
|------|------|
| `pre-commit` | Python 格式化（black + isort）、前端 lint-staged |
| `commit-msg` | 验证提交信息格式 |
| `pre-push` | AI 推送质量检查 |

**⚠️ AI 智能体必须遵守 Git 钩子输出——修复问题，禁止使用 `--no-verify`**


---
