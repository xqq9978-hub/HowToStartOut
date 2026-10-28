"""Check local Markdown links, anchors, Skill files and guide completeness."""

from pathlib import Path
import hashlib
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/newcomer-protection-assistant/SKILL.md'
V6 = ROOT / 'skills/newcomer-protection-assistant/references/新人保护指南-V6.md'
GUIDE = ROOT / 'docs/新人保护指南-完整阅读版.md'
ORIGINAL_V6_SHA256 = '2f7741de51c53f9975638ce5fd393ff835b195054a01cf5dd017cd31751eb283'


def anchors(path: Path) -> set[str]:
    return set(re.findall(r'<a id="([^"]+)"', path.read_text(encoding='utf-8')))


def check_links(path: Path) -> list[str]:
    content = path.read_text(encoding='utf-8')
    failures = []
    for target in re.findall(r'!?(?:\[[^\]]*\])\(([^)]+)\)', content):
        if target.startswith(('https://', 'http://', 'mailto:', 'tel:')):
            continue
        if any(char.isspace() for char in target):
            failures.append(f'{path.relative_to(ROOT)} → 链接地址含未编码空格 {target}')
        file_part, _, fragment = target.partition('#')
        destination = (path.parent / unquote(file_part)).resolve() if file_part else path
        if not destination.exists():
            failures.append(f'{path.relative_to(ROOT)} → 缺少 {target}')
        elif fragment and destination.is_file() and fragment not in anchors(destination):
            failures.append(f'{path.relative_to(ROOT)} → 缺少锚点 {target}')
    return failures


def main() -> None:
    required = [ROOT / 'README.md', GUIDE, SKILL, V6, ROOT / 'assets/cover.png', ROOT / 'index.html', *(ROOT / 'assets' / f'button-{name}.svg' for name in ('online', 'chapters', 'offline'))]
    assert all(p.is_file() for p in required), '核心文件不完整'
    assert hashlib.sha256(V6.read_bytes()).hexdigest() == ORIGINAL_V6_SHA256, 'V6 知识库与用户提供的原版不一致'
    guide = GUIDE.read_text(encoding='utf-8')
    assert len(re.findall(r'(?m)^## 第 \d+ 章 ', guide)) == 14
    assert len(re.findall(r'(?m)^## [A-K]\. ', guide)) == 11
    assert '<a id="item-9-18"></a>' in guide
    assert len(list((ROOT / 'book').glob('*.md'))) == 26
    for index, page in enumerate(sorted((ROOT / 'book').glob('*.md')), 1):
        assert page.read_text(encoding='utf-8').startswith(f'> 第 {index} / 26 页 · '), f'分章翻页顺序错误: {page.name}'
    skill = SKILL.read_text(encoding='utf-8')
    assert skill.startswith('---\nname: newcomer-protection-assistant\n')
    assert all(mode in skill for mode in ('INIT', 'CHECK', 'HELP', 'PLAN'))
    markdown = [ROOT / 'README.md', GUIDE, SKILL, V6, *sorted((ROOT / 'book').glob('*.md'))]
    errors = [error for p in markdown for error in check_links(p)]
    assert not errors, '\n'.join(errors[:30])
    print(f'核对通过：14 章、附录 A—K、26 个阅读页、{len(markdown)} 份 Markdown 的本地链接与锚点、Skill 与 V6 原版。')


if __name__ == '__main__':
    main()
