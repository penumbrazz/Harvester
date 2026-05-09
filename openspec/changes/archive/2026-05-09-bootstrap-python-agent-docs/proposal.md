## Why

Harvester 现在只有设计文档和 OpenSpec 配置，还没有可执行的 Python 项目骨架、测试入口或 agent 协作约束。先建立项目基座，可以让后续 GLM/Claude/Codex 按同一目录、命令和工程纪律工作。

## What Changes

- 创建 Python 项目骨架：`pyproject.toml`、`harvester/` 包、`tests/`、基础配置和健康检查占位。
- 创建 `AGENTS.md` 和 `CLAUDE.md`，明确所有 agent 必须中文沟通、按 OpenSpec change 工作、TDD、不得绕过 API 直写库。
- 建立本地开发命令约定：安装、格式化、测试、迁移、服务启动。
- 为后续 schema、API、job、search change 提供共同基础。

## Capabilities

### New Capabilities
- `project-bootstrap`: Python/FastAPI/Typer/pytest 项目基础、目录结构和开发命令约定。
- `agent-instructions`: 多 agent 协作说明，包含 AGENTS.md、CLAUDE.md 和 OpenSpec 执行纪律。

### Modified Capabilities

## Impact

- 新增 Python 包结构和测试目录。
- 新增根目录 `AGENTS.md`、`CLAUDE.md`。
- 后续 change 都依赖这个项目骨架。
