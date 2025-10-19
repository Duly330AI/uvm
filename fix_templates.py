#!/usr/bin/env python3
"""
Fix Django template syntax errors - split template tags onto separate lines
"""
import re
from pathlib import Path

def fix_template(file_path):
    """Fix template tag line breaks in a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix pattern: {% ... %} {% ... %} on same line
    # Split into separate lines
    patterns = [
        # {% extends "..." %} {% block ... %}
        (r'({%\s*extends\s+[^%]+%})\s*({%\s*block\s+)', r'\1\n\n\2'),
        
        # {% endblock %} {% block ... %}
        (r'({%\s*endblock\s*%})\s*({%\s*block\s+)', r'\1\n\n\2'),
        
        # {% endif %} {% else %}
        (r'({%\s*endif\s*%})\s*({%\s*else\s*%})', r'\1\n\2'),
        
        # {% endfor %} {% endif %}
        (r'({%\s*endfor\s*%})\s*({%\s*endif\s*%})', r'\1\n\2'),
        
        # %} {% on same line (generic)
        (r'(%})\s*({%\s*(?:if|for|block|else|elif|endif|endfor|endblock))', r'\1\n\2'),
        
        # Fix line breaks INSIDE tags: {% if ... \n %}
        (r'{%\s*if\s+([^%]+?)\s*\n\s*%}', lambda m: '{% if ' + m.group(1).replace('\n', ' ').strip() + ' %}'),
        (r'{%\s*elif\s+([^%]+?)\s*\n\s*%}', lambda m: '{% elif ' + m.group(1).replace('\n', ' ').strip() + ' %}'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    templates_dir = Path('backend/app/templates')
    
    if not templates_dir.exists():
        print(f"❌ Directory not found: {templates_dir}")
        return
    
    fixed_count = 0
    for template_file in templates_dir.rglob('*.html'):
        if fix_template(template_file):
            print(f"✅ Fixed: {template_file}")
            fixed_count += 1
    
    print(f"\n🎉 Fixed {fixed_count} template files!")

if __name__ == '__main__':
    main()
