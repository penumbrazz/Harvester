## ADDED Requirements

### Requirement: PDF raw evidence archive
系统 SHALL 将公开 PDF 附件作为 raw evidence 保存到 archive storage，并只在 Postgres 中保存 raw object metadata。

#### Scenario: 保存 PDF 原始 bytes
- **WHEN** PDF asset target 抓取成功且 payload 未超过大小限制
- **THEN** 系统 MUST 将原始 PDF bytes 写入 archive storage，并创建 content type 为 `application/pdf` 或等价 PDF media type 的 raw object metadata

#### Scenario: PDF payload 不进入 Postgres
- **WHEN** 系统保存 PDF raw object
- **THEN** 系统 MUST NOT 将 PDF bytes inline 存入 Postgres

#### Scenario: 超大 PDF 被拒绝
- **WHEN** PDF payload 超过配置的最大 payload byte size
- **THEN** 系统 MUST 将对应 crawl run 和 target 标记为失败，并且 MUST NOT 保存超大 payload

### Requirement: PDF text extraction
系统 SHALL 从 PDF raw object 抽取文本，并将抽取结果写入 content item version。

#### Scenario: PDF 文本抽取成功
- **WHEN** extraction worker 处理 content type 为 PDF 的 raw object
- **THEN** 系统 MUST 从 archive 读取 PDF bytes、抽取文本、生成 normalized text，并为对应 content item 创建或复用 item version

#### Scenario: PDF 文本抽取失败
- **WHEN** PDF 文件无法解析、加密、损坏或不包含可抽取文本
- **THEN** 系统 MUST 保留 raw object metadata，记录 extraction failure 原因，并且 MUST NOT 创建空文本 item version

#### Scenario: PDF 文本进入 chunk pipeline
- **WHEN** PDF 抽取创建新的 item version
- **THEN** 系统 MUST 按现有 chunking 规则创建 chunk，并创建后续 embedding job

### Requirement: PDF source priority
系统 SHALL 支持 recipe 为同一 content item 指定 PDF 文本优先于详情页 HTML 摘要作为主要版本来源。

#### Scenario: PDF 和详情页都可用
- **WHEN** 同一 external item ID 同时存在详情页 HTML 文本和 PDF 文本
- **THEN** 系统 MUST 按 recipe content priority 使用 PDF 文本作为主要 item version 来源，并保留详情页 observation

#### Scenario: PDF 不可用时使用 fallback
- **WHEN** 详情页可抽取文本但 PDF target 缺失、抓取失败或解析失败
- **THEN** 系统 MAY 按 recipe fallback 策略使用详情页文本创建 item version，并 MUST 在 metadata 或 audit 中标识该版本来源不是 PDF

### Requirement: PDF extraction traceability
系统 SHALL 保持 PDF 抽取结果到原始抓取证据和发现路径的可追溯性。

#### Scenario: Item version 关联 PDF raw object
- **WHEN** PDF 文本生成 item version
- **THEN** item version MUST 关联生成该版本的 PDF raw object

#### Scenario: 搜索结果可追溯到 Source
- **WHEN** 用户通过搜索找到 PDF 生成的 chunk
- **THEN** 系统 MUST 能通过 item version、content item、raw object 或 target 元数据追溯到原始 Source 和 PDF URL

### Requirement: CDC weekly PDF fixture coverage
系统 SHALL 提供确定性 fixture 覆盖 CDC 周报 list -> detail -> PDF 的完整链路，普通回归测试不得依赖外网。

#### Scenario: Fixture 链路生成 PDF content item
- **WHEN** 使用 CDC 周报 fixture 运行列表页、详情页和 PDF 抽取链路
- **THEN** 系统 MUST 生成稳定 external item ID 的 content item、PDF item version、chunk 和 embedding job

#### Scenario: Live smoke 显式开启
- **WHEN** 环境变量显式启用 CDC live smoke
- **THEN** 系统 MAY 访问真实 CDC 公开页面，并 MUST 验证至少一个周报 PDF raw object 和可搜索文本结果

#### Scenario: 默认测试不访问网络
- **WHEN** 未显式启用 live smoke
- **THEN** CDC PDF 链路测试 MUST 使用 fixture 或 adapter fake，并且 MUST NOT 访问网络
