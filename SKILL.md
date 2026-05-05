---
name: ai-note-2.0
description: 生成AI笔记（双页签图文笔记）。触发词：AI笔记、AI note、生成笔记、图文笔记、summary note、知识总结、做笔记、整理笔记、AI note、双页签。支持对任何内容（网页文章、音视频、文本）生成精美双页签HTML笔记，类似抖音AI笔记样式。包含固定在底部的「文字笔记」和「图解」两个页签，方便滑动后快速切换。
---

# AI Note - 双页签图文笔记生成器

## 工作流程

### 1. 内容获取阶段

根据用户输入获取内容：

- **URL链接**：使用 `web_fetch` 工具获取文章/页面内容
- **文字内容**：直接使用用户提供的内容
- **音视频**：搜索相关摘要或使用用户提供的文字描述
- **关键词**：使用 `web_search` 搜索相关信息

### 2. 内容分析阶段

提取核心信息，结构化组织：

- 提炼 3-8 个核心知识点
- 梳理知识点之间的逻辑关系
- 准备文字版笔记内容（markdown格式）
- 准备图解版内容（流程图/序列图/树形图/关系图）

### 3. 生成内容 JSON（核心步骤）

> ⚡ **Token 优化**：LLM 只生成内容 JSON（约 200-300 行），由 `scripts/build.py` 从模板组装最终 HTML（约 1200 行）。比直接生成完整 HTML **节省约 75% 输出 token**。

#### JSON 格式

将笔记内容输出为 JSON 文件，保存到 `ai-note-output/xxx_content.json`：

```json
{
  "title": "笔记标题（简短）",
  "subtitle": "副标题/补充说明",
  "tag": "分类标签",
  "source": "原文链接 HTML（无 URL 则为空字符串）",
  "text_content": "文字页签的完整 HTML 内容",
  "diagram_content": "图解页签的完整 HTML 内容"
}
```

> ⚠️ **JSON 内 HTML 属性必须使用单引号**：由于 `text_content` 和 `diagram_content` 是 JSON 双引号字符串，内部 HTML 的属性值必须用**单引号**包裹，避免转义冲突。
>
> ✅ 正确：`<div class='tag-pill tag-blue'>口径定义</div>`
> ❌ 错误：`<div class="tag-pill tag-blue">口径定义</div>` — 双引号在 JSON 字符串内需要转义为 `\"`，极易出错导致 JSON 解析失败
>
> 此规则适用于所有 HTML 属性：`class`、`style`、`onclick`、`id` 等，一律使用单引号。

#### 文字页签（text_content）填充规则
- 使用层级标题、列表、引用块、高亮等丰富样式
- 包含关键词标注、重点高亮、图标装饰
- 参考下方的`文字页签（📝 完整阐述）`详细规则

#### 图解页签（diagram_content）填充规则
- 参考下方的`图解页签（🎨 视觉总结）`详细规则
- **Mermaid 优先级降低**：仅强架构/链路内容才用，简单线性用 CSS Flow Nodes
- 每个图解模块用 `diagram-section` 容器包裹

#### 来源（source）填充规则
- 如果内容是**从 URL 获取的**，渲染为模板中的链接样式
- 如果内容是**用户直接输入的（无 URL）**，则填入空字符串
- 模板中 `.note-source` 的参考 HTML 结构：

```html
<div class="note-source">
  <span class="source-label">原文来源</span>
  <a class="source-link" href="https://..." target="_blank">公众号名称</a>
</div>
```

### 4. 组装 + 校验

#### 组装 HTML

```bash
cd <项目目录>
python scripts/build.py "ai-note-output/xxx_content.json"
```

- 读取 `ai-note-2.0/assets/template.html` 作为模板
- 替换 `<!-- NOTE_TITLE -->`、`<!-- TEXT_CONTENT -->` 等 6 个占位符
- 输出到 `ai-note-output/xxx.html`

#### 自动校验（必做步骤）

