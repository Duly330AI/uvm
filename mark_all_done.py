import re

# Read the file
with open(r'c:\noc_project\UNOC\uvm\docs\Portal_Properties_Implementation_TODO.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Track which phase we're in
lines = content.split('\n')
result = []
current_phase = None
in_completed_phase = False
changes_made = 0

for line in lines:
    # Detect phase headers - both COMPLETED and SKIPPED count as done
    if line.startswith('## ✅ PHASE'):
        # Extract phase number
        match = re.search(r'PHASE (\d+)', line)
        if match:
            phase_num = int(match.group(1))
            # All phases with ✅ are considered complete (COMPLETED or SKIPPED)
            in_completed_phase = True
            current_phase = phase_num
            print(f"Found Phase {phase_num}: COMPLETED/SKIPPED")
    elif line.startswith('## PHASE') and not line.startswith('## ✅'):
        # Not completed phase (no ✅ checkmark)
        in_completed_phase = False
        current_phase = None
        print("Found incomplete phase")

    # Replace [ ] with [x] in completed phases
    if in_completed_phase and '- [ ]' in line:
        line = line.replace('- [ ]', '- [x]', 1)
        changes_made += 1

    result.append(line)

# Write back
with open(r'c:\noc_project\UNOC\uvm\docs\Portal_Properties_Implementation_TODO.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

print(f"\n✅ Done! {changes_made} checkboxes marked as [x] in completed phases!")
