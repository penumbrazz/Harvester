## Why

Harvester 已能通过 Firecrawl 抓取新浪 7x24 实时财经快讯页面并保存 raw payload（Markdown 格式），但还没有 extractor 能从 Markdown 中抽取独立的 content_item。当前 `SinaFixtureExtractor` 只能处理 `{"statuses": [...]}` JSON fixture，无法解析真实 Firecrawl 返回的 Markdown 结构。

7x24 页面的 raw payload 是 Firecrawl 转成的 Markdown，每条快讯遵循固定模式：时间戳 → 标题链接（含 URL 和 ID）→ 阅读量 → 分隔。需要一个新的 extractor 将每条快讯解析为独立 `content_item`，才能进入 `item_version → chunk → search` 的完整链路。

## What Changes

- 新增 `Sina7x24Extractor`，解析 Firecrawl 返回的新浪 7x24 Markdown payload，每条快讯输出为一个 `CandidateItem`。
- 每条快讯从 Markdown 链接中提取 `external_item_id`（URL 末尾数字）和 `final_url`。
- 时间戳解析为结构化字段，存入 `extra`。
- 阅读量提取并存入 `extra`。
- 新增对应的 fixture raw 文件和 expected items 文件用于 contract 测试。
- 新增 extractor 单元测试和 raw-to-search 集成测试。

## Capabilities

### New Capabilities
- `sina-7x24-extractor`: 新浪 7x24 实时财经快讯 Markdown 解析 extractor，从 Firecrawl 输出中抽取独立 content_item。

### Modified Capabilities

## Impact

- 新增 extractor 文件 `harvester/extractors/sina_7x24.py`。
- 新增 fixture 文件 `tests/fixtures/raw/sina-7x24.md` 和 `tests/fixtures/expected/sina-7x24-items.json`。
- 新增测试文件 `tests/extractors/test_sina_7x24.py`。
- 新增集成测试或扩展现有 `test_sina_compressed_soak.py`。
- 不影响现有 `SinaFixtureExtractor` 和其他 extractor。
