# -*- coding: utf-8 -*-
"""
Data Flow 섹션 추출 스크립트
docs/_architecture 내 모든 문서에서 ### Data Flow 섹션을 추출하여 통합 문서 생성
"""
import os
import re
from pathlib import Path

def main():
    base_dir = Path(__file__).parent
    output_lines = []

    output_lines.append('# Data Flow 통합 문서')
    output_lines.append('')
    output_lines.append('> **생성일**: 2026-01-16')
    output_lines.append('> ')
    output_lines.append('> `docs/_architecture` 내 모든 문서의 `### Data Flow` 섹션을 통합한 문서입니다.')
    output_lines.append('')
    output_lines.append('---')
    output_lines.append('')
    output_lines.append('## 목차')
    output_lines.append('')

    # Find all md files with Data Flow sections
    dataflow_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '### Data Flow' in content:
                            rel_path = filepath.relative_to(base_dir)
                            dataflow_files.append((str(rel_path).replace('\\', '/'), filepath, content))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    pass

    # Sort by path
    dataflow_files.sort(key=lambda x: x[0])

    # Group by directory
    sections = []
    for rel_path, filepath, content in dataflow_files:
        parts = rel_path.split('/')
        if len(parts) > 1:
            dir_name = '/'.join(parts[:-1])
        else:
            dir_name = 'root'
        
        # Get title
        lines = content.split('\n')
        title = ''
        for line in lines:
            if line.startswith('# ') and not line.startswith('##'):
                title = line[2:].strip()
                break
        if not title:
            title = Path(filepath).stem
        
        # Extract Data Flow section
        dataflow_match = re.search(r'### Data Flow\s*\n(.*?)(?=\n---\s*\n|\n## |\n### [^D]|$)', content, re.DOTALL)
        if dataflow_match:
            dataflow_content = dataflow_match.group(1).strip()
            sections.append({
                'dir': dir_name,
                'rel_path': rel_path,
                'title': title,
                'content': dataflow_content
            })

    # Build TOC
    current_dir = ''
    toc_count = 1
    for sec in sections:
        if sec['dir'] != current_dir:
            current_dir = sec['dir']
            output_lines.append(f"- **{current_dir}/**")
        output_lines.append(f"  - [{sec['title']}](#{toc_count})")
        toc_count += 1

    output_lines.append('')
    output_lines.append('---')
    output_lines.append('')

    # Add sections
    current_dir = ''
    section_num = 1
    for sec in sections:
        if sec['dir'] != current_dir:
            current_dir = sec['dir']
            output_lines.append(f"## 📁 {current_dir}/")
            output_lines.append('')
        
        output_lines.append(f"### {section_num}. {sec['title']}")
        output_lines.append(f"> 📄 `docs/_architecture/{sec['rel_path']}`")
        output_lines.append('')
        output_lines.append(sec['content'])
        output_lines.append('')
        output_lines.append('---')
        output_lines.append('')
        section_num += 1

    # Write output
    output_path = base_dir / 'Full_DataFlow.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f'Created: {output_path}')
    print(f'Total sections: {len(sections)}')

if __name__ == '__main__':
    main()
