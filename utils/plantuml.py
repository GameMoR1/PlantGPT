import os
import re
import subprocess
import time

def extract_plantuml_code(text):
    code_blocks = re.findall(r"``````", text, re.DOTALL | re.IGNORECASE)
    if code_blocks:
        return code_blocks[0].strip()
    matches = re.findall(r"(@startuml.*?@enduml)", text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()
    return None

def generate_plantuml_diagram(plantuml_code, output_dir, filename, jar_path):
    temp_file = os.path.join(output_dir, f"{filename}.uml")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(plantuml_code.strip())
    time.sleep(0.1)
    cmd = [
        "java", "-jar", jar_path, "-charset", "UTF-8", "-stdrpt:1", temp_file
    ]
    result = subprocess.run(cmd, cwd=output_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"PlantUML error:\n{result.stderr.strip()}")
    png_path = os.path.splitext(temp_file)[0] + ".png"
    for _ in range(20):
        if os.path.exists(png_path):
            break
        time.sleep(0.1)
    if not os.path.exists(png_path):
        raise FileNotFoundError("Файл схемы не найден после генерации.")
    return png_path
