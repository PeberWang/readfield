"""
merge_lessons_simple.py — 最简拼接：原样拼各天正文，不改任何排版

用法：python merge_lessons_simple.py samples/castle
"""

import argparse, os, re, subprocess, sys

def split_tex(content: str):
    """返回 (preamble, title_block, body)
    
    title_block = title/author/date 三个命令（在 preamble 中 \\begin{document} 之前）
    body = \\begin{document} 到 \\end{document} 之间的内容
    """
    doc_begin = content.find(r'\begin{document}')
    doc_end = content.find(r'\end{document}')
    if doc_begin == -1:
        return None
    
    preamble = content[:doc_begin]
    
    # 提取 title/author/date 块（preamble 末尾部分）
    title_match = re.search(r'(\\title\{.+?\})\s*\n(\s*\\author\{.*?\}\s*\n)?(\s*\\date\{.*?\}\s*\n)?', preamble, re.DOTALL)
    title_block = title_match.group(0) if title_match else ''
    
    # 去除 preamble 中的 title/author/date（第一个 preamble 保留，其他的通过 title_block 注入 body）
    clean_preamble = preamble
    if title_match:
        clean_preamble = preamble[:title_match.start()] + preamble[title_match.end():]
    
    body_start = doc_begin + len(r'\begin{document}')
    if doc_end == -1:
        body = content[body_start:]
    else:
        body = content[body_start:doc_end]
    
    return clean_preamble, title_block.strip(), body.strip()


def find_day_dirs(base_dir: str):
    days = []
    for entry in os.listdir(base_dir):
        full = os.path.join(base_dir, entry)
        if os.path.isdir(full):
            m = re.match(r'^day-(\d+)$', entry)
            if m:
                days.append((int(m.group(1)), full))
    days.sort(key=lambda x: x[0])
    return days

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('base_dir', help='包含 day-XX 子目录的根目录')
    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    merged_dir = os.path.join(base_dir, 'merged')
    os.makedirs(merged_dir, exist_ok=True)

    days = find_day_dirs(base_dir)
    if not days:
        print('Error: 未找到 day-XX 目录', file=sys.stderr)
        sys.exit(1)

    # 读取各天
    clean_preamble = None
    segments = []
    for day_num, day_dir in days:
        tex_path = os.path.join(day_dir, '_lesson.tex')
        if not os.path.exists(tex_path):
            print(f'  Warning: {tex_path} 不存在，跳过')
            continue
        with open(tex_path, 'r', encoding='utf-8') as f:
            content = f.read()
        result = split_tex(content)
        if result is None:
            continue
        cp, title_block, body = result
        if clean_preamble is None:
            clean_preamble = cp
        segments.append((day_num, title_block, body))
        print(f'  day-{day_num:02d}: OK ({len(body)} chars body)')

    if clean_preamble is None:
        print('Error: 无可用 preamble', file=sys.stderr)
        sys.exit(1)

    # 拼接 — 每段前重新注入 title/author/date 再 maketitle
    lines = [clean_preamble.strip(), r'\begin{document}']
    for day_num, title_block, body in segments:
        lines.append(r'\newpage')
        # 注入该天的 title/author/date 定义
        lines.append(title_block)
        # 正文中第一个命令是 \maketitle，但 body 中已有 \maketitle
        # 直接放 body 即可（各天 body 开头必是 \maketitle）
        lines.append(body)
    lines.append(r'\end{document}')

    tex_content = '\n'.join(lines) + '\n'

    # 清理多余空行
    tex_content = re.sub(r'\n{4,}', '\n\n\n', tex_content)

    tex_path = os.path.join(merged_dir, 'merged_lessons.tex')
    with open(tex_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(tex_content)
    print(f'\n生成: {tex_path}')

    # 编译两遍
    xelatex = r'C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe'
    print('编译中...')
    for i in range(2):
        result = subprocess.run(
            [xelatex, '-interaction=nonstopmode', '-output-directory', merged_dir, tex_path],
            capture_output=True, text=True, timeout=120
        )
        err_lines = [l.strip() for l in result.stderr.split('\n') if '!' in l or 'Fatal' in l or 'Error' in l]
        if err_lines:
            for e in err_lines[:5]:
                print(f'  {e}')
        else:
            print(f'  第 {i+1} 遍编译完成')

    pdf_path = os.path.join(merged_dir, 'merged_lessons.pdf')
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f'\n成功: {pdf_path} ({size_kb:.1f} KB)')
    else:
        print('Error: PDF 未生成', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
