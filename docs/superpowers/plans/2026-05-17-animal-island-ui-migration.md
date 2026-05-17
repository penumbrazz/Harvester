# Animal Island UI 迁移实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Harvester 前端从 Notion 风格设计系统完全替换为 animal-island-ui 组件库（动物森友会风格）。

**Architecture:** 安装 animal-island-ui npm 包，删除 `src/components/ui/` 下所有手写组件，直接从 `animal-island-ui` 导入替换。布局组件保留文件但重写样式。所有 feature 页面的内联样式更新为新设计 token。自定义 StatusPill 组件用 NookPhone 配色实现。

**Tech Stack:** React 19, TypeScript, animal-island-ui 0.7.7, Vitest (单元测试), Playwright (E2E)

---

## 通用映射规则

本计划所有任务共用以下映射表。后续任务中引用映射时不再重复解释。

### Import 映射

```
旧: import { Button } from '../../components/ui/button'
新: import { Button } from 'animal-island-ui'

旧: import { Card } from '../../components/ui/card'
新: import { Card } from 'animal-island-ui'

旧: import { Input } from '../../components/ui/input'
新: import { Input } from 'animal-island-ui'

旧: import { Select } from '../../components/ui/select'
新: import { Select } from 'animal-island-ui'

旧: import { ConfirmDialog } from '../../components/ui/confirm-dialog'
新: import { Modal, Button } from 'animal-island-ui'

旧: import { StatusPill } from '../../components/ui/status-pill'
新: import { StatusPill } from '../../components/ui/status-pill'  // 保留自定义组件
```

### Button variant → type 映射

| 旧 variant | 新 type | 说明 |
|-----------|---------|------|
| `"primary"` | `"primary"` | 直接映射 |
| `"secondary"` | `"default"` | 默认样式按钮 |
| `"ghost"` | `"text"` | 无边框文字按钮 |

### Style token 映射

| 旧值 | 新值 | 用途 |
|------|------|------|
| `var(--color-white)` / `#ffffff` | `#f8f8f0` | 页面背景 |
| `var(--color-warm-white)` / `#f6f5f4` | `rgb(247,243,223)` | 内容区背景 |
| `var(--color-primary-text)` / `rgba(0,0,0,0.95)` | `#794f27` | 主标题文字 |
| `var(--color-warm-gray-500)` / `#615d59` | `#725d42` | 正文/标签文字 |
| `var(--color-warm-gray-300)` / `#a39e98` | `#9f927d` | 次级文字 |
| `var(--color-notion-blue)` / `#0075de` | `#19c8b9` | 主色调（薄荷青绿） |
| `var(--border-whisper)` | `2px solid #9f927d` | 边框 |
| `var(--shadow-card)` | `0 4px 10px rgba(107,92,67,0.42)` | 卡片阴影 |
| `var(--radius-lg)` / `12px` | `20px` | 卡片圆角 |
| `var(--radius-sm)` / `4px` | `12px` | 小元素圆角 |
| `var(--font-family)` (Inter) | `'Nunito', 'Noto Sans SC', sans-serif` | 字体 |

### Select 映射（非受控→受控）

```tsx
// 旧: children <option> 模式
<Select label="类型" value={v} onChange={e => setV(e.target.value)}>
  <option value="a">A</option>
  <option value="b">B</option>
</Select>

// 新: options 数组 + 受控
<Select
  options={[
    { key: '', label: '全部' },
    { key: 'a', label: 'A' },
    { key: 'b', label: 'B' },
  ]}
  value={v}
  onChange={setV}
/>
// label 需要外部添加，Select 没有 label prop
```

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/package.json` | 添加 animal-island-ui 依赖 |
| Modify | `frontend/src/main.tsx` | 添加 `animal-island-ui/style` 导入 |
| Rewrite | `frontend/src/index.css` | 替换所有 Notion CSS token 为 animal-island token |
| Delete | `frontend/src/components/ui/button.tsx` | 由 animal-island-ui Button 替代 |
| Delete | `frontend/src/components/ui/card.tsx` | 由 animal-island-ui Card 替代 |
| Delete | `frontend/src/components/ui/confirm-dialog.tsx` | 由 animal-island-ui Modal 替代 |
| Delete | `frontend/src/components/ui/input.tsx` | 由 animal-island-ui Input 替代 |
| Delete | `frontend/src/components/ui/select.tsx` | 由 animal-island-ui Select 替代 |
| Rewrite | `frontend/src/components/ui/status-pill.tsx` | 用 NookPhone 配色重写 |
| Delete | `frontend/src/types/style.ts` | Variant type 不再需要 |
| Rewrite | `frontend/src/lib/table-styles.ts` | 使用新设计 token |
| Modify | `frontend/src/lib/tokens.ts` | 更新数值 token |
| Modify | `frontend/src/components/common/app-layout.tsx` | 背景色和布局调整 |
| Modify | `frontend/src/components/common/sidebar.tsx` | 动森风格侧边栏 |
| Modify | `frontend/src/components/common/pagination-controls.tsx` | 使用 animal-island-ui Button |
| Modify | `frontend/src/pages/placeholder-page.tsx` | 更新内联样式 |
| Modify | `frontend/src/features/overview/overview-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/operations/dashboard-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/operations/crawls-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/operations/jobs-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/sources/sources-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/sources/components/propose-source-form.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/sources/components/source-row.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/recipes-schedules/recipes-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/recipes-schedules/schedules-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/recipes-schedules/components/recipe-row.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/recipes-schedules/components/schedule-row.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/recipes-schedules/components/selectors.tsx` | Select 迁移 |
| Modify | `frontend/src/features/content/content-library-page.tsx` | 组件替换 + 样式更新 |
| Modify | `frontend/src/features/content/content-detail-modal.tsx` | Modal 替换 + 样式更新 |
| Modify | `frontend/src/features/audit/audit-page.tsx` | 组件替换 + 样式更新 |
| Rewrite | `DESIGN.md` | 替换为 animal-island-ui DESIGN_PROMPT.md |
| Modify | `CLAUDE.md` | 更新设计系统引用 |

---

## Phase 0：基础设施

### Task 1: 安装 animal-island-ui 并添加 style 导入

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 安装 npm 包**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm install animal-island-ui
```

