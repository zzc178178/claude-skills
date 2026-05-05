# AI Note 2.0 — 双页签图文笔记生成器

AI 笔记生成技能（CodeBuddy/Claude/Trae 通用），支持对任何内容生成精美双页签 HTML 笔记。

## 功能

- 📝 **双页签笔记**：文字笔记 + 图解，固定在底部方便切换
- 🎨 **多种图解模式**：Mermaid 流程图、CSS 卡片网格、步骤列表、标签组
- ✏️ **随手记**：可编辑的"我的笔记"页签，自动保存
- 🎯 **自动校验**：生成后检查 HTML、CSS、Mermaid 语法

## 使用

将 `SKILL.md` 及 `assets/`、`references/` 放入 IDE 技能目录：

```
%USERPROFILE%\.claude\skills\ai-note-2.0\
```

在 IDE 中说出触发词：`AI 笔记` / `生成笔记` / `AI note`

## 样例预览

以下为 ai-note 生成的笔记样例，可直接在线预览：

- [🧠 Agent 记忆提取触发策略：四大框架对比解析](https://zzc178178.github.io/claude-skills/examples/Agent%20%E8%AE%B0%E5%BF%86%E6%8F%90%E5%8F%96%E8%A7%A6%E5%8F%91%E7%AD%96%E7%95%A5%EF%BC%9A%E5%9B%9B%E5%A4%A7%E6%A1%86%E6%9E%B6%E5%AF%B9%E6%AF%94%E8%A7%A3%E6%9E%90.html)
- [⚙️ RAG 从 Demo 到生产](https://zzc178178.github.io/claude-skills/examples/RAG%E4%BB%8EDemo%E5%88%B0%E7%94%9F%E4%BA%A7.html)

## 配套阅读器

生成的笔记推荐导入 **[知录](https://github.com/zzc178178/zhilu-note)** — 专为 ai-note 设计的笔记管理 PWA，支持：
- PWA 安装到桌面
- 双页签切换
- 离线阅读
- 跨设备云同步
