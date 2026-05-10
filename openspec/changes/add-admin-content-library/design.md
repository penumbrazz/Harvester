## Context

Harvester 的知识层是 `content_item / item_version / chunk`，搜索已经有关键词和向量 API。内容库页面需要让用户浏览和搜索资料库，而不是检查 raw evidence。

## Goals / Non-Goals

**Goals:**

- 新增 content item 列表 read API，支持分页、source/topic/status/type 过滤。
- 前端实现内容库 grid/list、关键词搜索、向量搜索、空状态和错误状态。
- 搜索结果展示可追溯字段：item/version/chunk/source/title/url/distance/snippet。
- 遵守 raw/content 分层，不暴露 raw payload。

**Non-Goals:**

- 不实现 raw object 查看器。
- 不实现内容编辑、标注、删除或收藏。
- 不新增 LightRAG/KG 页面。

## Decisions

1. **内容库列表与搜索 API 分离。**
   - 原因：空查询浏览和相关性搜索是不同语义，分页/排序也不同。
   - 替代方案：用空 q 搜索代表列表。会污染 `GET /items/search` 语义。

2. **向量搜索保留 offset 限制。**
   - 原因：现有 vector search 不支持 offset，前端只展示 limit 控制。
   - 替代方案：前端伪分页。会误导用户。

3. **grid/list 是同一数据的不同呈现。**
   - 原因：避免两套查询和状态管理。
   - 替代方案：分别实现。容易出现字段不一致。

## Risks / Trade-offs

- [Risk] content item 列表缺少正文摘要。→ Mitigation: 第一版展示 title/url/source/status/latest version，摘要可来自最新 version 或 chunk 后续补充。
- [Risk] vector 搜索依赖 embedding adapter。→ Mitigation: 前端显示 503 错误，不降级伪造结果。
- [Risk] 用户想看 raw evidence。→ Mitigation: 明确本页只展示资料库层，raw evidence inspection 另立 change。