Expected: package.json 中新增 `"animal-island-ui": "^0.7.7"` 依赖。

- [ ] **Step 2: 在 main.tsx 中添加 style 导入**

将 `frontend/src/main.tsx` 修改为：

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'

import 'animal-island-ui/style'
import { App } from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

注意：`animal-island-ui/style` 必须在 `./index.css` 之前导入。

- [ ] **Step 3: 验证安装成功**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm run build 2>&1 | head -20
```

Expected: 构建成功（可能有 TS 错误因为组件还没替换，但 import 解析应正常）。

- [ ] **Step 4: Commit**

```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester && git add frontend/package.json frontend/package-lock.json frontend/src/main.tsx && git commit -m "feat(frontend): install animal-island-ui and add style import"
```

---

### Task 2: 替换 index.css 设计 token

**Files:**
- Rewrite: `frontend/src/index.css`

- [ ] **Step 1: 用 animal-island 设计 token 替换整个 index.css**

将 `frontend/src/index.css` 完整替换为：

```css
/* Animal Island UI Design Tokens — 动物森友会风格设计系统 */

:root {
  /* Background */
  --color-bg: #f8f8f0;
  --color-bg-content: rgb(247, 243, 223);
  --color-bg-hover: #d6dff0;
  --color-bg-active: #B7C6E5;

  /* Text */
  --color-text-primary: #794f27;
  --color-text-body: #725d42;
  --color-text-secondary: #9f927d;

  /* Accent */
  --color-accent: #19c8b9;
  --color-focus: #ffcc00;

  /* Semantic */
  --color-success: #6fba2c;
  --color-warning: #f5c31c;
  --color-error: #e05a5a;
  --color-info: #889df0;

  /* NookPhone Status Colors */
  --color-pill-success-bg: #8ac68a;
  --color-pill-success-text: #fff;
  --color-pill-error-bg: #fc736d;
  --color-pill-error-text: #fff;
  --color-pill-warning-bg: #f7cd67;
  --color-pill-warning-text: #725d42;
  --color-pill-info-bg: #889df0;
  --color-pill-info-text: #fff;
  --color-pill-default-bg: rgb(247, 243, 223);
  --color-pill-default-text: #725d42;
  --color-pill-default-border: #c4b89e;

  /* Border */
  --border-default: 2px solid #9f927d;
  --border-light: 2px solid #c4b89e;
  --border-input: 2.5px solid #c4b89e;

  /* Shadows */
  --shadow-card: 0 4px 10px rgba(107, 92, 67, 0.42);
  --shadow-deep:
    0 4px 14px rgba(107, 92, 67, 0.35),
    0 8px 28px rgba(107, 92, 67, 0.2);
  --shadow-focus: 0 0 0 3px var(--color-focus);
  --shadow-button-3d: 0 5px 0 0 #bdaea0;
  --shadow-input-3d: 0 3px 0 0 #d4c9b4;

  /* Radius */
  --radius-sm: 12px;
  --radius-md: 16px;
  --radius-lg: 20px;
  --radius-pill: 50px;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-8: 48px;

  /* Typography */
  --font-family: 'Nunito', 'Noto Sans SC', 'Zen Maru Gothic', sans-serif;

  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.375rem;
  --font-size-2xl: 1.625rem;
  --font-size-3xl: 3rem;

  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-tight: 1.23;
  --line-height-normal: 1.5;

  /* Layout */
  --sidebar-width: 220px;
  --content-max-width: 1200px;
}

/* Reset */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-normal);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  background-color: var(--color-bg);
}

