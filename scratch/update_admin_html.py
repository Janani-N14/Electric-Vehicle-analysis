import re

html_path = "templates/admin-dashboard.html"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add id="stat-total" to the 48 count
content = content.replace(
    '<div class="stat-value blue">48</div>',
    '<div class="stat-value blue" id="stat-total">48</div>'
)

# 2. Add id="stat-idle" to the 9 count
content = content.replace(
    '<div class="stat-value orange">9</div>',
    '<div class="stat-value orange" id="stat-idle">9</div>'
)

# 3. Update + Add Vehicle button onclick
old_button = 'onclick="showModal(\'Add Vehicle\',\'Vehicle registration form would open here.\\nFill VIN, model, plate, assigned driver.\')"'
new_button = 'onclick="openAddVehicleModal()"'
content = content.replace(old_button, new_button)

# 4. Replace script block (everything between the last <script> and </script>)
# Find the start of the final script block
script_matches = list(re.finditer(r'<script>', content))
if script_matches:
    last_script_start = script_matches[-1].start()
    # Find the matching </script> tag after it
    end_match = re.search(r'</script>', content[last_script_start:])
    if end_match:
        last_script_end = last_script_start + end_match.end()
        # Replace the entire block
        content = content[:last_script_start] + '<script src="/static/admin-dashboard.js"></script>' + content[last_script_end:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("HTML modified successfully!")