```bash
python scripts/validate.py "ai-note-output/<输出文件名>.html"
```

校验项：
- 检查 HTML 标签是否完整闭合
- 检查占位符是否都已替换（`<!-- NOTE_TITLE -->` 等残留）
- 检查 Mermaid 常见语法问题（subgraph 缺引号、并行边 `&`、禁用类型、特殊字符 `≥→≤≠≈∈` 等）
- 检查 CSS 样式完整性（HTML 中使用的 class 是否在 `<style>` 中有定义）
- 检查 `<style>` 块是否被截断（长度过短则告警）

> 校验通过输出 `[OK] 校验通过，无异常`，失败时输出 `[WARNING]` 问题列表。**校验失败必须修正后重新生成，不得跳过此步骤。**

可选 E2E 校验（零依赖，轻量无开销）：

```bash
python scripts/validate.py --e2e "ai-note-output/<输出文件名>.html"
```

额外检查：
- 启动 HTTP 服务验证文件可正常网络加载
- 检查关键结构元素（header/tab导航/文字内容/图解容器/Mermaid CDN）
- 扫描页面中是否有 "渲染失败" 等错误关键词
- 输出可点击的 `http://localhost:8899/xxx.html` 链接，方便浏览器预览

## 设计要求

### 视觉风格
- 现代、清新、信息层级清晰
- 柔和的主色调（蓝/紫/青为主）
- 圆角卡片 + 柔和阴影
- 平滑的页签切换动画
- 适当留白，呼吸感

### 📐 头部组件高度标准

模板中 `.note-header` 的尺寸参考 `ai_note_RAG生产环境_20260504.html`：

| 属性 | 标准值 |
|---|---|
| `padding` | 20px 24px |
| `border-radius` | 16px |
| `h1 font-size` | 1.4rem |
| `.subtitle font-size` | 0.85rem |
| `.note-tag` | padding 3px 10px, font-size 0.7rem |

保持紧凑，不要加额外的 `.note-meta`、`.note-author` 等元素增加高度。

### 📐 图解模块高度标准

每个图解模块的高度参考 `ai_note_RAG生产环境_20260504.html` 中的对应模块：

| 模式 | 参考模块 | 高度约 | 内容上限 |
|---|---|---|---|
| Mermaid TB | RAG整体架构 | 一轮屏 | 9个节点（含4分支） |
| Mermaid LR | 生成控制 | 半轮屏 | 5个节点 |
| 三列卡片（无图标） | 数据准备 | 一轮屏 | 3卡×3行 + 效果条 |
| 三列卡片（带图标） | 混合检索 | 一轮屏 | 3卡×5行 + 信息条 + 效果条 |
| 纵向步骤 | 意图识别 | 一轮屏 | 3步 + 路由条 |
| 两列标签 | 工程协同 | 半轮屏 | 4卡×1行标题 + 标签组 |
| CSS Tree | 选型决策树 | 一轮屏 | 3-4层深度 |

注意保持内容精炼，不要让单个模块超出参考示例的高度。如需更多内容，拆成多个模块而非堆在一个模块里。

### ⚠️ 两页签的核心分工原则

```
文字页签 = 完整阐述  —  从头读到尾，理解知识
图解页签 = 视觉总结  —  扫一眼就懂，快速回顾
```

**关键判断标准**：问自己"这个内容读者是**逐行阅读**理解的，还是**一眼扫过去**就能抓住对比结论的？"
- 逐行阅读 → 文字页签
- 扫一眼就懂 → 图解页签

---

### 文字页签（📝 完整阐述）

只能放需要**读者逐行阅读**才能理解的内容：

- 大标题 + 副标题
- 用彩色标签/徽章标注分类
- ✅ **文字页签无卡片组件**，所有内容以纯文字形式呈现：
  - 正文标题和段落：`h2/h3/p/ul/ol`
  - 单条重点强调：`.highlight-box`（蓝/橙/绿竖条）
  - 引用观点：`blockquote`（灰竖条斜体）
  - 源码示例：`pre > code`
  - 对比数据：`table`
  - 内联标记：`.tag-*`（圆角彩色标签）
  - 底部关键词：`.footer-tags`
