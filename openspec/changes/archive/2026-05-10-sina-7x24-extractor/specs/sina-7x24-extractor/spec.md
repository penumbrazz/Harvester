## ADDED Requirements

### Requirement: 新浪 7x24 Markdown 解析
系统 SHALL 提供 `Sina7x24Extractor`，从 Firecrawl 返回的新浪 7x24 Markdown payload 中逐条抽取快讯为独立 `CandidateItem`。

#### Scenario: 成功解析多条快讯
- **WHEN** extractor 收到包含多条快讯的 7x24 Markdown payload
- **THEN** 系统 MUST 为每条快讯返回一个 `CandidateItem`，`item_type` 为 `"flash"`

#### Scenario: 跳过页面头部噪声
- **WHEN** Markdown payload 包含广告、导航等非快讯内容
- **THEN** 系统 MUST 只返回匹配时间戳+链接模式的快讯，跳过噪声

#### Scenario: 空 payload 返回空列表
- **WHEN** extractor 收到空字符串或不含快讯模式的 payload
- **THEN** 系统 MUST 返回空列表

### Requirement: 快讯 ID 和 URL 提取
系统 SHALL 从每条快讯的 Markdown 链接中提取唯一 ID 和 URL。

#### Scenario: 提取 external_item_id
- **WHEN** 快讯链接为 `[title](https://wap.cj.sina.cn/pc/7x24/4869892)`
- **THEN** 系统 MUST 提取 `4869892` 作为 `external_item_id`

#### Scenario: 提取 final_url
- **WHEN** 快讯链接为 `[title](https://wap.cj.sina.cn/pc/7x24/4869892)`
- **THEN** 系统 MUST 提取完整 URL 作为 `final_url` 和 `original_url`

### Requirement: 时间戳提取
系统 SHALL 从每条快讯中提取时间戳。

#### Scenario: 提取 HH:MM:SS 时间戳
- **WHEN** 快讯时间戳行为 `21:37:33`
- **THEN** 系统 MUST 将 `21:37:33` 存入 `extra.time`

### Requirement: 阅读量提取
系统 SHALL 从每条快讯中提取阅读量数字。

#### Scenario: 提取万级阅读量
- **WHEN** 阅读量行为 `43.74万 阅读`
- **THEN** 系统 MUST 将 `437400` 存入 `extra.read_count`

#### Scenario: 提取普通阅读量
- **WHEN** 阅读量行为 `3200 阅读`
- **THEN** 系统 MUST 将 `3200` 存入 `extra.read_count`

#### Scenario: 缺失阅读量
- **WHEN** 快讯没有阅读量行
- **THEN** 系统 MUST 将 `extra.read_count` 设为 `None`

### Requirement: 标题和内容提取
系统 SHALL 从 Markdown 链接文字中提取快讯标题。

#### Scenario: 提取标题文本
- **WHEN** 快讯链接为 `【海南省委书记冯飞与新质生产力领域相关企业及投资机构代表座谈】据海南日报...`
- **THEN** 系统 MUST 将链接文字作为 `title` 和 `content_text`

### Requirement: Fixture 和 contract 测试
系统 SHALL 提供基于真实抓取样本的 fixture 文件和 contract 测试。

#### Scenario: Fixture raw 文件存在且非空
- **WHEN** 运行 fixture contract 测试
- **THEN** `tests/fixtures/raw/sina-7x24.md` MUST 存在且包含至少 3 条快讯模式

#### Scenario: Expected items 文件与 extractor 输出一致
- **WHEN** 运行 extractor 对 fixture raw 的解析
- **THEN** 输出 MUST 与 `tests/fixtures/expected/sina-7x24-items.json` 中的 items 数量一致，且每个 item 包含 `external_item_id`、`item_type`、`title`

### Requirement: Raw-to-search 集成验证
系统 SHALL 验证 7x24 抽取结果能进入 `content_item → item_version` 的完整链路。

#### Scenario: 抽取结果通过 pipeline 入库
- **WHEN** 使用 adapter fake 模拟 7x24 抓取并通过 extractor 抽取
- **THEN** 系统 MUST 成功创建 `ContentItem` 和 `ItemVersion`，且 `external_item_id` 与 extractor 输出一致
