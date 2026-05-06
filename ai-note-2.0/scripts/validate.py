"""ai-note 后处理校验脚本
检查 HTML 标签闭合、Mermaid 语法问题、CSS 样式完整性、占位符替换；
可选 --e2e 模式启动 HTTP 服务做轻量 E2E 检查。
仅使用 Python 内置库，无外部依赖。
"""
import sys
import re
import os
import threading
import urllib.request
import http.server
import socketserver
from html.parser import HTMLParser

SELF_CLOSING = {'br','hr','img','input','meta','link','area','base','col','embed','source','track','wbr'}

REQUIRED_CSS_CLASSES = {
    'tree-wrap':         'CSS Tree',
    'node-root':         'CSS Tree 根节点',
    'node-label':        'CSS Tree 节点标签',
    'node-leaf':         'CSS Tree 叶节点',
    'tree-tag':          'CSS Tree 标签',
    'diagram-grid-3':    '三列网格卡片',
    'diagram-grid-4':    '四列网格卡片',
    'diagram-grid-auto': '自适应网格卡片',
    'grid-card':         '网格卡片项',
    'grid-card-icon':    '带图标卡片',
    'grid-card-label':   '卡片标签',
    'grid-card-title':   '卡片标题',
    'grid-card-emoji':   '卡片 emoji',
    'grid-card-sub':     '卡片副标题',
    'grid-card-desc':    '卡片描述',
    'step-list':         '纵向步骤卡片',
    'step-item':         '步骤项',
    'step-circle':       '步骤序号圆形',
    'step-content':      '步骤内容',
    'step-title':        '步骤标题',
    'step-desc':         '步骤描述',
    'step-tag':          '步骤标签',
    'tag-grid-2':        '两列标签卡片',
    'tag-card':          '标签卡片项',
    'tag-card-title':    '标签卡片标题',
    'tag-group':         '标签组',
    'tag-pill':          '标签胶囊',
    'effect-bar':        '效果条',
    'info-bar':          '信息条',
    'highlight-box':     '高亮框',
    'css-flow':          'CSS Flow Nodes',
    'css-flow-row':      'CSS Flow 行',
    'css-node':          'CSS Flow 节点',
    'css-arrow':         'CSS Flow 箭头',
    'diagram-section':   '图解模块容器',
    'diagram-desc':      '图解说明文字',
}

MERMAID_FORBIDDEN_CHARS = {
    '≥': '改用 >=',
    '→': '删除或改用 ->',
    '≤': '改用 <=',
    '≠': '改用 !=',
    '≈': '改用 ~=',
    '∈': '改用 in',
    '_': '变量名避免下划线（如 running=True 而非 running_True）',
}

PLACEHOLDER_PATTERN = re.compile(r'<!--\s*(NOTE_TITLE|NOTE_SUBTITLE|NOTE_TAG|NOTE_SOURCE|TEXT_CONTENT|DIAGRAM_CONTENT)\s*-->')


class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in SELF_CLOSING:
            self.tags.append(tag)

    def handle_endtag(self, tag):
        if tag not in SELF_CLOSING:
            if self.tags and self.tags[-1] == tag:
                self.tags.pop()
            else:
                self.errors.append(
                    f"标签错配: 遇到 </{tag}> 时栈顶为 <{self.tags[-1] if self.tags else '?'}>"
                )


def extract_css_classes(css_text):
    classes = set()
    for m in re.finditer(r'\.([a-zA-Z_][\w-]*)', css_text):
        classes.add(m.group(1))
    return classes


def extract_html_classes(html_text):
    classes = set()
    # 匹配双引号 class="xxx" 和单引号 class='xxx'
    for m in re.finditer(r'''class=["']([^"']+)["']''', html_text):
        for cls in m.group(1).split():
            classes.add(cls)
    return classes


