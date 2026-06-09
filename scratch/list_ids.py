import sys
# Force UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

with open("templates/admin-dashboard.html", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "id=" in line:
            parts = line.split("id=")
            for p in parts[1:]:
                # Extract the id string
                quote = p[0]
                val = p[1:].split(quote)[0]
                print(f"Line {i+1}: id={val} -> {line.strip()[:100]}")