a {
  color: var(--color-accent);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/index.css && git commit -m "feat(frontend): replace Notion design tokens with Animal Island UI tokens"
```

---

### Task 3: 替换 DESIGN.md

**Files:**
- Rewrite: `DESIGN.md`

- [ ] **Step 1: 从 animal-island-ui 仓库获取 DESIGN_PROMPT.md 内容**

Run:
```bash
curl -sL https://raw.githubusercontent.com/guokaigdg/animal-island-ui/main/DESIGN_PROMPT.md -o /tmp/animal-island-design-prompt.md
```

- [ ] **Step 2: 创建新的 DESIGN.md**

在文件顶部添加 Harvester 项目上下文后，粘贴 DESIGN_PROMPT.md 的全部内容。文件开头应为：

```markdown
# Harvester 设计系统

> 本设计系统基于 [animal-island-ui](https://github.com/guokaigdg/animal-island-ui) 组件库，受《集合啦！动物森友会》启发。
> 下方内容来自 animal-island-ui 的 DESIGN_PROMPT.md，定义了色板、字体、尺寸、形状、阴影和交互状态规范。

---

（此处粘贴 DESIGN_PROMPT.md 的完整内容）
```

- [ ] **Step 3: Commit**

```bash
git add DESIGN.md && git commit -m "docs: replace Notion design system with Animal Island UI design spec"
```

---

### Task 4: 更新 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新设计系统引用**

将 CLAUDE.md 中第 20 行附近的：
```
涉及前端视觉、布局、组件样式或交互状态时，必须先读根目录 `DESIGN.md`，并以其中的 Notion 风格设计系统为准。
```
替换为：
```
涉及前端视觉、布局、组件样式或交互状态时，必须先读根目录 `DESIGN.md`，并以其中的 Animal Island UI 风格设计系统为准。优先使用 `animal-island-ui` 提供的组件，参考 `AI_USAGE.md` 了解组件 API。
```

- [ ] **Step 2: 更新组件复用部分**

在 "组件复用" 部分（约第 96 行附近）的搜索列表中新增一项：

```
3. 优先检查 `animal-island-ui` 提供的组件（Button、Card、Input、Select、Modal、Switch、Tabs、Checkbox、Collapse 等）
```

同时更新编号，原来的第 3 点变为第 4 点。

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md && git commit -m "docs: update CLAUDE.md to reference Animal Island UI design system"
```

---

### Task 5: 安装 SKILL.md 为 Claude Code skill

**Files:**
- Create: `.claude/skills/animal-island-ui.md`

- [ ] **Step 1: 获取 SKILL.md 内容**

Run:
```bash
curl -sL https://raw.githubusercontent.com/guokaigdg/animal-island-ui/main/skill/SKILL.md -o /tmp/animal-island-skill.md
```

- [ ] **Step 2: 复制为 Claude Code skill 文件**

Run:
```bash
mkdir -p /Users/zhourenkang/Workspace/daydream/Harvester/.claude/skills && cp /tmp/animal-island-skill.md /Users/zhourenkang/Workspace/daydream/Harvester/.claude/skills/animal-island-ui.md
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/animal-island-ui.md && git commit -m "chore: add animal-island-ui SKILL.md as Claude Code skill"
```

---

## Phase 1：核心组件替换

### Task 6: 删除旧 UI 组件和类型

**Files:**
- Delete: `frontend/src/components/ui/button.tsx`
- Delete: `frontend/src/components/ui/card.tsx`
- Delete: `frontend/src/components/ui/confirm-dialog.tsx`
- Delete: `frontend/src/components/ui/input.tsx`
- Delete: `frontend/src/components/ui/select.tsx`
- Delete: `frontend/src/types/style.ts`

- [ ] **Step 1: 删除文件**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend/src && rm components/ui/button.tsx components/ui/card.tsx components/ui/confirm-dialog.tsx components/ui/input.tsx components/ui/select.tsx types/style.ts
```

- [ ] **Step 2: Commit**

```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester && git add -u frontend/src/components/ui/ frontend/src/types/style.ts && git commit -m "refactor(frontend): remove old Notion-style UI components"
```

---

### Task 7: 重写 StatusPill 组件

**Files:**
- Rewrite: `frontend/src/components/ui/status-pill.tsx`

StatusPill 没有直接的 animal-island-ui 对应组件，使用 NookPhone 配色系统自定义实现。保持相同的 props API（`variant` + `children`），这样使用方不需要改动 import。

- [ ] **Step 1: 重写 status-pill.tsx**

```tsx
type PillVariant = 'success' | 'error' | 'warning' | 'info' | 'default'

interface StatusPillProps {
  variant?: PillVariant
  children: React.ReactNode
}

const variantColors: Record<PillVariant, { bg: string; text: string; border?: string }> = {
  success: { bg: 'var(--color-pill-success-bg)', text: 'var(--color-pill-success-text)' },
  error: { bg: 'var(--color-pill-error-bg)', text: 'var(--color-pill-error-text)' },
  warning: { bg: 'var(--color-pill-warning-bg)', text: 'var(--color-pill-warning-text)' },
  info: { bg: 'var(--color-pill-info-bg)', text: 'var(--color-pill-info-text)' },
  default: {
    bg: 'var(--color-pill-default-bg)',
    text: 'var(--color-pill-default-text)',
    border: '2px solid var(--color-pill-default-border)',
  },
}

export function StatusPill({ variant = 'default', children }: StatusPillProps) {
  const colors = variantColors[variant]

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 12px',
        borderRadius: 'var(--radius-pill)',
        backgroundColor: colors.bg,
        color: colors.text,
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-xs)',
        fontWeight: 600,
        letterSpacing: '0.125px',
        lineHeight: 1.33,
        ...(colors.border ? { border: colors.border } : {}),
      }}
    >
      {children}
    </span>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/status-pill.tsx && git commit -m "refactor(frontend): rewrite StatusPill with NookPhone color palette"
