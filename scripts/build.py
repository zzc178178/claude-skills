"""AI Note 笔记组装脚本
读取 content.json + template.html，替换占位符生成最终 HTML。
大幅节省 LLM 输出 token（LLM 只需生成内容 JSON，无需输出模板代码）。

目录结构：
  输出目录/
  ├── _content/          ← 源码目录（所有 _content.json 放这里）
  │   └── xxx_content.json
  ├── xxx.html           ← HTML 输出（与 _content/ 同级）
  └── ...

用法:
  python scripts/build.py ai-note-output/_content/xxx_content.json
  python scripts/build.py ai-note-output/_content/              # 批量构建目录下所有 JSON
"""
import sys
import json
import os
import re


def find_template():
    """查找模板文件"""
    # 1. skill 目录（开发环境）
    skill_path = os.path.join(
        os.path.expanduser('~'),
        '.claude', 'skills', 'ai-note-2.0', 'assets', 'template.html'
    )
    if os.path.exists(skill_path):
        return skill_path

    # 2. 项目 scripts 同级
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'template.html')
    if os.path.exists(local_path):
        return os.path.abspath(local_path)

    # 3. 当前目录
    cwd_path = os.path.join(os.getcwd(), 'template.html')
    if os.path.exists(cwd_path):
        return os.path.abspath(cwd_path)

    print(f"[FAIL] 未找到模板文件")
    print(f"  预期位置: {skill_path}")
    sys.exit(1)


def read_json_safe(path):
    """读取 JSON，解析失败时尝试自动修复并给出精确诊断"""
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()

    # 1. 直接尝试解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        _exc = e

    # 2. 诊断：定位出错位置，输出上下文
    lines = raw.split('\n')
    line_no = _exc.lineno
    col_no = _exc.colno
    context_start = max(0, line_no - 3)
    context_end = min(len(lines), line_no + 2)
    print(f"[WARN] JSON 解析失败: 第 {line_no} 行, 第 {col_no} 列 — {_exc.msg}")
    print(f"  上下文:")
    for i in range(context_start, context_end):
        marker = ' >>>' if i == line_no - 1 else '    '
        print(f"  {marker} {i+1}: {lines[i][:120]}")

    # 3. 自动修复：将 HTML 属性中的双引号替换为单引号
    print(f"[FIX] 尝试自动修复：将 HTML 属性双引号 → 单引号...")
    # Pattern: inside HTML tags, replace attribute double quotes with single quotes
    # Match: <tag attr="value"> → <tag attr='value'>
    fixed = re.sub(
        r'(<[a-zA-Z][^>]*)\b([a-zA-Z-]+)="([^"]*)"([^>]*>)',
        r"\1\2='\3'\4",
        raw
    )
    # May need multiple passes for multiple attributes on one tag
    for _ in range(5):
        new_fixed = re.sub(
            r'(<[a-zA-Z][^>]*)\b([a-zA-Z-]+)="([^"]*)"([^>]*>)',
            r"\1\2='\3'\4",
            fixed
        )
        if new_fixed == fixed:
            break
        fixed = new_fixed

    try:
        data = json.loads(fixed)
        # Save fixed version back
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[FIX] 自动修复成功，已更新 JSON 文件")
        return data
    except json.JSONDecodeError as e2:
        print(f"[FAIL] 自动修复失败: {e2.msg}")
        print(f"  请检查 JSON 文件中是否有多余/缺失的引号、逗号或转义字符")
        sys.exit(1)


def build(json_path):
    template_path = find_template()

    # 读取模板
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 读取内容 JSON（带自动修复）
    data = read_json_safe(json_path)

    # 将 null 字段转为空字符串，避免 str.replace 崩溃
    for key in ['title', 'subtitle', 'tag', 'source', 'text_content', 'diagram_content']:
        if data.get(key) is None:
            data[key] = ''
            print(f"  [WARN] 字段 '{key}' 为 null，已转为空字符串")

    # 验证必要字段
    required = ['title', 'tag', 'subtitle', 'source', 'text_content', 'diagram_content']
    for key in required:
        if key not in data:
            raise ValueError(f"[FAIL] 缺少必要字段: {key}")

    # 校验 source 格式（允许空字符串，仅非空时校验）
    source = data['source']
    if source and ('note-source' not in source or 'source-link' not in source):
        raise ValueError(
            f"[FAIL] source 字段格式错误，缺少 note-source 包装结构\n"
            f"正确格式: <div class='note-source'><span class='source-label'>原文来源</span><a class='source-link' href='...' target='_blank'>名称</a></div>"
        )

    # 替换占位符
    html = template
    for ph, key in [('NOTE_TITLE', 'title'), ('NOTE_SUBTITLE', 'subtitle'),
                     ('NOTE_TAG', 'tag'), ('NOTE_SOURCE', 'source'),
                     ('TEXT_CONTENT', 'text_content'), ('DIAGRAM_CONTENT', 'diagram_content')]:
        html = html.replace(f'<!-- {ph} -->', str(data[key]))

    # 确定输出路径：使用 JSON 中的 title 字段作为文件名（支持中文）
    safe_title = re.sub(r'[\\/:*?"<>|]', '', str(data['title'])).strip()
    if not safe_title:
        safe_title = 'ai_note_' + os.path.splitext(os.path.basename(json_path))[0]
    # 限制文件名长度，避免过长
    if len(safe_title) > 50:
        safe_title = safe_title[:50]
    output_name = safe_title + '.html'

    json_abs = os.path.abspath(json_path)
    # 如果 JSON 在 _content/ 子目录中，输出到父目录；否则输出到同级
    if os.path.basename(os.path.dirname(json_abs)) == '_content':
        out_dir = os.path.dirname(os.path.dirname(json_abs))  # _content/ 的父目录
    else:
        out_dir = os.path.dirname(json_abs)
    output_path = os.path.join(out_dir, output_name)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] 笔记已生成: {output_path}（{len(html)} 字符）")


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/build.py <content_json_path>")
        print("      python scripts/build.py <_content_dir>   # 批量构建目录下所有 _content.json")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        sys.exit(1)

    # 如果是目录，批量处理所有 _content.json
    if os.path.isdir(path):
        json_files = [f for f in os.listdir(path) if f.endswith('_content.json')]
        if not json_files:
            print(f"[WARN] 目录下未找到 _content.json 文件: {path}")
            sys.exit(0)
        total = len(json_files)
        ok = 0
        fail = 0
        for i, fname in enumerate(json_files, 1):
            fpath = os.path.join(path, fname)
            print(f"\n[{i}/{total}] 处理: {fname}")
            try:
                build(fpath)
                ok += 1
            except Exception as e:
                print(f"  [FAIL] {e}")
                fail += 1
        print(f"\n{'='*40}\n批量完成: ✅ {ok} 成功, ❌ {fail} 失败 / 共 {total}")
        if fail > 0:
            sys.exit(1)
    else:
        build(path)


if __name__ == '__main__':
    main()
