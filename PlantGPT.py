import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk  # Для Listbox и событий клавиатуры
from PIL import Image, ImageTk
import subprocess
import os
import re
import threading
import sqlite3
import json
import shutil
import time
from pathlib import Path
from io import BytesIO

from g4f import ChatCompletion  # pip install g4f

# Настройка темы CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")

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

class Database:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.create_table()

    def create_table(self):
        with self.lock:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS schemes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    code TEXT,
                    image_path TEXT,
                    image_data BLOB
                )
            ''')
            self.conn.commit()

    def add_scheme(self, filename, code, image_path):
        with self.lock:
            image_data = None
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
            except Exception:
                pass
            self.cursor.execute('''
                INSERT OR REPLACE INTO schemes (filename, code, image_path, image_data)
                VALUES (?, ?, ?, ?)
            ''', (filename, code, image_path, image_data))
            self.conn.commit()

    def get_all_schemes(self):
        with self.lock:
            self.cursor.execute('SELECT id, filename FROM schemes ORDER BY id DESC')
            return self.cursor.fetchall()

    def get_scheme_by_id(self, scheme_id):
        with self.lock:
            self.cursor.execute('SELECT filename, code, image_path, image_data FROM schemes WHERE id=?', (scheme_id,))
            return self.cursor.fetchone()

    def delete_scheme_by_id(self, scheme_id):
        with self.lock:
            self.cursor.execute('SELECT image_path FROM schemes WHERE id=?', (scheme_id,))
            row = self.cursor.fetchone()
            if row:
                image_path = row[0]
                try:
                    if image_path and os.path.isfile(image_path):
                        os.remove(image_path)
                except Exception:
                    pass
            self.cursor.execute('DELETE FROM schemes WHERE id=?', (scheme_id,))
            self.conn.commit()

    def close(self):
        with self.lock:
            self.conn.close()

def bind_ctrl_v(textbox):
    def paste_event(event):
        try:
            clipboard = textbox.clipboard_get()
            textbox.insert("insert", clipboard)
        except Exception:
            pass
        return "break"
    textbox.bind("<Control-v>", paste_event)
    textbox.bind("<Control-V>", paste_event)
    textbox.bind("<Shift-Insert>", paste_event)

class CodeViewer(ctk.CTkToplevel):
    def __init__(self, master, code):
        super().__init__(master)
        self.title("Код PlantUML")
        self.geometry("700x500")
        self.text = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.text.pack(fill="both", expand=True)
        self.text.insert("0.0", code)
        self.text.configure(state="normal")
        bind_ctrl_v(self.text)
        self.text.configure(state="disabled")

class MethodologyEditor(ctk.CTkToplevel):
    def __init__(self, master, methodologies_dir, refresh_callback):
        super().__init__(master)
        self.title("Добавить методологию")
        self.geometry("600x400")
        self.methodologies_dir = methodologies_dir
        self.refresh_callback = refresh_callback

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Название методологии (имя файла):").pack(anchor="w")
        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(frame, textvariable=self.name_var)
        self.name_entry.pack(fill="x", pady=5)

        ctk.CTkLabel(frame, text="Описание методологии:").pack(anchor="w")
        self.desc_text = ctk.CTkTextbox(frame, height=200)
        self.desc_text.pack(fill="both", expand=True, pady=5)
        bind_ctrl_v(self.desc_text)

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.save_methodology).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", command=self.destroy).pack(side="left", padx=5)

    def save_methodology(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введите название методологии")
            return
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").rstrip()
        if not safe_name:
            messagebox.showerror("Ошибка", "Название методологии содержит недопустимые символы")
            return
        desc = self.desc_text.get("0.0", "end").strip()
        if not desc:
            messagebox.showerror("Ошибка", "Введите описание методологии")
            return
        os.makedirs(self.methodologies_dir, exist_ok=True)
        file_path = os.path.join(self.methodologies_dir, safe_name + ".txt")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(desc)
            messagebox.showinfo("Успех", f"Методология '{safe_name}' сохранена")
            self.refresh_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

class MethodologyDeleteWindow(ctk.CTkToplevel):
    def __init__(self, master, methodologies_dir, refresh_callback):
        super().__init__(master)
        self.title("Удалить методологии")
        self.geometry("400x400")
        self.methodologies_dir = methodologies_dir
        self.refresh_callback = refresh_callback

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Выберите методологии для удаления:").pack(anchor="w")

        self.listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE)
        self.listbox.pack(fill="both", expand=True, pady=5)

        self.load_methodologies()

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Удалить выбранные", command=self.delete_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", command=self.destroy).pack(side="left", padx=5)

    def load_methodologies(self):
        self.listbox.delete(0, tk.END)
        try:
            files = [f for f in os.listdir(self.methodologies_dir) if f.endswith(".txt")]
        except Exception:
            files = []
        for f in files:
            self.listbox.insert(tk.END, f)

    def delete_selected(self):
        selected = list(self.listbox.curselection())
        if not selected:
            messagebox.showwarning("Внимание", "Выберите методологии для удаления.")
            return
        selected_files = [self.listbox.get(i) for i in selected]
        if messagebox.askyesno("Подтверждение", f"Удалить выбранные методологии?\n{', '.join(selected_files)}"):
            errors = []
            for f in selected_files:
                try:
                    os.remove(os.path.join(self.methodologies_dir, f))
                except Exception as e:
                    errors.append(f"{f}: {e}")
            if errors:
                messagebox.showerror("Ошибка", "Ошибки при удалении:\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Успех", "Выбранные методологии удалены.")
            self.refresh_callback()
            self.load_methodologies()

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, config_data, save_callback, methodologies_dir, load_methodologies_callback):
        super().__init__(master)
        self.title("Настройки")
        self.geometry("800x650")
        self.resizable(False, False)
        self.config_data = config_data
        self.save_callback = save_callback
        self.methodologies_dir = methodologies_dir
        self.load_methodologies_callback = load_methodologies_callback

        self.download_progress_var = ctk.StringVar(value="")

        frame = ctk.CTkFrame(self)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Jar path
        ctk.CTkLabel(frame, text="Путь к plantuml.jar:").grid(row=0, column=0, sticky="w")
        self.jar_path_var = ctk.StringVar(value=self.config_data.get("jar_path", str(PLANTUML_JAR_PATH)))
        self.jar_entry = ctk.CTkEntry(frame, textvariable=self.jar_path_var, width=400)
        self.jar_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Выбрать...", command=self.choose_jar).grid(row=0, column=2, padx=5)
        ctk.CTkButton(frame, text="Скачать plantuml.jar", command=self.download_plantuml).grid(row=0, column=3, padx=5)

        # Download progress label
        self.download_progress_label = ctk.CTkLabel(frame, textvariable=self.download_progress_var, text_color="blue")
        self.download_progress_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0,10))

        # Output dir
        ctk.CTkLabel(frame, text="Папка вывода:").grid(row=2, column=0, sticky="w", pady=10)
        self.dir_var = ctk.StringVar(value=self.config_data.get("output_dir", str(IMAGES_DIR)))
        self.dir_entry = ctk.CTkEntry(frame, textvariable=self.dir_var, width=400)
        self.dir_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(frame, text="Выбрать...", command=self.choose_dir).grid(row=2, column=2, padx=5, pady=10)

        # Improve prompt checkbox
        self.improve_prompt_var = ctk.BooleanVar(value=self.config_data.get("improve_prompt", False))
        self.improve_cb = ctk.CTkCheckBox(frame, text="Улучшить промт", variable=self.improve_prompt_var)
        self.improve_cb.grid(row=3, column=0, columnspan=4, sticky="w")

        # Max retries
        ctk.CTkLabel(frame, text="Макс. попыток генерации схемы:").grid(row=4, column=0, sticky="w", pady=10)
        self.max_retries_var = ctk.StringVar(value=str(self.config_data.get("max_retries", 5)))
        self.max_retries_entry = ctk.CTkEntry(frame, textvariable=self.max_retries_var, width=60)
        self.max_retries_entry.grid(row=4, column=1, sticky="w", padx=5, pady=10)

        # Prompt improvements inputs
        ctk.CTkLabel(frame, text="Промт для улучшения (часть 1):").grid(row=5, column=0, sticky="nw", pady=(20,5))
        self.prompt_improve_1 = ctk.CTkTextbox(frame, height=80)
        self.prompt_improve_1.grid(row=5, column=1, columnspan=3, sticky="ew", pady=(20,5), padx=(0,10))
        self.prompt_improve_1.insert("0.0", self.config_data.get("prompt_improve_1", ""))
        bind_ctrl_v(self.prompt_improve_1)

        ctk.CTkLabel(frame, text="Промт для улучшения (часть 2):").grid(row=6, column=0, sticky="nw", pady=5)
        self.prompt_improve_2 = ctk.CTkTextbox(frame, height=80)
        self.prompt_improve_2.grid(row=6, column=1, columnspan=3, sticky="ew", pady=5, padx=(0,10))
        self.prompt_improve_2.insert("0.0", self.config_data.get("prompt_improve_2", ""))
        bind_ctrl_v(self.prompt_improve_2)

        # Buttons for methodology management and folder cleaning
        btn_meth_frame = ctk.CTkFrame(frame)
        btn_meth_frame.grid(row=7, column=0, columnspan=4, pady=10, sticky="ew")
        ctk.CTkButton(btn_meth_frame, text="Добавить методологию", command=self.open_methodology_editor).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Удалить методологии", command=self.open_methodology_delete).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Очистить папку с изображениями", command=self.clear_images).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Сбросить настройки", command=self.reset_settings).pack(side="left", padx=10)

        # Save/Cancel buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=8, column=0, columnspan=4, pady=20)
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Отмена", command=self.destroy).pack(side="left", padx=10)

        frame.columnconfigure(1, weight=1)

    def choose_jar(self):
        path = filedialog.askopenfilename(title="Выберите plantuml.jar", filetypes=[("JAR files", "*.jar")])
        if path:
            self.jar_path_var.set(path)
            self.config_data["jar_path"] = path
            self.save_callback(self.config_data)

    def choose_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dir_var.set(folder)
            self.config_data["output_dir"] = folder
            self.save_callback(self.config_data)

    def open_methodology_editor(self):
        MethodologyEditor(self, self.methodologies_dir, self.load_methodologies_callback)

    def open_methodology_delete(self):
        MethodologyDeleteWindow(self, self.methodologies_dir, self.load_methodologies_callback)

    def clear_images(self):
        if messagebox.askyesno("Подтверждение", "Очистить папку с изображениями? Все файлы будут удалены."):
            try:
                for f in os.listdir(IMAGES_DIR):
                    file_path = os.path.join(IMAGES_DIR, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                messagebox.showinfo("Успех", "Папка с изображениями очищена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось очистить папку: {e}")

    def download_plantuml(self):
        try:
            for f in os.listdir(PLANTUML_DIR):
                file_path = os.path.join(PLANTUML_DIR, f)
                try:
                    if os.path.isfile(file_path) and file_path.endswith(".jar"):
                        os.remove(file_path)
                except Exception:
                    pass

            save_path = PLANTUML_JAR_PATH
            self.download_progress_var.set("0%")

            def reporthook(blocknum, blocksize, totalsize):
                if totalsize > 0:
                    percent = int(blocknum * blocksize * 100 / totalsize)
                    if percent > 100:
                        percent = 100
                    self.download_progress_var.set(f"Скачивание plantuml.jar: {percent}%")
                else:
                    self.download_progress_var.set(f"Скачивание plantuml.jar...")

            def download():
                try:
                    import urllib.request
                    urllib.request.urlretrieve(PLANTUML_DOWNLOAD_URL, save_path, reporthook)
                    self.jar_path_var.set(str(save_path))
                    self.config_data["jar_path"] = str(save_path)
                    self.save_callback(self.config_data)
                    self.download_progress_var.set("Скачивание завершено")
                    messagebox.showinfo("Успех", "plantuml.jar успешно скачан")
                except Exception as e:
                    self.download_progress_var.set("")
                    messagebox.showerror("Ошибка", f"Не удалось скачать plantuml.jar: {e}")
                finally:
                    self.after(1000, lambda: self.download_progress_var.set(""))

            threading.Thread(target=download, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при скачивании: {e}")
            self.download_progress_var.set("")

    def reset_settings(self):
        default_config = {
            "jar_path": str(PLANTUML_JAR_PATH),
            "output_dir": str(IMAGES_DIR),
            "improve_prompt": False,
            "max_retries": 5,
            "prompt_improve_1": "",
            "prompt_improve_2": ""
        }
        self.config_data.clear()
        self.config_data.update(default_config)
        self.save_callback(self.config_data)

        self.jar_path_var.set(self.config_data["jar_path"])
        self.dir_var.set(self.config_data["output_dir"])
        self.improve_prompt_var.set(self.config_data["improve_prompt"])
        self.max_retries_var.set(str(self.config_data["max_retries"]))
        self.prompt_improve_1.delete("0.0", "end")
        self.prompt_improve_1.insert("0.0", self.config_data["prompt_improve_1"])
        self.prompt_improve_2.delete("0.0", "end")
        self.prompt_improve_2.insert("0.0", self.config_data["prompt_improve_2"])

        messagebox.showinfo("Успех", "Настройки сброшены к значениям по умолчанию.")

    def on_save(self):
        self.config_data["jar_path"] = self.jar_path_var.get()
        self.config_data["output_dir"] = self.dir_var.get()
        self.config_data["improve_prompt"] = self.improve_prompt_var.get()
        try:
            self.config_data["max_retries"] = int(self.max_retries_var.get())
        except Exception:
            self.config_data["max_retries"] = 5
        self.config_data["prompt_improve_1"] = self.prompt_improve_1.get("0.0", "end").strip()
        self.config_data["prompt_improve_2"] = self.prompt_improve_2.get("0.0", "end").strip()
        self.save_callback(self.config_data)
        self.destroy()

class PlantUMLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PlantGPT")
        self.geometry("1200x820")

        ensure_dirs()

        self.db = Database()
        self.config_data = load_config()

        self.failed_attempts = 0

        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(top_frame, text="Имя файла схемы (без расширения):").pack(side="left")
        self.filename_var = ctk.StringVar()
        self.filename_entry = ctk.CTkEntry(top_frame, textvariable=self.filename_var, width=200)
        self.filename_entry.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Методология:").pack(side="left", padx=(20,0))
        self.methodology_var = ctk.StringVar(value="Не выбирать (GPT сам решит)")
        self.methodology_menu = ctk.CTkComboBox(top_frame, variable=self.methodology_var, width=300)
        self.methodology_menu.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="Настройки", command=self.open_settings).pack(side="right")

        prompt_frame = ctk.CTkFrame(self)
        prompt_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(prompt_frame, text="Введите промт для ChatGPT:").pack(anchor="w")
        self.prompt_text = ctk.CTkTextbox(prompt_frame, height=120, font=("Consolas", 13))
        self.prompt_text.pack(fill="x")
        bind_ctrl_v(self.prompt_text)

        clear_btn_frame = ctk.CTkFrame(prompt_frame)
        clear_btn_frame.pack(fill="x", pady=(5,0))
        ctk.CTkButton(clear_btn_frame, text="Очистить промт", command=self.clear_prompt, width=120).pack(anchor="e")

        action_frame = ctk.CTkFrame(self)
        action_frame.pack(pady=10)

        self.gen_button = ctk.CTkButton(action_frame, text="Сгенерировать схему", font=("Segoe UI", 14, "bold"),
                                        fg_color="#00cc77", command=self.on_generate)
        self.gen_button.pack(side="left")

        self.fail_label_var = ctk.StringVar(value="Неудачных попыток: 0")
        self.fail_label = ctk.CTkLabel(action_frame, textvariable=self.fail_label_var, text_color="red",
                                      font=("Segoe UI", 12, "bold"))
        self.fail_label.pack(side="left", padx=20)

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(pady=5)
        self.progress.stop()

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="both", expand=True, padx=10, pady=5)

        left_frame = ctk.CTkFrame(bottom_frame, width=350)
        left_frame.pack(side="left", fill="y")

        ctk.CTkLabel(left_frame, text="Сохранённые схемы:").pack(anchor="w")
        self.scheme_listbox = tk.Listbox(left_frame, width=35, height=30)
        self.scheme_listbox.pack(side="left", fill="y")
        self.scheme_listbox.bind("<<ListboxSelect>>", self.on_scheme_select)

        scrollbar = ctk.CTkScrollbar(left_frame, orientation="vertical", command=self.scheme_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.scheme_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(left_frame)
        btn_frame.pack(pady=10, fill="x")
        ctk.CTkButton(btn_frame, text="Показать код", command=self.show_code).pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Загрузить код в промт", command=self.load_code_to_prompt).pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Экспорт схемы в папку вывода", command=self.export_scheme_files).pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Удалить выбранную схему", fg_color="#cc3300", hover_color="#ff4d4d",
                      command=self.delete_selected_scheme).pack(fill="x", pady=10)

        right_frame = ctk.CTkFrame(bottom_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=10)

        ctk.CTkLabel(right_frame, text="Превью схемы:").pack(anchor="w")
        self.preview_label = ctk.CTkLabel(right_frame, fg_color="gray")
        self.preview_label.pack(fill="both", expand=True)

        self.apply_config()
        self.load_methodologies()
        self.load_scheme_list()

    def clear_prompt(self):
        self.prompt_text.delete("0.0", "end")

    def open_settings(self):
        # Передаём функцию сохранения конфигурации в окно настроек
        SettingsWindow(self, self.config_data, self.save_config, METHODOLOGIES_DIR, self.load_methodologies)

    def on_settings_save(self, new_config):
        self.config_data = new_config
        self.apply_config()
        self.save_config()

    def apply_config(self):
        self.improve_prompt = self.config_data.get("improve_prompt", False)
        try:
            self.max_retries = int(self.config_data.get("max_retries", 5))
        except Exception:
            self.max_retries = 5

    def save_config(self, config=None):
        if config is None:
            config = self.config_data
        save_config(config)

    def load_methodologies(self):
        try:
            files = [f for f in os.listdir(METHODOLOGIES_DIR) if f.endswith(".txt")]
        except Exception:
            files = []
        self.loaded_methodologies = {}
        for f in files:
            try:
                path = os.path.join(METHODOLOGIES_DIR, f)
                with open(path, "r", encoding="utf-8") as file:
                    desc = file.read().strip()
                    name = os.path.splitext(f)[0]
                    self.loaded_methodologies[name] = desc
            except Exception:
                pass
        values = ["Не выбирать (GPT сам решит)"] + sorted(self.loaded_methodologies.keys())
        self.methodology_menu.configure(values=values)
        if self.methodology_var.get() not in values:
            self.methodology_var.set("Не выбирать (GPT сам решит)")

    def load_scheme_list(self):
        self.scheme_listbox.delete(0, tk.END)
        schemes = self.db.get_all_schemes()
        for sid, fname in schemes:
            self.scheme_listbox.insert("end", f"{sid}: {fname}")

    # Остальной код без изменений (on_scheme_select, show_code, load_code_to_prompt,
    # export_scheme_files, delete_selected_scheme, on_generate, worker_thread_retry,
    # safe_update_fail_label, safe_log, safe_notify, safe_finish, safe_load_scheme_list,
    # safe_show_preview, log, on_closing)

    def on_scheme_select(self, event):
        sel = self.scheme_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        item_text = self.scheme_listbox.get(idx)
        scheme_id = int(item_text.split(":")[0])
        data = self.db.get_scheme_by_id(scheme_id)
        if data:
            filename, code, image_path, image_data = data
            if image_data:
                try:
                    img = Image.open(BytesIO(image_data))
                    img.thumbnail((self.preview_label.winfo_width(), self.preview_label.winfo_height()), Image.Resampling.LANCZOS)
                    self.imgtk = ImageTk.PhotoImage(img)
                    self.preview_label.configure(image=self.imgtk, text="")
                except Exception as e:
                    self.preview_label.configure(image="", text=f"Ошибка загрузки изображения:\n{e}")
            else:
                if image_path and os.path.isfile(image_path):
                    try:
                        img = Image.open(image_path)
                        img.thumbnail((self.preview_label.winfo_width(), self.preview_label.winfo_height()), Image.Resampling.LANCZOS)
                        self.imgtk = ImageTk.PhotoImage(img)
                        self.preview_label.configure(image=self.imgtk, text="")
                    except Exception as e:
                        self.preview_label.configure(image="", text=f"Ошибка загрузки изображения:\n{e}")
                else:
                    self.preview_label.configure(image="", text="Изображение не найдено")
            self.filename_var.set(filename)

    def show_code(self):
        sel = self.scheme_listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите схему из списка.")
            return
        idx = sel[0]
        item_text = self.scheme_listbox.get(idx)
        scheme_id = int(item_text.split(":")[0])
        data = self.db.get_scheme_by_id(scheme_id)
        if data:
            _, code, _, _ = data
            CodeViewer(self, code)

    def load_code_to_prompt(self):
        sel = self.scheme_listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите схему из списка.")
            return
        idx = sel[0]
        item_text = self.scheme_listbox.get(idx)
        scheme_id = int(item_text.split(":")[0])
        data = self.db.get_scheme_by_id(scheme_id)
        if data:
            _, code, _, _ = data
            self.prompt_text.delete("0.0", "end")
            self.prompt_text.insert("0.0", code)

    def export_scheme_files(self):
        sel = self.scheme_listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите схему из списка.")
            return
        idx = sel[0]
        item_text = self.scheme_listbox.get(idx)
        scheme_id = int(item_text.split(":")[0])
        data = self.db.get_scheme_by_id(scheme_id)
        if not data:
            messagebox.showerror("Ошибка", "Данные схемы не найдены.")
            return
        filename, code, image_path, _ = data
        output_dir = self.config_data.get("output_dir", str(IMAGES_DIR))
        if not os.path.isdir(output_dir):
            messagebox.showerror("Ошибка", "Некорректная папка вывода.")
            return

        try:
            uml_path = os.path.join(output_dir, f"{filename}.uml")
            with open(uml_path, "w", encoding="utf-8") as f:
                f.write(code)

            if image_path and os.path.isfile(image_path):
                png_path = os.path.join(output_dir, os.path.basename(image_path))
                shutil.copy2(image_path, png_path)
            else:
                png_path = None

            msg = f"Схема экспортирована:\n{uml_path}"
            if png_path:
                msg += f"\n{png_path}"
            self.safe_notify("Экспорт завершён", msg)
        except Exception as e:
            self.safe_notify("Ошибка при экспорте", str(e), error=True)

    def delete_selected_scheme(self):
        sel = self.scheme_listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите схему для удаления.")
            return
        idx = sel[0]
        item_text = self.scheme_listbox.get(idx)
        scheme_id = int(item_text.split(":")[0])
        if messagebox.askyesno("Подтверждение", f"Удалить схему ID {scheme_id}?"):
            self.db.delete_scheme_by_id(scheme_id)
            self.load_scheme_list()
            self.preview_label.configure(image="", text="")
            self.filename_var.set("")
            self.fail_label_var.set("Неудачных попыток: 0")

    def on_generate(self):
        self.failed_attempts = 0
        self.fail_label_var.set(f"Неудачных попыток: {self.failed_attempts}")

        prompt = self.prompt_text.get("0.0", "end").strip()
        methodology = self.methodology_var.get()
        methodology_prompt = self.loaded_methodologies.get(methodology, "")

        improve_prompt = self.config_data.get("improve_prompt", False)
        try:
            max_retries = int(self.config_data.get("max_retries", 5))
        except Exception:
            max_retries = 5

        prompt_improve_1 = self.config_data.get("prompt_improve_1", "").strip()
        prompt_improve_2 = self.config_data.get("prompt_improve_2", "").strip()

        if improve_prompt:
            combined_prompt = "Придумай схему, а затем сгенерируй код для PlantUML, чтобы он нарисовал схему, придуманную тобой. Далее подробное описание темы.\n\n"
            combined_prompt += prompt
            if methodology_prompt:
                combined_prompt += f"\n\nИспользуй следующую методологию для рисования схемы:\n{methodology_prompt}"
            if prompt_improve_1:
                combined_prompt += f"\n\n{prompt_improve_1}"
            if prompt_improve_2:
                combined_prompt += f"\n\n{prompt_improve_2}"
            combined_prompt += "\n\nПерепроверь код, сделай его ПОЛНОСТЬЮ корректным, чтобы PlantUML сгенерировал хорошую схему."
            prompt = combined_prompt
        else:
            if methodology_prompt:
                prompt += f"\n\nИспользуй следующую методологию для рисования схемы:\n{methodology_prompt}"

        output_dir = self.config_data.get("output_dir", str(IMAGES_DIR))
        filename = self.filename_var.get().strip()
        jar_path = self.config_data.get("jar_path", str(PLANTUML_JAR_PATH))

        if not jar_path or not os.path.isfile(jar_path):
            messagebox.showerror("Ошибка", "Укажите корректный путь к plantuml.jar в настройках")
            return
        if not prompt.strip():
            messagebox.showerror("Ошибка", "Введите промт.")
            return
        if not filename:
            messagebox.showerror("Ошибка", "Введите имя файла схемы.")
            return
        if not os.path.isdir(output_dir):
            messagebox.showerror("Ошибка", "Некорректная папка вывода.")
            return
        if any(c in filename for c in r'\/:*?"<>|'):
            messagebox.showerror("Ошибка", "Имя файла содержит недопустимые символы.")
            return

        self.save_config()
        self.gen_button.configure(state="disabled")
        self.progress.start()
        self.preview_label.configure(image="", text="")
        self.log("Отправка запроса ChatGPT...")

        threading.Thread(target=self.worker_thread_retry, args=(prompt, output_dir, filename, jar_path, max_retries), daemon=True).start()

    def worker_thread_retry(self, prompt, output_dir, filename, jar_path, max_retries):
        current_prompt = prompt
        self.failed_attempts = 0
        self.safe_update_fail_label()
        for attempt in range(1, max_retries + 1):
            try:
                response = ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": current_prompt}]
                )
                self.safe_log(f"Ответ получен (попытка {attempt}).")
                plantuml_code = extract_plantuml_code(response)
                if not plantuml_code:
                    self.safe_log("Код PlantUML не найден в ответе.")
                    self.safe_notify("Ошибка", "Код PlantUML не найден в ответе.")
                    self.safe_finish()
                    return

                self.safe_log("Извлечён код PlantUML.")
                self.safe_log("Генерация схемы...")
                png_path = generate_plantuml_diagram(plantuml_code, output_dir, filename, jar_path)
                self.safe_log(f"Схема успешно сгенерирована: {png_path}")

                dest_img_path = IMAGES_DIR / f"{filename}.png"
                with open(png_path, "rb") as f_src:
                    data = f_src.read()
                with open(dest_img_path, "wb") as f_dst:
                    f_dst.write(data)

                self.db.add_scheme(filename, plantuml_code, str(dest_img_path))
                self.safe_log("Схема и код сохранены в базе данных.")
                self.safe_notify("Генерация завершена", f"Схема успешно сохранена:\n{dest_img_path}")

                self.safe_load_scheme_list()
                self.safe_show_preview(str(dest_img_path))
                self.safe_finish()
                return

            except RuntimeError as e:
                err_text = str(e)
                if "Some diagram description contains errors" in err_text or "diagram description contains errors" in err_text.lower():
                    self.failed_attempts += 1
                    self.safe_update_fail_label()
                    self.safe_log(f"Ошибка PlantUML: {err_text}")
                    self.safe_log("Попытка исправить код с помощью GPT...")
                    current_prompt = (
                        current_prompt
                        + "\n\nКод PlantUML содержит ошибки. Пожалуйста, исправь и выведи корректный, рабочий код."
                    )
                    time.sleep(1)
                    continue
                else:
                    self.safe_log(f"Ошибка PlantUML: {err_text}")
                    self.safe_notify("Ошибка PlantUML", err_text, error=True)
                    break
            except Exception as e:
                self.safe_log(f"Ошибка: {e}")
                self.safe_notify("Ошибка", str(e), error=True)
                break
        self.safe_finish()

    def safe_update_fail_label(self):
        def update():
            self.fail_label_var.set(f"Неудачных попыток: {self.failed_attempts}")
        self.after(0, update)

    def safe_log(self, message):
        self.after(0, lambda: self.log(message))

    def safe_notify(self, title, message, error=False):
        def notify():
            if error:
                messagebox.showerror(title, message)
            else:
                messagebox.showinfo(title, message)
        self.after(0, notify)

    def safe_finish(self):
        def finish():
            self.progress.stop()
            self.gen_button.configure(state="normal")
        self.after(0, finish)

    def safe_load_scheme_list(self):
        self.after(0, self.load_scheme_list)

    def safe_show_preview(self, image_path):
        def show():
            if not os.path.isfile(image_path):
                self.preview_label.configure(image="", text="Изображение не найдено")
                return
            try:
                img = Image.open(image_path)
                img.thumbnail((self.preview_label.winfo_width(), self.preview_label.winfo_height()), Image.Resampling.LANCZOS)
                self.imgtk = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=self.imgtk, text="")
            except Exception as e:
                self.preview_label.configure(image="", text=f"Ошибка загрузки изображения:\n{e}")
        self.after(0, show)

    def log(self, message):
        print(message)

    def on_closing(self):
        self.db.close()
        self.save_config()
        self.destroy()

if __name__ == "__main__":
    ensure_dirs()
    app = PlantUMLApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