def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    errors = []

    # ── 1. HTML 标签闭合 ──
    checker = TagChecker()
    try:
        checker.feed(content)
        if checker.tags:
            errors.append(f"未闭合标签: {', '.join(checker.tags)}")
        errors.extend(checker.errors)
    except Exception as e:
        errors.append(f"HTML 解析异常: {e}")

    # ── 2. 占位符残留检查 ──
    unreplaced = PLACEHOLDER_PATTERN.findall(content)
    if unreplaced:
        errors.append(f"占位符未替换: {', '.join(sorted(set(unreplaced)))}")

    # ── 3. Mermaid 检查 ──
    blocks = re.findall(r'<div class="mermaid"[^>]*>(.*?)</div>', content, re.DOTALL)
    for i, block in enumerate(blocks, 1):
        for m in re.finditer(r'subgraph\s+(\w[\w.-]*)', block):
            name = m.group(1)
            if name.lower() in ('tb','bt','lr','rl','td','flowchart','graph'):
                continue
            pos = m.end()
            if pos < len(block) and block[pos] != '"':
                errors.append(f"Mermaid 块 #{i}: subgraph '{name}' 缺少引号")

        if re.search(r'\w+\s*&\s*\w+\s*--[-=>]', block):
            errors.append(f"Mermaid 块 #{i}: 使用了并行边语法 '&'")

        if re.search(r'^\s*mindmap\b', block, re.MULTILINE):
            errors.append(f"Mermaid 块 #{i}: 包含禁用的 mindmap 语法")

        for char, suggestion in MERMAID_FORBIDDEN_CHARS.items():
            if char in block:
                errors.append(f"Mermaid 块 #{i}: 包含禁止字符 '{char}'，{suggestion}")

    # ── 4. CSS 样式完整性检查 ──
    style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    if not style_match:
        errors.append("未找到 <style> 块，样式可能丢失")
    else:
        css_text = style_match.group(1)
        defined_classes = extract_css_classes(css_text)
        used_classes = extract_html_classes(content)

        missing = []
        for cls, component in REQUIRED_CSS_CLASSES.items():
            if cls in used_classes and cls not in defined_classes:
                missing.append(f"  - .{cls}（{component}）")

        if missing:
            errors.append("CSS 样式缺失 — 以下 class 在 HTML 中使用但 <style> 中无定义：")
            errors.extend(missing)

        style_len = len(css_text)
        if style_len < 5000:
            errors.append(f"<style> 块过短（{style_len} 字符），可能被截断（正常应 > 10000 字符）")

    return errors


def e2e_check(path, port=8899):
    """启动 HTTP 服务，验证 HTML 能否正常被浏览器加载。"""
    from urllib.parse import quote
    out_dir = os.path.dirname(os.path.abspath(path))
    file_name = os.path.basename(path)

    url = f"http://localhost:{port}/{quote(file_name)}"

    orig_cwd = os.getcwd()
    os.chdir(out_dir)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    os.chdir(orig_cwd)

    try:
        print(f"  [SERV] HTTP 服务: http://localhost:{port}")
        print(f"  [OPEN] 笔记: {url}")

        resp = urllib.request.urlopen(url, timeout=5)
        html = resp.read().decode('utf-8')

        if len(html) < 1000:
            print(f"  [WARN] 页面内容异常过短（{len(html)} 字符）")
        else:
            print(f"  [OK]   页面加载成功（{len(html)} 字符）")

        # 检查页面中是否有明显的错误关键词（排除 script 标签内的代码）
        html_no_script = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        ERROR_KEYWORDS = ['图表渲染失败', '渲染失败', '报错']
        for kw in ERROR_KEYWORDS:
            if kw in html_no_script:
                print(f"  [WARN] 页面包含错误提示: '{kw}'")

        struct_checks = [
            ('header', 'note-header'),
            ('tab导航', 'tab-nav'),
            ('文字内容', 'tab-text'),
            ('图解容器', 'diagram-tab'),
            ('Mermaid', 'mermaid.min.js'),
        ]
        for name, keyword in struct_checks:
            if keyword in html:
                print(f"  [OK]   {name} 存在")
            else:
                print(f"  [WARN] {name} 未找到 ('{keyword}')")

    except Exception as e:
        print(f"  [FAIL] HTTP 请求失败: {e}")
    finally:
        httpd.shutdown()
        print(f"  🌐 HTTP 服务已关闭")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/validate.py <html_文件路径>        # 静态校验")
        print("  python scripts/validate.py --e2e <html_文件路径>  # 静态+E2E校验")
        sys.exit(1)

    e2e_mode = False
    path_arg = None
    for arg in sys.argv[1:]:
        if arg == '--e2e':
            e2e_mode = True
        else:
            path_arg = arg

    if not path_arg:
        print("错误: 未提供文件路径")
        sys.exit(1)

    if not os.path.exists(path_arg):
        print(f"文件不存在: {path_arg}")
        sys.exit(1)

    print(f"校验文件: {os.path.basename(path_arg)}")
    print()
    errors = check_file(path_arg)
    if errors:
        print("[WARNING] 校验发现问题：")
        for e in errors:
            print(f"  - {e}")
        has_errors = True
    else:
        print("[OK] 静态校验通过，无异常")
        has_errors = False

    if e2e_mode:
        print()
        print("═══ E2E 校验 ═══")
        e2e_check(path_arg)

    if has_errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
