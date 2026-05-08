# Harvester OpenSpec Changes

总是用中文沟通、写文档和注释。

这些 change 是给 GLM/Claude/Codex 分块实现 Harvester MVP 用的。每个 change 都已经包含：

- `proposal.md`
- `design.md`
- `specs/**/spec.md`
- `tasks.md`

执行时使用：

```bash
openspec status --change "<change-name>"
openspec instructions apply --change "<change-name>" --json
```

## 推荐顺序

1. `bootstrap-python-agent-docs`
2. `build-control-plane-schema`
3. `build-api-cli-state-machine`
4. `build-job-pipeline-dedup`
5. `build-search-fixtures-deployment`

## 并行策略

`bootstrap-python-agent-docs` 和 `build-control-plane-schema` 是基础，建议先顺序完成。

schema 完成后，可以并行：

- `build-api-cli-state-machine`
- `build-job-pipeline-dedup`

最后执行：

- `build-search-fixtures-deployment`

原因：搜索、fixture 和 deployment smoke 需要前面的 API、schema、pipeline 都有可用入口。

## 测试纪律

每个 `tasks.md` 都已经按“先测试、再实现、再运行命令”拆分。不要跳过测试任务。

如果某个测试因为前置 change 未完成而无法运行，暂停并说明缺少哪个 change，不要临时删除测试。
