# Harvester 前端 UI 迁移：Notion 风格 → Animal Island UI

## 背景

Harvester 前端当前使用 Notion 风格的设计系统（warm neutrals、whisper borders、多层低透明度阴影）。将完全替换为 [animal-island-ui](https://github.com/guokaigdg/animal-island-ui) 组件库——受《集合啦！动物森友会》启发的 React + TypeScript UI 组件库。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 采用程度 | 完全替换 | 用户明确要求全量切换 |
| 集成方式 | npm 包直接使用 | 维护成本低，跟随上游更新 |
| 改造顺序 | 从基础组件开始 | 逐步推进，降低风险 |
| 组件范围 | 仅对应现有功能 | 不引入无用的装饰性组件 |

## 工作清单

### Phase 0：基础设施

1. **安装 animal-island-ui npm 包**
   - `npm install animal-island-ui`
   - 在 `frontend/src/main.tsx` 中添加 `import 'animal-island-ui/style'`

2. **替换 DESIGN.md**
   - 删除现有 Notion 风格 DESIGN.md
   - 直接复制 animal-island-ui 项目的 `DESIGN_PROMPT.md` 内容作为 DESIGN.md（设计系统规范总览：色板、字体、尺寸、形状、阴影、交互状态）
   - 在文件顶部添加 Harvester 项目上下文说明

3. **更新 CLAUDE.md**
   - 第 20 行：`Notion 风格设计系统` → `Animal Island UI 风格设计系统`
   - 组件复用部分：新增 "优先检查 animal-island-ui 提供的组件"

4. **安装 animal-island-ui SKILL.md 为 Claude Code skill**

5. **替换 index.css 设计 token**
   - 删除所有 Notion 风格 CSS 自定义属性
   - 写入 animal-island-ui 设计 token（`:root` 变量）
   - 添加 Google Fonts 引入（Nunito + Noto Sans SC + Zen Maru Gothic）
   - 添加字体声明

### Phase 1：核心组件替换

删除 `src/components/ui/` 下所有手写组件，直接从 `animal-island-ui` 导入。

| 现有组件 | 替换为 | API 适配说明 |
|----------|--------|-------------|
| `Button` (primary/secondary/ghost) | `Button` from animal-island-ui | `variant="primary"` → `type="primary"`, `variant="secondary"` → `type="default"`, `variant="ghost"` → `type="dashed"` |
| `Card` | `Card` from animal-island-ui | 直接使用 `type="default"` |
| `ConfirmDialog` | `Modal` from animal-island-ui | 用 Modal + 自定义 footer（确认/取消按钮）实现确认对话框模式 |
| `Input` | `Input` from animal-island-ui | 直接替换，API 兼容 |
| `Select` | `Select` from animal-island-ui | 从非受控改为受控模式，适配 `options` 数组格式 |
| `StatusPill` | 自定义组件 | 无直接映射。用 animal-island-ui NookPhone 配色实现 pill 标签 |

### Phase 2：布局组件重样式

不删除组件文件，但重写内联样式使用新的设计 token。

| 组件 | 改动 |
|------|------|
| `AppLayout` | 背景色 `#f8f8f0`，sidebar 宽度 `220px` |
| `Sidebar` | 动森风格侧边栏：叶子纹理背景、菜单项圆角 12px、hover `#d6dff0`、active `#B7C6E5` |
| `PaginationControls` | 使用 animal-island-ui Button 组件，pill 形状 |

### Phase 3：Feature 页面样式更新

更新所有 9 个页面 + 7 个子组件的内联样式：

- `table-styles.ts` → 重写为 animal-island 表格样式
- `tokens.ts` → 更新数值 token（字重等）
- 所有 feature 组件中的 `style={{...}}` 更新为引用新 CSS 变量

涉及文件清单：

```
features/overview/overview-page.tsx
features/operations/dashboard-page.tsx
features/operations/crawls-page.tsx
features/operations/jobs-page.tsx
features/sources/sources-page.tsx
features/sources/components/propose-source-form.tsx
features/sources/components/source-row.tsx
features/recipes-schedules/recipes-page.tsx
features/recipes-schedules/schedules-page.tsx
features/recipes-schedules/components/recipe-row.tsx
features/recipes-schedules/components/schedule-row.tsx
features/recipes-schedules/components/selectors.tsx
features/content/content-library-page.tsx
features/content/content-detail-modal.tsx
features/audit/audit-page.tsx
pages/placeholder-page.tsx
lib/table-styles.ts
lib/tokens.ts
lib/navigation.ts（可能需要更新样式引用）
```

### Phase 4：测试更新

- 更新所有现有单元测试中的 import 路径
- 更新 mock 组件引用
- 确保所有 `data-testid` 保持不变
- 运行全量测试确认无回归

## 组件 API 映射细节

### Button

```tsx
// 之前
import { Button } from '../components/ui/button'
<Button variant="primary" onClick={...}>Text</Button>

// 之后
import { Button } from 'animal-island-ui'
<Button type="primary" onClick={...}>Text</Button>
```

### Input

```tsx
// 之前
import { Input } from '../components/ui/input'
<Input label="Name" value={v} onChange={...} />

// 之后
import { Input } from 'animal-island-ui'
<Input value={v} onChange={...} />  // 无 label prop，需外部添加
```

### Select

```tsx
// 之前
import { Select } from '../components/ui/select'
<Select label="Type">
  <option value="a">A</option>
</Select>

// 之后
import { Select } from 'animal-island-ui'
<Select
  options={[{ label: 'A', value: 'a' }]}
  value="a"
  onChange={...}
/>
```

### Card

```tsx
// 之前
import { Card } from '../components/ui/card'
<Card>Content</Card>

// 之后
import { Card } from 'animal-island-ui'
<Card type="default">Content</Card>
```

### Modal (替换 ConfirmDialog)

```tsx
// 之前
import { ConfirmDialog } from '../components/ui/confirm-dialog'
<ConfirmDialog open={...} title="..." message="..." onConfirm={...} onCancel={...} />

// 之后
import { Modal } from 'animal-island-ui'
<Modal
  open={open}
  title="Title"
  onCancel={onCancel}
  footer={<>
    <Button type="dashed" onClick={onCancel}>Cancel</Button>
    <Button type="primary" onClick={onConfirm}>Confirm</Button>
  </>}
>
  <p>Message content</p>
</Modal>
```

### StatusPill（自定义实现）

```tsx
// 使用 NookPhone 配色系统
const STATUS_COLOR_MAP = {
  success: { bg: '#8ac68a', text: '#fff' },     // app-green
  error:   { bg: '#fc736d', text: '#fff' },     // app-red
  warning: { bg: '#f7cd67', text: '#725d42' },   // app-yellow
  info:    { bg: '#889df0', text: '#fff' },      // app-blue
  default: { bg: 'rgb(247,243,223)', text: '#725d42', border: '#c4b89e' }, // default
}
```

## 风格对比速查

| 属性 | Notion (旧) | Animal Island (新) |
|------|------------|-------------------|
| 背景 | `#ffffff` | `#f8f8f0` (奶油米白) |
| 内容区背景 | `#f6f5f4` | `rgb(247,243,223)` |
| 主文字 | `rgba(0,0,0,0.95)` | `#794f27` (温暖棕) |
| 正文字 | `#615d59` | `#725d42` |
| 次级文字 | `#a39e98` | `#9f927d` |
| 主色调 | `#0075de` (Notion Blue) | `#19c8b9` (薄荷青绿) |
| 焦点色 | `#097fe8` (Blue) | `#ffcc00` (黄色) |
| 按钮 3D 阴影 | 无 | `0 5px 0 0 #bdaea0` |
| 按钮圆角 | `4px` | `50px` (pill) |
| 卡片圆角 | `12px` | `20px` |
| 边框 | `1px solid rgba(0,0,0,0.1)` | `2px solid #9f927d` |
| 字体 | Inter | Nunito + Noto Sans SC |
| 按钮字重 | 600 | 600-700 |
| 成功色 | `#1aae39` | `#6fba2c` |
| 警告色 | `#dd5b00` | `#f5c31c` |
| 错误色 | N/A | `#e05a5a` |
