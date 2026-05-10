## 1. Fixture 准备

- [x] 1.1 从真实抓取的 archive 中截取前 10 条快讯，创建 `tests/fixtures/raw/sina-7x24.md`。
- [x] 1.2 手动编写 `tests/fixtures/expected/sina-7x24-items.json`，包含对应 fixture 的 expected items（含 `external_item_id`、`item_type`、`title`、`extra.time`、`extra.read_count`）。
- [x] 1.3 更新 `tests/fixtures/test_fixture_contract.py`，增加 `sina-7x24.md` 的 contract 测试（至少 3 条快讯模式）和 `sina-7x24-items.json` 的 expected items 校验。

## 2. Extractor 实现

- [x] 2.1 先创建 `tests/extractors/test_sina_7x24.py`，覆盖多条快讯解析、ID/URL 提取、时间戳提取、阅读量提取（万级和普通）、标题提取、空 payload、噪声跳过。
- [x] 2.2 实现 `harvester/extractors/sina_7x24.py`，用正则从 Markdown 中逐条匹配快讯，提取 `external_item_id`、`final_url`、`title`、`extra.time`、`extra.read_count`。
- [x] 2.3 运行 `uv run pytest tests/extractors/test_sina_7x24.py -q` 并确认通过。

## 3. Contract 和集成测试

- [x] 3.1 运行 `uv run pytest tests/fixtures/test_fixture_contract.py -q` 并确认 fixture contract 通过。
- [x] 3.2 新增或扩展集成测试，用 adapter fake 模拟 7x24 抓取，验证 extractor 输出经 pipeline 进入 `content_item` 和 `item_version`。
- [x] 3.3 运行集成测试 `uv run pytest tests/integration/ -q` 并确认通过。

## 4. 全量验证

- [x] 4.1 运行 `uv run pytest -q` 并确认全量测试通过。
- [x] 4.2 提交信息使用 `feat: add sina 7x24 markdown extractor`。
