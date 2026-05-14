import os
import re
import json

def md_to_notion_blocks(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    blocks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Headings
        if line.startswith('# '):
            blocks.append({"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith('## '):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith('### '):
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
        # Bullet points
        elif line.startswith('- ') or line.startswith('* '):
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        # Numbered list (simple)
        elif re.match(r'^\d+\.', line):
            blocks.append({"type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": re.sub(r'^\d+\.\s*', '', line)}}]}})
        # Tables (Simplified - as code block for now if complex, or text)
        elif line.startswith('|'):
            blocks.append({"type": "code", "code": {"language": "markdown", "rich_text": [{"type": "text", "text": {"content": line}}]}})
        # Standard paragraph
        else:
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})
    
    return blocks

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python md_to_notion_blocks.py <file_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    if os.path.exists(path):
        blocks = md_to_notion_blocks(path)
        # Notion API limit: 100 blocks per request. For now we assume files are small enough.
        print(json.dumps(blocks[:100], ensure_ascii=False))