```

---

### Task 8: 更新 table-styles.ts 和 tokens.ts

**Files:**
- Rewrite: `frontend/src/lib/table-styles.ts`
- Modify: `frontend/src/lib/tokens.ts`

- [ ] **Step 1: 更新 table-styles.ts**

```ts
import type { CSSProperties } from 'react'

export const cellStyle: CSSProperties = {
  padding: '10px var(--space-3)',
  fontSize: 'var(--font-size-sm)',
  verticalAlign: 'middle',
  borderBottom: 'var(--border-default)',
  color: 'var(--color-text-body)',
}
```

- [ ] **Step 2: 更新 tokens.ts**

```ts
export const fontWeight = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const
```

（tokens.ts 内容不变，保留即可，因为数值 token 不涉及样式系统）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/table-styles.ts frontend/src/lib/tokens.ts && git commit -m "refactor(frontend): update table-styles to use Animal Island design tokens"
```

---

## Phase 1.5：Feature 页面组件替换

以下任务逐个更新 feature 页面。每个任务的改动模式相同：
1. 替换 import 路径
2. 适配组件 API（Button variant→type, Select 受控化等）
3. 更新内联样式引用新 CSS 变量

### Task 9: 更新 overview-page.tsx

**Files:**
- Modify: `frontend/src/features/overview/overview-page.tsx`

- [ ] **Step 1: 替换 imports**

将：
```tsx
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { StatusPill } from '../../components/ui/status-pill'
```

替换为：
```tsx
import { Button, Card, Input } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
```

- [ ] **Step 2: 适配 Button 用法**

文件中所有 Button 实例：
- `<Button variant="primary"` → `<Button type="primary"`
- `<Button variant="secondary"` → `<Button type="default"`
- `<Button variant="ghost"` → `<Button type="text"`

- [ ] **Step 3: 适配 Card 用法**

所有 `<Card` 添加 `type="default"`：
- `<Card>` → `<Card type="default">`
- `<Card style={...}>` → `<Card type="default" style={...}>`

- [ ] **Step 4: 适配 Input 用法**

当前 Input 有 `label` prop，animal-island-ui Input 无此 prop。将带 label 的 Input 改为外部 label：

```tsx
// 旧:
<Input label="API 基础 URL" id="base-url" value={editConfig.baseUrl} onChange={...} />

// 新:
<label htmlFor="base-url" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--color-text-body)', marginBottom: 'var(--space-1)' }}>
  API 基础 URL
</label>
<Input id="base-url" value={editConfig.baseUrl} onChange={...} />
```

同理处理 `label="API Token"` 的 Input。

- [ ] **Step 5: 更新内联样式**

将以下 style 中的旧 token 替换为新 token：
- `color: 'var(--color-primary-text)'` → `color: 'var(--color-text-primary)'`
- `color: 'var(--color-warm-gray-500)'` → `color: 'var(--color-text-body)'`
- `color: 'var(--color-warm-gray-300)'` → `color: 'var(--color-text-secondary)'`
- `backgroundColor: 'var(--color-warm-white)'` → `backgroundColor: 'var(--color-bg-content)'`
- `backgroundColor: 'var(--color-white)'` → `backgroundColor: 'var(--color-bg-content)'`（Card 内区域）
- `border: 'var(--border-whisper)'` → `border: 'var(--border-default)'`
- `borderBottom: 'var(--border-whisper)'` → `borderBottom: 'var(--border-default)'`
- `borderRadius: 'var(--radius-lg)'` → `borderRadius: 'var(--radius-lg)'`（变量名相同但值从 12px→20px）
- `borderRadius: 'var(--radius-sm)'` → `borderRadius: 'var(--radius-sm)'`（值从 4px→12px）
- `boxShadow: 'var(--shadow-card)'` → `boxShadow: 'var(--shadow-card)'`（变量名相同但值已变）

