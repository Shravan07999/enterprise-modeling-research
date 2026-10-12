import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from exporters.adl_exporter import generate_adl

sample_output = '''Here is the enterprise model:

```json
[
  {"id": "1", "label": "Goal: Reduce Churn", "type": "Goal", "next": ["2"]},
  {"id": "2", "label": "Process: Handle Tickets", "type": "Process", "next": ["3", "4"]},
  {"id": "3", "label": "Data: Ticket DB", "type": "Data", "next": []},
  {"id": "4", "label": "Resource: Support Team", "type": "Resource", "next": []}
]
```
'''

content, err = generate_adl(
    stage1_blueprint="test blueprint",
    final_output=sample_output,
    framework_selected="4EM",
    model_name="test_model",
)

if err:
    print(f"TEST 1 ERROR: {err}")
else:
    print(f"TEST 1 SUCCESS: generated {len(content)} chars")

sample_no_json = """Here is a narrative about the enterprise model.
Goals include reducing churn and improving satisfaction.
Processes include ticket handling and customer support.
"""

content2, err2 = generate_adl(
    stage1_blueprint="test",
    final_output=sample_no_json,
    framework_selected="4EM",
    model_name="test_model",
)

if err2:
    print(f"\nTEST 2 ERROR (expected): {err2}")
else:
    print(f"\nTEST 2 SUCCESS: generated {len(content2)} chars")

if content:
    with open("test_adl_output.adl", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\nFull ADL output written to test_adl_output.adl")

print("\n--- Structure validation ---")
lines = content.split("\n")
print(f"Total lines: {len(lines)}")

instance_count = sum(1 for l in lines if l.strip().startswith("INSTANCE"))
relation_count = sum(1 for l in lines if l.strip().startswith("RELATION"))
end_count = sum(1 for l in lines if l.strip() == "//END")
attr_count = sum(1 for l in lines if l.strip().startswith("ATTRIBUTE"))
value_count = sum(1 for l in lines if l.strip().startswith("VALUE"))

print(f"INSTANCE blocks: {instance_count}")
print(f"RELATION blocks: {relation_count}")
print(f"//END markers: {end_count}")
print(f"ATTRIBUTE entries: {attr_count}")
print(f"VALUE entries: {value_count}")
print(f"Expected //END markers: {instance_count + relation_count}")

if end_count != instance_count + relation_count:
    print("WARNING: //END count mismatch!")

print("\n--- INSTANCE block structure check ---")
in_instance = False
current_attrs = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("INSTANCE"):
        in_instance = True
        current_attrs = []
        inst_name = stripped
    elif stripped == "//END" and in_instance:
        in_instance = False
        print(f"  {inst_name}")
        print(f"    Attributes: {current_attrs}")
    elif stripped.startswith("ATTRIBUTE") and in_instance:
        attr_name = stripped.replace("ATTRIBUTE ", "")
        current_attrs.append(attr_name)

print("\n--- RELATION block structure check ---")
in_relation = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("RELATION"):
        in_relation = True
        rel_line = i + 1
        print(f"  Line {rel_line}: {stripped}")
    elif stripped.startswith("FROM") and in_relation:
        print(f"    {stripped}")
    elif stripped.startswith("TO") and in_relation:
        print(f"    {stripped}")
    elif stripped == "//END" and in_relation:
        in_relation = False
