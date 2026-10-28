"""Build the GitHub chapter pages from the continuous reader edition."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/新人保护指南-完整阅读版.md'
BOOK = ROOT / 'book'


def safe_title(title: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '', title).strip()


def markdown_target(path: str) -> str:
    """Encode characters that break GitHub's inline Markdown destinations."""
    return path.replace('%', '%25').replace(' ', '%20').replace('(', '%28').replace(')', '%29')


def render() -> dict[str, str]:
    source = SOURCE.read_text(encoding='utf-8')
    start = source.index('## 开篇：')
    section_pattern = re.compile(r'(?m)^<a id="(chapter-\d+|appendix-[a-k])"></a>\s*\n')
    boundaries = list(section_pattern.finditer(source, start))
    assert len(boundaries) == 25, '需要 14 章和 11 个附录'

    pieces: list[tuple[str, str, str]] = [('intro', '00-阅读入口.md', source[start:boundaries[0].start()])]
    for i, match in enumerate(boundaries):
        end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(source)
        body = source[match.start():end]
        heading = re.search(r'(?m)^## (.+)$', body)
        assert heading, match.group(1)
        anchor = match.group(1)
        if anchor.startswith('chapter-'):
            number = int(anchor.split('-')[1])
            title = re.sub(r'^第 \d+ 章 ', '', heading.group(1))
            filename = f'{number:02d}-{safe_title(title)}.md'
        else:
            letter = anchor[-1].upper()
            title = re.sub(r'^[A-K]\. ', '', heading.group(1))
            filename = f'附录-{letter}-{safe_title(title)}.md'
        if anchor == 'chapter-14':
            body = re.sub(r'\n---\n\n## 附录\n\s*$', '\n', body)
        pieces.append((anchor, filename, body))

    anchor_files = {'guide-toc': '../README.md'}
    for _, filename, body in pieces:
        for anchor in re.findall(r'<a id="([^"]+)"', body):
            assert anchor not in anchor_files, f'重复锚点: {anchor}'
            anchor_files[anchor] = filename

    output = {}
    for page_index, (_, filename, body) in enumerate(pieces):
        def link_target(match: re.Match[str]) -> str:
            anchor = match.group(1)
            assert anchor in anchor_files, f'找不到锚点: {anchor}'
            target = anchor_files[anchor]
            return f'](#{anchor})' if target == filename else f']({markdown_target(target)}#{anchor})'

        body = re.sub(r'\]\(#([^)]+)\)', link_target, body)
        page_links = ['[项目首页](../README.md)', '[连续阅读版](../docs/新人保护指南-完整阅读版.md)']
        if page_index > 0:
            page_links.append(f'[← 上一页]({markdown_target(pieces[page_index - 1][1])})')
        if page_index + 1 < len(pieces):
            page_links.append(f'[下一页 →]({markdown_target(pieces[page_index + 1][1])})')
        nav = ' · '.join(page_links)
        output[filename] = f'> 第 {page_index + 1} / {len(pieces)} 页 · {nav}\n\n{body.strip()}\n\n---\n\n{nav}\n'
    return output


def main() -> None:
    expected = render()
    if '--check' in sys.argv:
        actual_names = {p.name for p in BOOK.glob('*.md')}
        assert actual_names == set(expected), f'章节文件不一致：缺少 {set(expected) - actual_names}，多出 {actual_names - set(expected)}'
        for name, content in expected.items():
            assert (BOOK / name).read_text(encoding='utf-8') == content, f'章节未同步: {name}'
        print(f'{len(expected)} 个分章文件与连续阅读版一致')
        return

    BOOK.mkdir(parents=True, exist_ok=True)
    for old in BOOK.glob('*.md'):
        old.unlink()
    for name, content in expected.items():
        (BOOK / name).write_text(content, encoding='utf-8')
    print(f'已生成 {len(expected)} 个分章文件')


if __name__ == '__main__':
    main()