- [ ] **Step 6: 运行类型检查**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npx tsc --noEmit 2>&1 | head -30
```

修复任何类型错误。

- [ ] **Step 7: Commit**

```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester && git add frontend/src/features/overview/overview-page.tsx && git commit -m "refactor(frontend): migrate overview page to animal-island-ui components"
```

---

### Task 10: 更新 dashboard-page.tsx

**Files:**
- Modify: `frontend/src/features/operations/dashboard-page.tsx`

- [ ] **Step 1: 替换 imports**

将 `import { Button } from '../../components/ui/button'` 替换为 `import { Button } from 'animal-island-ui'`。

- [ ] **Step 2: 适配 Button 用法**

- `variant="ghost"` → `type="text"`
- `variant="primary"` → `type="primary"`

- [ ] **Step 3: 更新内联样式**

应用通用 style token 映射（同 Task 9 Step 5）。重点修改：
- 卡片/面板背景: `var(--color-white)` → `var(--color-bg-content)`
- 文字颜色: `var(--color-primary-text)` → `var(--color-text-primary)`, `var(--color-warm-gray-500)` → `var(--color-text-body)`
- 边框: `var(--border-whisper)` → `var(--border-default)`
- 阴影: 确认引用 `var(--shadow-card)`（新值已更新）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/operations/dashboard-page.tsx && git commit -m "refactor(frontend): migrate dashboard page to animal-island-ui"
```

---

### Task 11: 更新 crawls-page.tsx

**Files:**
- Modify: `frontend/src/features/operations/crawls-page.tsx`

- [ ] **Step 1: 替换 imports**

将 `import { Button } from '../../components/ui/button'` 替换为 `import { Button } from 'animal-island-ui'`。

- [ ] **Step 2: 适配 Button + 更新内联样式**

- Button: `variant="ghost"` → `type="text"`, `variant="primary"` → `type="primary"`
- 内联样式: 应用通用 style token 映射

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/operations/crawls-page.tsx && git commit -m "refactor(frontend): migrate crawls page to animal-island-ui"
```

---

### Task 12: 更新 jobs-page.tsx

**Files:**
- Modify: `frontend/src/features/operations/jobs-page.tsx`

- [ ] **Step 1: 替换 imports**

将 `import { Button } from '../../components/ui/button'` 替换为 `import { Button } from 'animal-island-ui'`。

- [ ] **Step 2: 适配 Button + 更新内联样式**

- Button: 同上映射
- 内联样式: 应用通用 style token 映射

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/operations/jobs-page.tsx && git commit -m "refactor(frontend): migrate jobs page to animal-island-ui"
```

---

### Task 13: 更新 sources 相关页面

**Files:**
- Modify: `frontend/src/features/sources/sources-page.tsx`
- Modify: `frontend/src/features/sources/components/propose-source-form.tsx`
- Modify: `frontend/src/features/sources/components/source-row.tsx`

- [ ] **Step 1: 更新 sources-page.tsx**

替换 imports：
```tsx
// 旧:
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { StatusPill } from '../../components/ui/status-pill'

// 新:
import { Button, Input } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
```

适配 Button: `variant="primary"` → `type="primary"`, `variant="ghost"` → `type="text"`

适配 Input: 带有 `label` prop 的 Input 需要外部 label（参考 Task 9 Step 4）。

更新内联样式: 应用通用 style token 映射。

- [ ] **Step 2: 更新 propose-source-form.tsx**

替换 imports：
```tsx
// 旧:
import { Button } from '../../../components/ui/button'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'

// 新:
import { Button, Input, Select } from 'animal-island-ui'
```

适配 Select: 将 children `<option>` 模式转为受控 `options` 数组。此文件使用 Select 让用户选择 source kind。需要：

```tsx
// 旧:
<Select label="类型" id="kind" value={formKind} onChange={e => setFormKind(e.target.value)}>
  <option value="web">网页</option>
  <option value="rss">RSS</option>
  <option value="api">API</option>
</Select>

// 新:
<label htmlFor="kind" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--color-text-body)', marginBottom: 'var(--space-1)' }}>
  类型
</label>
<Select
  options={[
    { key: 'web', label: '网页' },
    { key: 'rss', label: 'RSS' },
    { key: 'api', label: 'API' },
  ]}
  value={formKind}
  onChange={setFormKind}
/>
```

注意：需要确认 Select 选项的 value 列表是否与实际文件匹配。执行时请读取文件确认 `<option>` 的实际值。

适配 Button: 映射同上。

适配 Input: 带有 `label` prop 的 Input 需要外部 label。

- [ ] **Step 3: 更新 source-row.tsx**

替换 StatusPill import（保持不变，因为 StatusPill 是自定义组件）：
```tsx
import { StatusPill } from '../../../components/ui/status-pill'
```

如果文件中有其他 UI 组件 import，按映射表替换。

更新内联样式。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/sources/ && git commit -m "refactor(frontend): migrate sources pages to animal-island-ui"
```

---

### Task 14: 更新 recipes-schedules 相关页面

**Files:**
- Modify: `frontend/src/features/recipes-schedules/recipes-page.tsx`
- Modify: `frontend/src/features/recipes-schedules/schedules-page.tsx`
- Modify: `frontend/src/features/recipes-schedules/components/recipe-row.tsx`
- Modify: `frontend/src/features/recipes-schedules/components/schedule-row.tsx`
- Modify: `frontend/src/features/recipes-schedules/components/selectors.tsx`

- [ ] **Step 1: 更新 recipes-page.tsx**

替换 imports：
```tsx
// 旧:
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'

