## ADDED Requirements

### Requirement: Content item list
系统 SHALL 提供内容库列表 API 和页面，用于浏览已抽取的 content items。

#### Scenario: List content items
- **WHEN** 用户打开内容库页面且未输入搜索查询
- **THEN** 系统 MUST 展示 content item ID、类型、source、topic、标题、canonical URL、状态、创建时间和更新时间

#### Scenario: Filter content items
- **WHEN** 用户按 source、topic、item type 或 status 筛选
- **THEN** 页面 MUST 只展示匹配的 content items

### Requirement: Content search
系统 SHALL 在内容库页面提供关键词和向量搜索。

#### Scenario: Keyword search
- **WHEN** 用户输入关键词并选择 keyword 模式
- **THEN** 前端 MUST 调用真实 `GET /items/search?mode=keyword` 并展示匹配的 content item 结果

#### Scenario: Vector search
- **WHEN** 用户输入查询并选择 vector 模式
- **THEN** 前端 MUST 调用真实 `GET /items/search?mode=vector` 并展示 chunk 级结果和 distance

#### Scenario: Embedding unavailable
- **WHEN** vector 搜索 API 返回 embedding adapter 不可用
- **THEN** 前端 MUST 显示错误且不得伪造搜索结果

### Requirement: Raw payload remains hidden
系统 SHALL 保持 raw evidence 与内容库展示分离。

#### Scenario: Render content result
- **WHEN** 内容库展示列表或搜索结果
- **THEN** 响应和 UI MUST NOT 包含 raw HTML、API payload 或 archive 文件内容

### Requirement: Grid and list views
系统 SHALL 支持内容库 grid 和 list 两种展示方式。

#### Scenario: Toggle content view
- **WHEN** 用户在 grid 和 list 之间切换
- **THEN** 页面 MUST 使用同一批真实 API 数据重新渲染，不得重新 mock 数据
