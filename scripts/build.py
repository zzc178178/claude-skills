"""AI Note 笔记组装脚本
读取 content.json + template.html，替换占位符生成最终 HTML。
大幅节省 LLM 输出 token（LLM 只需生成内容 JSON，无需输出模板代码）。

用法:
  python scripts/build.py ai-note-output/xxx_content.json

输出:
  ai-note-output/xxx.html
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
        pass

    # 2. 诊断：定位出错位置，输出上下文
    lines = raw.split('\n')
    line_no = e.lineno
    col_no = e.colno
    context_start = max(0, line_no - 3)
    context_end = min(len(lines), line_no + 2)
    print(f"[WARN] JSON 解析失败: 第 {line_no} 行, 第 {col_no} 列 — {e.msg}")
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

    # 验证必要字段
    required = ['title', 'tag', 'subtitle', 'source', 'text_content', 'diagram_content']
    for key in required:
        if key not in data:
            print(f"[FAIL] 缺少必要字段: {key}")
            sys.exit(1)

    # 替换占位符
    html = template
    html = html.replace('<!-- NOTE_TITLE -->', data['title'])
    html = html.replace('<!-- NOTE_SUBTITLE -->', data['subtitle'])
    html = html.replace('<!-- NOTE_TAG -->', data['tag'])
    html = html.replace('<!-- NOTE_SOURCE -->', data['source'])
    html = html.replace('<!-- TEXT_CONTENT -->', data['text_content'])
    html = html.replace('<!-- DIAGRAM_CONTENT -->', data['diagram_content'])

    # 确定输出路径
    json_basename = os.path.basename(json_path)
    if json_basename.endswith('_content.json'):
        output_name = json_basename.replace('_content.json', '.html')
    else:
        safe_title = re.sub(r'[\\/:*?"<>|]', '', data['title']).strip()
        output_name = safe_title + '.html'

    out_dir = os.path.dirname(os.path.abspath(json_path))
    output_path = os.path.join(out_dir, output_name)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] 笔记已生成: {output_path}（{len(html)} 字符）")


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/build.py <content_json_path>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        sys.exit(1)

    build(path)


if __name__ == '__main__':
    main()