- ❌ **不要出现任何卡片样式组件**（概念卡、网格卡等），有对比需求归图解页签
- ✅ **文中内嵌的说明性表格**（如"CRUD 四操作分类表"，读者需要对照上下文看每一行的含义）
  - 判断标准：表格行是独立的"条目解释"，不是"汇总对比"
- 列表、引用块、高亮框
- 代码块（完整源码示例）
- 重点内容使用彩色底纹高亮
- 底部加上标签信息

---

### 图解页签（🎨 视觉总结）

只能放**一眼扫过去就能获得洞察**的视觉内容：

#### 视觉图表类型选型规则

> ⚠️ **Mermaid 优先级调低**：Mermaid 渲染依赖 CDN 且有语法风险，优先使用纯 CSS 方案。仅当内容包含**强架构/多分支/循环链路**（如系统架构图、复杂决策流）才用 Mermaid 流程图。
> **简单的线性顺序（≤4 节点）改用 CSS Flow Nodes**，零依赖零风险。

```
复杂系统架构/多分支流程图（>4 节点）  → Mermaid flowchart TB（纵向）
强链路但节点少（≤6 有分支）           → Mermaid flowchart LR（横向）
并列概念/3个方案对比                  → 纯CSS三列卡片网格（1fr 1fr 1fr，无图标/带图标均可）
多步骤递进（1→2→3）                  → 纯CSS纵向flex卡片+序号圆形
简单线性流程（≤4 无分支）             → CSS Flow Nodes（纯标签节点）
多维度信息分组                        → 纯CSS两列网格卡片+标签组
汇总对比表（多主体×多维度）            → HTML 表格
特征对比卡片                          → CSS .diagram-card（搭配渐变背景）
树形结构（分类/选型）                 → CSS Tree（零依赖，见下方规则）
```

**选型总原则**：**一眼扫过去能抓住结论**的才放图解页签。需要逐行阅读理解的放文字页签。

**表格规则**：所有表格（包括汇总对比表）统一放文字页签。图解页签中如需展示对比，改用卡片/标签/树形结构替代。

---

#### 6种布局模式详解

##### 模式① · Mermaid 流程图（LR 优先 / TB 兜底）

适用：流程图/流程链

**LR 优先**：`flowchart LR` 横向布局为默认选择，紧凑不占页面高度。

```html
<div class="diagram-section">
  <h3>🏗️ 系统核心流程</h3>
  <div class="diagram-desc">从输入到输出的完整流程</div>
  <div class="mermaid">
flowchart LR
    Q[用户输入] --> E[Embedding]
    E --> VEC[(向量库)]
    VEC --> ANN{ANN 搜索}
    ANN --> Res[结果]
  </div>
</div>
```

> 通过精简节点文本（4字以内）可使 6-8 个节点在 LR 下一排展示。

**TB 兜底**：仅在满足以下**任意一条**时才使用 `flowchart TB` 纵向布局：
- 节点数 > 8 个
- 分支 > 4 条（含复杂的循环回路）
- 节点文本单行放不下（如含长参数说明）

```html
<div class="mermaid">
flowchart TB
    U[用户Query] --> QI[Query理解]
    QI --> Route{意图路由}
    Route -->|知识问答| Search[混合检索]
    Route -->|计算求解| Calc[计算模块]
    Route -->|闲聊| Chat[LLM对话]
    KBase[(知识库)] -.-> Search
    Search --> Gen[生成]
    Gen --> Score{置信度}
    Score -->|达标| Ans[回答]
    Score -->|不足| Re[二次检索]
    Re --> Gen
  </div>
</div>
```

- **⚠️ 避免在 Mermaid 文本中使用 `≥`、`→`、`_`（下划线）等特殊符号**，改用 `>=`、`->`、变量名不加下划线（如 `running=True`）