// 新:
import { Button, Input, Select } from 'animal-island-ui'
```

适配 Select: 当前 recipes-page 使用了 filter select（审批状态、执行器）。将 `<select>` 或 Select 组件转为受控模式。读取文件确认实际用法后按以下模式适配：

```tsx
// 旧（如果使用 Select 组件）:
<Select label="审批状态">
  <option value="">全部状态</option>
  <option value="approved">已批准</option>
  ...
</Select>

// 新:
<Select
  options={[
    { key: '', label: '全部状态' },
    { key: 'approved', label: '已批准' },
    ...
  ]}
  value={approvalFilter}
  onChange={setApprovalFilter}
/>
```

如果页面中使用的是原生 `<select>` 而非 Select 组件，则保持原生元素但更新样式为新 token。

适配 Button: 映射同上。

- [ ] **Step 2: 更新 schedules-page.tsx**

与 recipes-page 相同模式替换 imports 和适配组件。

- [ ] **Step 3: 更新 recipe-row.tsx**

替换 imports（StatusPill 保持自定义组件 import）。更新内联样式。

- [ ] **Step 4: 更新 schedule-row.tsx**

同 recipe-row.tsx 模式。

- [ ] **Step 5: 更新 selectors.tsx**

此文件使用 Select 组件。将所有 Select 替换为 animal-island-ui Select，转为受控 options 数组模式。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/recipes-schedules/ && git commit -m "refactor(frontend): migrate recipes-schedules pages to animal-island-ui"
```

---

### Task 15: 更新 content 相关页面

**Files:**
- Modify: `frontend/src/features/content/content-library-page.tsx`
- Modify: `frontend/src/features/content/content-detail-modal.tsx`

- [ ] **Step 1: 更新 content-library-page.tsx**

替换 imports：
```tsx
// 旧:
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { StatusPill } from '../../components/ui/status-pill'

// 新:
import { Button, Input } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
```

适配 Button、Input、内联样式：同上。

- [ ] **Step 2: 更新 content-detail-modal.tsx**

如果此文件使用了 ConfirmDialog，替换为 Modal：

```tsx
// 旧:
import { ConfirmDialog } from '../../components/ui/confirm-dialog'
<ConfirmDialog open={...} title="..." message="..." onConfirm={...} onCancel={...} />

// 新:
import { Modal, Button } from 'animal-island-ui'
<Modal
  open={open}
  title="Title"
  onClose={onCancel}
  footer={
    <>
      <Button type="default" onClick={onCancel}>取消</Button>
      <Button type="primary" onClick={onConfirm}>确认</Button>
    </>
  }
>
  <p>Message content</p>
</Modal>
```

读取文件确认实际用法后适配。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/content/ && git commit -m "refactor(frontend): migrate content pages to animal-island-ui"
```

---

### Task 16: 更新 audit-page.tsx

**Files:**
- Modify: `frontend/src/features/audit/audit-page.tsx`

- [ ] **Step 1: 替换 imports**

audit-page 使用 Button 和可能的原生 `<select>`。

```tsx
// 旧:
import { Button } from '../../components/ui/button'

// 新:
import { Button } from 'animal-island-ui'
```

- [ ] **Step 2: 适配 Button + 更新内联样式**

- Button: 映射同上
- 原生 `<select>`: 保持原生元素（因为测试用 `user.selectOptions`），更新内联样式使用新 token
- StatusPill: 如果使用，保持自定义组件 import
- 内联样式: 应用通用 style token 映射

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/audit/audit-page.tsx && git commit -m "refactor(frontend): migrate audit page to animal-island-ui"
```

---

### Task 17: 更新 placeholder-page.tsx

**Files:**
- Modify: `frontend/src/pages/placeholder-page.tsx`

- [ ] **Step 1: 更新内联样式**

```tsx
interface PlaceholderPageProps {
  title: string
  description: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div data-testid={`page-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <h2
        style={{
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-2xl)',
          fontWeight: 700,
          letterSpacing: '-0.625px',
          lineHeight: 'var(--line-height-tight)',
          marginBottom: 'var(--space-3)',
          color: 'var(--color-text-primary)',
        }}
      >
        {title}
      </h2>
      <p
        style={{
          fontSize: 'var(--font-size-base)',
          color: 'var(--color-text-body)',
          lineHeight: 'var(--line-height-normal)',
        }}
      >
        {description}
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/placeholder-page.tsx && git commit -m "refactor(frontend): update placeholder page styles to Animal Island tokens"
```

---

## Phase 2：布局组件重样式

### Task 18: 重样式 AppLayout

**Files:**
- Modify: `frontend/src/components/common/app-layout.tsx`

- [ ] **Step 1: 更新 AppLayout 样式**

```tsx
import type { ReactNode } from 'react'

