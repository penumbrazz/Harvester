# 内容库详情弹窗 & 来源筛选

**日期**：2026-05-16
**状态**：已批准

## 背景

内容库页面（`/content`）当前只能看到内容条目的元数据（标题、类型、状态、URL、时间），无法查看文章完整正文。此外，筛选栏缺少按来源筛选的功能。

## 目标

1. 点击内容条目时弹出详情弹窗，显示完整元数据和文章正文
2. 筛选栏新增来源下拉筛选器

## 设计

### 1. 后端：内容详情 API

**新增端点**：`GET /items/content/{content_item_id}`

响应体：

```json
{
  "id": "uuid",
  "item_type": "article",
  "title": "文章标题",
  "canonical_url": "https://...",
  "status": "active",
  "source_name": "来源名",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "latest_version": {
    "id": "uuid",
    "normalized_text": "文章完整正文...",
    "language": "zh",
    "content_hash": "abc123",
    "created_at": "ISO datetime"
  }
}
```

- `latest_version`：JOIN `item_version` 表取最新一条（`created_at DESC`），无版本时为 `null`
- 错误码：404（content_item_id 不存在）

### 2. 前端：详情弹窗组件

**组件名**：`ContentDetailModal`

**触发**：点击 `ContentRow` 或 `ContentCard` 整行/卡片

**尺寸与样式**（遵循 DESIGN.md）：
- `max-width: 720px`，`max-height: 80vh`
- 背景：白色，12px 圆角，Deep Shadow (Level 3)
- 遮罩：`rgba(0,0,0,0.4)`

**布局**：
- 顶部：标题（22px weight 700）+ 关闭按钮（右上角 X）
- 元数据区：pill badges（类型、状态）+ 来源名
- 信息行：URL 链接（Notion Blue）+ 时间戳
- 分隔线：whisper border
- 正文区：`overflow-y: auto`，`normalized_text` 完整展示

**状态处理**：
- 加载态：骨架屏
- 无正文（`latest_version` 为 null）：显示"暂无正文内容"

**关闭方式**：
- 点击 X 按钮
- 点击遮罩层
- 按 Escape 键

**data-testid**：
- 弹窗容器：`content-detail-modal`
- 关闭按钮：`close-content-detail-button`
- 正文区域：`content-detail-body`

### 3. 前端：来源筛选器

**位置**：筛选栏，在类型和状态筛选器之后

**数据**：页面加载时调用 `listSources({ limit: 100 })` 获取来源列表

**UI**：Select 组件，选项为 `全部来源` + 各来源 `name`，选中值传 `source_id`

**data-testid**：`select-source-filter`

### 4. 前端：交互集成

**点击行为**：
- `ContentRow` 和 `ContentCard` 整行/卡片可点击，`cursor: pointer`
- 悬浮背景：`#f6f5f4`（warm white）
- 点击后调用详情 API，打开弹窗

**状态管理**：
- `ContentLibraryPage` 维护 `selectedItemId: string | null`
- 弹窗组件自行管理加载态和数据获取

## 不包含

- 版本历史展示
- Chunk 分块信息展示
- 正文内容编辑