---

##### 模式② · 纯CSS三列卡片网格（无图标）

适用：**3个并列概念/方案/要点，卡片描述需要读字**

```html
<div class="diagram-section">
  <h3>📦 标题</h3>
  <div class="diagram-desc">说明文字</div>
  <div class="diagram-grid-3">
    <div class="grid-card">
      <div class="grid-card-label">📄 小标签</div>
      <div class="grid-card-title">标题</div>
      <div class="grid-card-desc">描述文字</div>
    </div>
    <div class="grid-card">
      <div class="grid-card-label">🔗 小标签</div>
      <div class="grid-card-title">标题</div>
      <div class="grid-card-desc">描述文字</div>
    </div>
    <div class="grid-card">
      <div class="grid-card-label">📐 小标签</div>
      <div class="grid-card-title">标题</div>
      <div class="grid-card-desc">描述文字</div>
    </div>
  </div>
  <div class="effect-bar">📊 效果：召回准确率从 0.62 提升至 0.84</div>
</div>
```

---

##### 模式③ · 纯CSS三列卡片网格（带大图标+边框）

适用：**3种方法/产品对比，需要视觉锚点，一眼区分**

```html
<div class="diagram-section">
  <h3>🎯 混合检索：三重保障</h3>
  <div class="diagram-desc">说明文字</div>
  <div class="diagram-grid-3">
    <div class="grid-card grid-card-icon">
      <div class="grid-card-label">方法一</div>
      <div class="grid-card-emoji">🧮</div>
      <div class="grid-card-title">向量检索</div>
      <div class="grid-card-sub">BGE-large-zh模型</div>
      <div class="grid-card-desc">语义相似度匹配</div>
    </div>
    <!-- 重复 ×3 -->
  </div>
  <div class="info-bar">
    <span>召回阈值 0.72</span><span class="bar-sep">|</span>
    <span>语义模糊→向量</span><span class="bar-sep">|</span>
    <span>关键词精确→BM25</span>
  </div>
  <div class="effect-bar">📊 效果：召回准确率从 0.84 提升至 0.91</div>
</div>
```

---

##### 模式④ · 纯CSS纵向卡片（带序号圆形标记）

适用：**步骤递进/阶梯方案/多级分类（1→2→3顺序关系）**

```html
<div class="diagram-section">
  <h3>🧠 Query理解：三级方案</h3>
  <div class="diagram-desc">说明文字</div>
  <div class="step-list">
    <div class="step-item" style="background:#e8f0fe;">
      <div class="step-circle" style="background:#667eea;">1</div>
      <div class="step-content">
        <div class="step-title">第一级 · 规则匹配 <span class="step-tag" style="color:#667eea;">⚡ 零延迟</span></div>
        <div class="step-desc">描述文字</div>
      </div>
    </div>
    <div class="step-item" style="background:#f0ebff;">
      <div class="step-circle" style="background:#7c3aed;">2</div>
      <div class="step-content">
        <div class="step-title">第二级 · BERT分类器 <span class="step-tag" style="color:#7c3aed;">⏱ 几十毫秒</span></div>
        <div class="step-desc">描述文字</div>
      </div>
    </div>
    <div class="step-item" style="background:#fef4e8;">
      <div class="step-circle" style="background:#f59e0b;">3</div>
      <div class="step-content">
        <div class="step-title">第三级 · LLM兜底 <span class="step-tag" style="color:#f59e0b;">🧠 最强理解</span></div>
        <div class="step-desc">描述文字</div>
      </div>
    </div>
  </div>
  <div class="info-bar" style="text-align:center;">
    <strong>🔀 路由分发：</strong>知识问答→混合检索 | 闲聊→LLM对话
  </div>
</div>
```

颜色递进规范：蓝(`#e8f0fe`/`#667eea`) → 紫(`#f0ebff`/`#7c3aed`) → 橙(`#fef4e8`/`#f59e0b`)

---

