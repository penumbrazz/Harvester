## 1. Fetch Policy

- [x] 1.1 先创建 `tests/domain/test_fetch_policy.py`，覆盖非 `http`/`https` 协议拒绝、localhost 拒绝、private IP 拒绝、link-local 拒绝、公网域名允许和 DNS 解析失败。
- [x] 1.2 实现 `harvester/domain/fetch_policy.py`，提供可复用的 public-web allow/deny 结果和机器可读 reason。
- [x] 1.3 增加 redirect final URL 复检测试，覆盖公网 URL redirect 到 private IP 时被拒绝。
- [x] 1.4 将 fetch policy reason 设计成稳定字符串，方便 API、adapter、audit 和 CLI 复用。
- [x] 1.5 运行 `uv run pytest tests/domain/test_fetch_policy.py -q` 并确认通过。

## 2. Firecrawl Adapter

- [x] 2.1 先创建 `tests/adapters/test_firecrawl.py`，用 `httpx.MockTransport` 覆盖成功响应、错误响应、timeout/malformed 响应和缺失配置。
- [x] 2.2 实现 `harvester/adapters/firecrawl.py`，读取 `FIRECRAWL_API_URL`、可选 API key、timeout 和 scrape path 配置。
- [x] 2.3 将不同 Firecrawl 响应形状归一化为 crawl result：original URL、final URL、HTTP status、content type、payload text、metadata。
- [x] 2.4 确保真实 adapter 不会在缺失 Firecrawl URL 时回退到 stub/fixture。
- [x] 2.5 运行 `uv run pytest tests/adapters/test_firecrawl.py -q` 并确认通过。

## 3. Raw Archive

- [x] 3.1 先创建 `tests/jobs/test_raw_archive.py`，覆盖 payload 写入 archive、content hash、byte size、storage URI、retention metadata 和 oversized 拒绝。
- [x] 3.2 实现 `harvester/jobs/archive.py` 或等价模块，按 crawl run/source/date 写入 raw payload 文件。
- [x] 3.3 增加配置读取：`HARVESTER_ARCHIVE_PATH`、最大 payload bytes、默认 raw retention days。
- [x] 3.4 确保 raw payload 不进入 Postgres，只写 `raw_objects.storage_uri` 和 metadata。
- [x] 3.5 运行 `uv run pytest tests/jobs/test_raw_archive.py tests/jobs/test_raw_object_metadata.py -q` 并确认通过。

## 4. Crawl Execution Service

- [x] 4.1 先创建 `tests/jobs/test_public_crawl_execution.py`，覆盖 approved source/recipe 成功抓取、未批准 source 拒绝、未批准 recipe 拒绝、高风险 recipe 拒绝、policy 拒绝和 adapter 失败。
- [x] 4.2 实现 crawl execution service，负责创建/更新 `crawl_runs`、调用 fetch policy、调用 adapter、写 archive、创建 `raw_objects` 和 audit events。
- [x] 4.3 成功时将 `crawl_runs.raw_object_id` 指向新 raw object，并记录 final URL、HTTP status、content type、fetch fingerprint。
- [x] 4.4 失败时将 `crawl_runs.status` 标记为 failed，并写入可被 `/failures/recent` 读取的 `error_message`。
- [x] 4.5 运行 `uv run pytest tests/jobs/test_public_crawl_execution.py tests/api/test_failures.py -q` 并确认通过。

## 5. API and CLI

- [x] 5.1 先创建 `tests/api/test_crawl.py`，覆盖 `POST /crawl/run` 的认证、成功响应、source/recipe 状态拒绝和 policy 拒绝。
- [x] 5.2 增加 `harvester/api/routers/crawl.py` 并在 `harvester/api/app.py` 注册 router。
- [x] 5.3 先创建 `tests/cli/test_crawl_cli_http_only.py`，断言 CLI 只通过 HTTP API 调用 crawl run，不直接创建数据库 session。
- [x] 5.4 增加 `harvester crawl run --source-id ... --recipe-id ...`，输出 crawl run ID、status 和 raw object ID。
- [x] 5.5 运行 `uv run pytest tests/api/test_crawl.py tests/cli/test_crawl_cli_http_only.py -q` 并确认通过。

## 6. CDC Raw-to-Search Smoke

- [x] 6.1 先创建 `tests/integration/test_cdc_public_crawl_smoke.py`，默认跳过真实网络，仅在 `HARVESTER_ENABLE_LIVE_CRAWL=1` 时执行。
- [x] 6.2 用 adapter fake 覆盖普通集成测试，验证 CDC raw payload 经 extractor 进入 `content_item`、`item_version`、`chunk` 和 keyword search。
- [x] 6.3 增加显式 live smoke 路径，抓取 CDC 公开页面并验证 raw object metadata、抽取结果和可搜索输出。
- [x] 6.4 更新 `scripts/smoke.sh`，在配置启用时执行 CDC live crawl smoke；默认仍只跑 deterministic fixture smoke。
- [x] 6.5 运行 `uv run pytest tests/integration/test_cdc_public_crawl_smoke.py tests/search/test_keyword_search.py -q` 并确认通过。

## 7. Documentation and Verification

- [x] 7.1 更新 `.env.example`，补齐 Firecrawl API key、scrape path、timeout、max bytes、live crawl smoke 开关和 archive 配置。
- [x] 7.2 更新 README，说明真实公开网页抓取的架构、流程、安全边界和 smoke 命令。
- [x] 7.3 运行 `uv run pytest tests/domain/test_fetch_policy.py tests/adapters/test_firecrawl.py tests/jobs/test_raw_archive.py tests/jobs/test_public_crawl_execution.py tests/api/test_crawl.py tests/cli/test_crawl_cli_http_only.py -q` 并确认通过。
- [x] 7.4 运行 `uv run pytest -q` 并确认全量测试通过。
- [x] 7.5 如果任务全部完成，提交信息使用 `feat: implement public web crawl`。