import { Sidebar } from './sidebar'
import type { NavItem } from './sidebar'

interface AppLayoutProps {
  navItems: NavItem[]
  activeKey: string
  onNavigate: (key: string) => void
  children: ReactNode
}

export function AppLayout({
  navItems,
  activeKey,
  onNavigate,
  children,
}: AppLayoutProps) {
  return (
    <div
      data-testid="app-layout"
      style={{ display: 'flex', height: '100vh', overflow: 'hidden', backgroundColor: 'var(--color-bg)' }}
    >
      <Sidebar items={navItems} activeKey={activeKey} onNavigate={onNavigate} />
      <main
        style={{
          flex: 1,
          padding: 'var(--space-6)',
          maxWidth: 'var(--content-max-width)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'var(--color-bg)',
        }}
      >
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/common/app-layout.tsx && git commit -m "style(frontend): restyle AppLayout with Animal Island background"
```

---

### Task 19: 重样式 Sidebar

**Files:**
- Modify: `frontend/src/components/common/sidebar.tsx`

- [ ] **Step 1: 重写 Sidebar 为动森风格**

```tsx
export interface NavItem {
  key: string
  label: string
}

interface SidebarProps {
  items: NavItem[]
  activeKey: string
  onNavigate: (key: string) => void
}

export function Sidebar({ items, activeKey, onNavigate }: SidebarProps) {
  return (
    <aside
      data-testid="sidebar"
      style={{
        width: 'var(--sidebar-width)',
        minHeight: '100vh',
        backgroundColor: 'var(--color-bg-content)',
        borderRight: 'var(--border-default)',
        padding: 'var(--space-4) 0',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: '0 var(--space-4) var(--space-5)',
          borderBottom: 'var(--border-default)',
          marginBottom: 'var(--space-2)',
        }}
      >
        <h1
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-lg)',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
          }}
        >
          Harvester
        </h1>
      </div>
      <nav>
        {items.map((item) => {
          const isActive = activeKey === item.key
          return (
            <button
              key={item.key}
              data-testid={`nav-${item.key}`}
              onClick={() => onNavigate(item.key)}
              style={{
                display: 'block',
                width: 'calc(100% - 16px)',
                textAlign: 'left',
                padding: '10px var(--space-4)',
                margin: '2px 8px',
                border: 'none',
                borderRadius: '12px',
                backgroundColor: isActive ? 'var(--color-bg-active)' : 'transparent',
                color: isActive
                  ? 'var(--color-text-primary)'
                  : 'var(--color-text-body)',
                fontFamily: 'var(--font-family)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)'
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }
              }}
            >
              {item.label}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/common/sidebar.tsx && git commit -m "style(frontend): restyle Sidebar with Animal Crossing theme"
```

---

### Task 20: 重样式 PaginationControls（使用 animal-island-ui Button）

**Files:**
- Modify: `frontend/src/components/common/pagination-controls.tsx`

- [ ] **Step 1: 用 animal-island-ui Button 重写 PaginationControls**

```tsx
import { Button } from 'animal-island-ui'

interface PaginationControlsProps {
  total: number
  offset: number
  pageSize: number
  onPageChange: (offset: number) => void
}

export function PaginationControls({
  total,
  offset,
  pageSize,
  onPageChange,
}: PaginationControlsProps) {
  if (total <= pageSize) return null

  const isPrevDisabled = offset === 0
  const isNextDisabled = offset + pageSize >= total
  const rangeEnd = Math.min(offset + pageSize, total)

  return (
    <div
      data-testid="pagination-controls"
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 'var(--space-4)',
        fontSize: 'var(--font-size-sm)',
        color: 'var(--color-text-body)',
      }}
    >
      <span data-testid="pagination-range">
        {offset + 1}-{rangeEnd} of {total}
      </span>
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <Button
          type="default"
          size="small"
          disabled={isPrevDisabled}
          onClick={() => onPageChange(Math.max(0, offset - pageSize))}
          data-testid="pagination-prev"
        >
          上一页
        </Button>
        <Button
          type="default"
          size="small"
          disabled={isNextDisabled}
          onClick={() => onPageChange(offset + pageSize)}
          data-testid="pagination-next"
        >
          下一页
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/common/pagination-controls.tsx && git commit -m "refactor(frontend): migrate PaginationControls to animal-island-ui Button"
```

---

## Phase 3：测试更新

### Task 21: 更新单元测试

**Files:**
- Modify: `frontend/src/features/audit/__tests__/audit-page.test.tsx`
- Modify: `frontend/src/features/operations/__tests__/dashboard-page.test.tsx`
- Modify: `frontend/src/features/operations/__tests__/crawls-page.test.tsx`
- Modify: `frontend/src/features/operations/__tests__/jobs-page.test.tsx`
- Modify: `frontend/src/features/sources/__tests__/sources-page.test.tsx`
- Modify: `frontend/src/features/content/__tests__/content-library-page.test.tsx`
- Modify: `frontend/src/features/content/__tests__/search.test.tsx`
- Modify: `frontend/src/features/content/__tests__/view-toggle.test.tsx`
- Modify: `frontend/src/features/recipes-schedules/__tests__/recipes-page.test.tsx`
- Modify: `frontend/src/features/recipes-schedules/__tests__/schedules-page.test.tsx`
- Modify: `frontend/src/features/recipes-schedules/__tests__/selectors.test.tsx`
- Modify: `frontend/src/test/app.test.tsx`

测试文件的主要修改点：

1. **移除对旧 UI 组件的 mock**：如果测试文件中有 `vi.mock('../../components/ui/button')` 等调用，删除这些 mock。animal-island-ui 组件可以直接在测试中使用。

2. **Select 测试适配**：audit-page 测试使用 `user.selectOptions(select, 'source')` 操作原生 `<select>`。如果 audit-page 保持原生 `<select>`，测试无需修改。如果替换为 animal-island-ui Select，需要改为通过 click + 选择 option 的方式。

3. **Button variant 查询**：如果测试中有通过 text 查找 variant 特定按钮的逻辑，无需修改（因为按钮文字不变）。

4. **data-testid 保持不变**：所有 data-testid 属性应保持原值。

- [ ] **Step 1: 逐个检查测试文件**

对每个测试文件运行测试确认当前状态：

```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npx vitest run 2>&1 | tail -40
```

记录哪些测试通过、哪些失败。

- [ ] **Step 2: 修复失败的测试**

根据失败信息逐一修复。主要修复模式：
- 如果有 mock 旧组件路径，删除或更新 mock 路径
- 如果 Select API 变化导致测试失败，适配测试代码
- 如果有 import 路径错误，修正路径

- [ ] **Step 3: 运行全量测试确认通过**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npx vitest run
```

Expected: 所有测试通过。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/ -u && git commit -m "test(frontend): update unit tests for animal-island-ui migration"
```

---

### Task 22: 类型检查 + 构建验证

**Files:**
- 无新增修改，纯验证

- [ ] **Step 1: 运行 TypeScript 类型检查**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npx tsc --noEmit
```

Expected: 无类型错误。如果有，逐一修复。

- [ ] **Step 2: 运行完整构建**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm run build
```

Expected: 构建成功，无错误。

- [ ] **Step 3: 运行 lint 检查**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm run lint
```

修复所有 lint 问题。

- [ ] **Step 4: 运行格式化**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm run format
```

- [ ] **Step 5: Commit 所有修复**

```bash
git add frontend/ && git commit -m "fix(frontend): resolve type errors and lint issues from UI migration"
```

---

### Task 23: 视觉验证

- [ ] **Step 1: 启动开发服务器**

Run:
```bash
cd /Users/zhourenkang/Workspace/daydream/Harvester/frontend && npm run dev
```

- [ ] **Step 2: 在浏览器中逐页检查**

打开 http://localhost:5173，逐页验证：

1. **概览页**：页面背景应为奶油米白 `#f8f8f0`，文字为温暖棕色，按钮为 pill 形状，卡片圆角 20px
2. **仪表盘**：指标卡片使用新样式，状态标签使用 NookPhone 配色
3. **信息源**：表格使用新 border 样式，Select 下拉为 animal-island-ui 风格
4. **采集配方/调度计划**：同上
5. **抓取任务/作业队列**：同上
6. **内容库**：同上
7. **审计日志**：时间线使用新配色，原生 select 保持功能但样式更新
8. **侧边栏**：圆角菜单项，hover 浅蓝，active 深蓝背景

重点检查：
- 所有按钮是否有 3D 底部阴影
- 输入框是否为 pill 形状
- 字体是否为 Nunito（非 Inter）
- 整体配色是否为暖色调（非灰色）
- 没有残留的 Notion 蓝色 `#0075de`

- [ ] **Step 3: 记录并修复视觉问题**

如果发现样式问题，记录并逐一修复。

---

## 注意事项

1. **animal-island-ui Select 是纯受控组件**：`value` 和 `onChange` 都是 required，没有 `defaultValue`。迁移时必须为每个 Select 提供 state。
2. **Button 没有 `variant` prop**：使用 `type` prop，取值为 `primary | default | dashed | text | link`。
3. **Input 没有 `label` prop**：需要在使用处外层添加 `<label>` 元素。
4. **Card 需要 `type` prop**：`type="default"` 为标准卡片，`type="title"` 为标题卡片。
5. **不要覆盖 Button 的 3D 阴影**：这是 animal-island-ui 的核心视觉标识。
6. **不要强制覆盖圆角为 0**：所有交互元素应保持 pill 形状。
7. **CSS 变量名已更新**：从 Notion 风格名称（如 `--color-notion-blue`）改为语义名称（如 `--color-accent`），更新所有引用。
8. **data-testid 必须保持不变**：E2E 测试依赖这些属性。