##### 模式⑤ · CSS Flow Nodes（简单线性流程）

适用：**简单线性流程（≤4节点，无分支）** — 替代 Mermaid LR 的低风险方案

```html
<div class="diagram-section">
  <h3>✍️ 生成阶段流程</h3>
  <div class="diagram-desc">说明文字</div>
  <div class="css-flow">
    <div class="css-flow-row">
      <span class="css-node blue">检索结果</span>
      <span class="css-arrow">→</span>
      <span class="css-node blue">Prompt组装</span>
      <span class="css-arrow">→</span>
      <span class="css-node blue">LLM生成</span>
      <span class="css-arrow">→</span>
      <span class="css-node green">输出回答</span>
    </div>
  </div>
</div>
```

- 节点数控制在 **≤4 个**
- 超过4个或含分支 → 改用 Mermaid LR（模式①·LR）
- 零依赖，零语法风险，纯 CSS 渲染

---

##### 模式⑥ · 纯CSS两列网格+标签组

适用：**多维度信息分组/功能要点/工程细节**

```html
<div class="diagram-section">
  <h3>⚡ 工程协同：系统性优化</h3>
  <div class="diagram-desc">说明文字</div>
  <div class="tag-grid-2">
    <div class="tag-card">
      <div class="tag-card-title">📤 文档管理</div>
      <div class="tag-group">
        <span class="tag-pill tag-blue">增量更新脚本</span>
        <span class="tag-pill tag-blue">差异化embedding</span>
      </div>
    </div>
    <div class="tag-card">
      <div class="tag-card-title">🎯 检索性能</div>
      <div class="tag-group">
        <span class="tag-pill tag-purple">Milvus分区索引</span>
        <span class="tag-pill tag-purple">只检索相关分区</span>
      </div>
    </div>
    <div class="tag-card">
      <div class="tag-card-title">⚡ 响应速度</div>
      <div class="tag-group">
        <span class="tag-pill tag-green">高频query缓存</span>
        <span class="tag-pill tag-green">流式输出</span>
      </div>
    </div>
    <div class="tag-card">
      <div class="tag-card-title">📊 监控指标</div>
      <div class="tag-group">
        <span class="tag-pill tag-orange">召回准确率</span>
        <span class="tag-pill tag-orange">投诉率</span>
        <span class="tag-pill tag-orange">响应延迟</span>
      </div>
    </div>
  </div>
</div>
```

标签颜色对应：`tag-blue`(功能) / `tag-purple`(技术) / `tag-green`(性能) / `tag-orange`(监控)

---

#### 选型速查表（Mermaid 优先级降低）

| 内容类型 | 使用组件 | 原因 |
|---|---|---|
| 强架构/复杂分支流程（>4节点） | **Mermaid**（LR优先，TB兜底） | 需要SVG箭头+分支，不适合CSS |
| 简单线性流程（≤4节点，无分支） | **CSS Flow Nodes** | 零依赖，零语法风险 |
| 并列概念/方案对比 | 模式② 三列卡片 | 并列对比，一眼看完 |
| 方案对比+视觉锚点 | 模式③ 三列卡片+图标 | emoji帮区分 |
| 步骤递进（1→2→3） | 模式④ 纵向+序号 | 顺序关系 |
| 多维信息分组 | 模式⑥ 两列+标签 | 分类不占行 |
| 树形分类/选型 | CSS Tree | 层级缩进+连接线 |
| 汇总对比/说明性表格 | **放文字页签** | 表格需读单元格文字 |
| 阶段标签/并列指示 | CSS Flow Nodes（纯标签，无箭头） | 仅非流程的阶段标注 |

### 随手记页签（✏️ 用户自定义）

第三个页签，模板已内置，**生成时无需修改**：
- 默认空白，`contenteditable` 富文本编辑
- 内容自动保存到 `localStorage`，key 以笔记标题区分
- 用户在此写自己的总结/想法

## 参考模板

完整HTML模板见 `assets/template.html`
