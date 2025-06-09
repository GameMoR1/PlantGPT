from pathlib import Path

HOME_DIR = Path.home()
APP_DIR = HOME_DIR / "PlantGPT"
DB_DIR = APP_DIR / "DB"
IMAGES_DIR = APP_DIR / "Images"
METHODOLOGIES_DIR = APP_DIR / "Methodologies"
PLANTUML_DIR = APP_DIR / "PlantUML"
PLANTUML_JAR_PATH = PLANTUML_DIR / "plantuml.jar"
CONFIG_FILE = APP_DIR / "config.json"
DB_PATH = DB_DIR / "plantuml_schemes.db"

PLANTUML_DOWNLOAD_URL = "https://github.com/plantuml/plantuml/releases/download/v1.2025.3/plantuml-1.2025.3.jar"

def ensure_dirs():
    for d in [APP_DIR, DB_DIR, IMAGES_DIR, METHODOLOGIES_DIR, PLANTUML_DIR]:
        d.mkdir(parents=True, exist_ok=True)
