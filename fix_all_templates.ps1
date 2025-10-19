# Template Fixer - Fixes all Django template syntax errors
# Fixes line breaks inside and between template tags

$files = Get-ChildItem -Path backend\app\templates -Recurse -Filter *.html
$fixedCount = 0

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    if (-not $content) { continue }

    $original = $content

    # Fix 1: Split tags on same line: %} {% -> %}\n{%
    $content = $content -replace '(%})\s+({%\s*(?:block|if|for|endif|endfor|endblock|else|elif|empty))', "`$1`n`$2"

    # Fix 2: Remove line breaks INSIDE tags: {% ...\n... %}
    # This is tricky - we need to handle multi-line tags
    while ($content -match '({%[^%]*?)\n([^%]*?%})') {
        $content = $content -replace '({%[^%]*?)\n([^%]*?%})', '$1 $2'
    }

    # Fix 3: Ensure proper spacing in tags
    $content = $content -replace '{%\s+', '{% '
    $content = $content -replace '\s+%}', ' %}'

    if ($content -ne $original) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        Write-Host "✅ Fixed: $($file.Name)" -ForegroundColor Green
        $fixedCount++
    }
}

Write-Host "`n🎉 Fixed $fixedCount template files!" -ForegroundColor Cyan
