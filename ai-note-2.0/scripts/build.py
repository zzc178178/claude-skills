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
import urllib.request
import urllib.error
import socket


def find_template():
    """查找模板文件"""
    # 1. skill 目录（开发环境）
    skill_path = os.path.join(
        os.path.expanduser('~'),
        '.claude', 'skills', 'ai-note-2.0', 'ai-note-2.0', 'assets', 'template.html'
    )
    if os.path.exists(skill_path):
        return skill_path

    # 2. 项目 scripts 同级的 assets 目录
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'template.html')
    if os.path.exists(local_path):
        return os.path.abspath(local_path)

    # 3. 当前目录
    cwd_path = os.path.join(os.getcwd(), 'template.html')
    if os.path.exists(cwd_path):
        return os.path.abspath(cwd_path)

    print(f"[FAIL] 未找到模板文件")
    print(f"  预期位置: {skill_path}")
    sys.exit(1)


def _fix_multiline_strings(raw):
    """修复 JSON 字符串值中的真实换行符（逐字符扫描，100% 可靠）
    JSON 标准不允许字符串内包含真实换行符，需要替换为 \\n 转义序列。
    逐字符扫描，仅在字符串值内部将真实换行符替换为 \\n。
    """
    result = []
    in_string = False        # 当前是否在 JSON 字符串值内
    in_escape = False        # 当前是否在转义序列内（\\...）
    quote_at = 0             # 上一个未闭合双引号的位置（用于跳过 key 的引号）

    for i, ch in enumerate(raw):
        if in_escape:
            # 转义序列内的字符原样保留
            result.append(ch)
            in_escape = False
            continue

        if ch == '\\':
            # 转义序列开始
            result.append(ch)
            in_escape = True
            continue

        if ch == '"':
            if in_string:
                # 结束当前字符串值
                in_string = False
            else:
                # 开始新字符串值
                in_string = True
            result.append(ch)
            continue

        if in_string and ch == '\n':
            # 字符串值内部的真实换行符 → 替换为 \\n
            result.append('\\n')
            continue

        result.append(ch)

    return ''.join(result)


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

    # 3. 自动修复：合并多行字符串值（JSON 标准不允许字符串内包含真实换行符）
    if 'control character' in _exc.msg:
        print(f"[FIX] 检测到多行字符串（字符串值内含真实换行符），尝试合并...")
        try:
            fixed = _fix_multiline_strings(raw)
            raw = fixed
            # 用修复后的内容重试解析
            data = json.loads(raw)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[FIX] 多行字符串合并成功，已更新 JSON 文件")
            return data
        except json.JSONDecodeError as e3:
            print(f"  [WARN] 多行合并后仍解析失败: {e3.msg}，继续后续修复...")
            # Fall through to step 4 with original raw
            lines = raw.split('\n')
    else:
        fixed = raw

    # 4. 自动修复：将 HTML 属性中的双引号替换为单引号
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


SITE_DISPLAY = {
    'mp.weixin.qq.com': '微信公众号',
    'weixin.qq.com':    '微信公众号',
    'zhuanlan.zhihu.com': '知乎专栏',
    'zhihu.com':        '知乎',
    'juejin.cn':        '掘金',
    'oschina.net':      '开源中国',
    'csdn.net':         'CSDN',
    '36kr.com':         '36氪',
    'huxiu.com':        '虎嗅',
    'sspai.com':        '少数派',
    'infoq.cn':         'InfoQ',
    'geekbang.org':     '极客邦',
}

def _site_name(url):
    """从 URL 提取可读的站点名称"""
    for domain, name in SITE_DISPLAY.items():
        if domain in url:
            return name
    m = re.search(r'https?://([^/]+)', url)
    if m:
        return m.group(1).replace('www.', '')
    return '原文链接'


def _fetch_author_wechat(url, timeout=5):
    """尝试从微信公众号文章页提取公众号名称
    返回公众号名称，失败返回 None。
    """
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return None

    # WeChat 公众号名称的几种可能位置
    patterns = [
        r'var\s+nickname\s*=\s*"([^"]+)"',           # 内联 JS 变量
        r'var\s+appmsg_ext\s*=\s*\{[^}]*?"author_name"\s*:\s*"([^"]+)"',  # appmsg_ext
        r'weui_media_extra_info[^>]*>([^<]+)',         # 页面底部公众号名片
        r'class="profile_nickname">([^<]+)',             # 新版公众号名
        r'property="og:article:author"[^>]*content="([^"]+)"',  # og meta
        r'class="rich_media_meta_nickname"[^>]*>([^<]+)',      # 文章头部公众号名
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            name = m.group(1).strip()
            if name and len(name) < 50:
                return name
    return None


def _wrap_source_url(url):
    """将裸 URL 包装为 note-source 格式，尝试抓取公众号名称充实链接文字"""
    site = None
    if 'mp.weixin.qq.com' in url:
        print(f"  [INFO] 尝试抓取公众号名称...")
        site = _fetch_author_wechat(url)
        if site:
            print(f"  [INFO] 识别到公众号: {site}")
        else:
            print(f"  [INFO] 未识别到公众号名，使用默认名称")

    name = site or _site_name(url)
    return (
        f"<div class='note-source'>"
        f"<span class='source-label'>原文来源</span>"
        f"<a class='source-link' href='{url}' target='_blank'>{name}</a>"
        f"</div>"
    )


def enrich_source(source):
    """验充实化 source 字段：裸 URL → 完整 HTML 格式"""
    if not source:
        return source
    # 已经是完整格式
    if 'note-source' in source and 'source-link' in source:
        return source
    # 裸 URL
    if source.startswith('http://') or source.startswith('https://'):
        print(f"  [FIX] source 为裸 URL，自动充实...")
        return _wrap_source_url(source)
    # 其他形式，直接包装
    print(f"  [WARN] source 格式不符合要求，自动包装")
    return _wrap_source_url(source)


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

    # 验证 source 字段；裸 URL 会自动充实为完整 HTML 格式
    data['source'] = enrich_source(data.get('source', ''))

    # 验证必要字段
    required = ['title', 'tag', 'subtitle', 'source', 'text_content', 'diagram_content']
    for key in required:
        if key not in data:
            raise ValueError(f"[FAIL] 缺少必要字段: {key}")

    # 校验 source 格式（允许空字符串，仅非空时校验）
    source = data['source']
    if source and ('note-source' not in source or 'source-link' not in source):
        print(f"  [WARN] source 字段缺少标准 HTML 包装，尝试自动包装...")
        data['source'] = _wrap_source_url(source)

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
