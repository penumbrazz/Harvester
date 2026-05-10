## Context

Harvester 已实现真实公开网页抓取。Firecrawl 将新浪 7x24 页面（`https://finance.sina.com.cn/7x24/`）转为 Markdown，每条快讯遵循固定模式：

```markdown
21:37:33

[黎巴嫩总理纳瓦夫·萨拉姆：已与叙利亚方面达成协议...](https://wap.cj.sina.cn/pc/7x24/4869892)

43.74万 阅读

0

21:36:50

[下一条快讯标题](https://wap.cj.sina.cn/pc/7x24/4869891)

...
```

每条快讯由 4 个连续段落组成：**时间戳** → **标题链接**（Markdown link，URL 含唯一 ID）→ **阅读量** → **分隔（数字 0）**。

现有 `SinaFixtureExtractor` 处理的是 `{"statuses": [...]}` JSON 格式，无法解析此 Markdown 结构。

## Goals / Non-Goals

**Goals:**

- 实现 `Sina7x24Extractor`，从 Firecrawl Markdown 中逐条抽取快讯为 `CandidateItem`。
- 从 Markdown 链接中提取 `external_item_id`（URL 路径末段数字）和 `final_url`。
- 解析时间戳、阅读量等元数据存入 `extra`。
- 提取标题文本（去掉方括号的链接文字）作为 `title`，链接文字同时作为 `content_text`。
- 提供基于真实抓取样本的 fixture 和 contract 测试。
- 验证 raw-to-search 集成链路。

**Non-Goals:**

- 不修改现有 `SinaFixtureExtractor`。
- 不处理 7x24 页面的分页或无限滚动。
- 不做实时推送或增量更新（那是 scheduler/worker 的职责）。
- 不处理快讯详情页（只处理列表页 Markdown）。

## Decisions

1. **用正则表达式逐条匹配，不用逐行状态机。**
   - 选择：用正则模式匹配 `HH:MM:SS\n[title](url)\n阅读量\n0` 的重复结构。
   - 原因：7x24 Markdown 格式高度规律，正则简洁且易于测试。每条快讯之间以空行和数字 `0` 分隔。
   - 替代方案：逐行状态机。实现更复杂，优势不明显。

2. **`external_item_id` 取 URL 路径末段数字。**
   - 选择：从 `https://wap.cj.sina.cn/pc/7x24/4869892` 中提取 `4869892` 作为唯一 ID。
   - 原因：这是新浪快讯的唯一标识，稳定且可用于 dedup。
   - 替代方案：用完整 URL 做 ID。太长，且 URL 可能含查询参数。

3. **`item_type` 固定为 `"flash"`。**
   - 选择：快讯类型标记为 `"flash"`，区别于现有 `"post"`、`"article"`。
   - 原因：7x24 快讯是短消息流，语义上不同于文章和社交媒体帖子。

4. **时间戳只做字符串提取，不做日期推断。**
   - 选择：提取 `HH:MM:SS` 存入 `extra.time`，不尝试组合日期。
   - 原因：Markdown 中只有时间没有日期，日期需要从其他来源（如 crawl_run 时间）推断，第一版保持简单。

5. **阅读量去掉"万"转为数字。**
   - 选择：`43.74万 阅读` → `437400`（整数），存入 `extra.read_count`。
   - 原因：结构化数字方便后续过滤和排序。

## Risks / Trade-offs

- **[Risk] Markdown 格式变化** → Mitigation: 正则容许一定灵活度（可变空行、可选前缀）。格式大变时需更新正则，但 fixture 测试会立即暴露问题。
- **[Risk] 页面头部有广告/导航噪声** → Mitigation: 第一条匹配到时间戳+链接模式的才开始抽取，跳过页面头部噪声。
- **[Risk] 无日期信息** → Mitigation: `extra.time` 只存时间字符串，日期由 `crawl_run.created_at` 推断，下游消费时组合。
