import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import urllib.request
from pathlib import Path

from utils.text_utils import bind_ctrl_v as bind_ctrl_v
from utils.dirs import IMAGES_DIR, PLANTUML_JAR_PATH, PLANTUML_DIR, PLANTUML_DOWNLOAD_URL
from gui.methodology_editor import MethodologyEditor
from gui.methodology_delete_window import MethodologyDeleteWindow

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

        # 1. Тема приложения — переключатель в самом верху
        theme_frame = ctk.CTkFrame(frame)
        theme_frame.grid(row=0, column=0, columnspan=4, pady=10, sticky="ew")
        ctk.CTkLabel(theme_frame, text="Тема приложения:").pack(side="left", padx=10)
        self.theme_var = ctk.StringVar(value=self.config_data.get("theme", "dark"))
        self.theme_switch = ctk.CTkSwitch(
            theme_frame, text="", command=self.change_theme,
            variable=self.theme_var, onvalue="dark", offvalue="light"
        )
        self.theme_switch = ctk.CTkSwitch(
            theme_frame, text="", command=self.change_theme,
            variable=self.theme_var, onvalue="dark", offvalue="light"
        )
        self.theme_switch = ctk.CTkSwitch(
            theme_frame, text="", command=self.change_theme,
            variable=self.theme_var, onvalue="dark", offvalue="light"
        )
        self.theme_switch.pack(side="left", padx=5)
        self.theme_label = ctk.CTkLabel(
            theme_frame,
            text="Тёмная тема" if self.theme_var.get() == "dark" else "Светлая тема",
            font=("Arial", 14)
        )
        self.theme_label.pack(side="left", padx=5)

        # Jar path
        ctk.CTkLabel(frame, text="Путь к plantuml.jar:").grid(row=1, column=0, sticky="w")
        self.jar_path_var = ctk.StringVar(value=self.config_data.get("jar_path", str(PLANTUML_JAR_PATH)))
        self.jar_entry = ctk.CTkEntry(frame, textvariable=self.jar_path_var, width=400)
        self.jar_entry.grid(row=1, column=1, sticky="ew", padx=5)
        ctk.CTkButton(frame, text="Выбрать...", command=self.choose_jar).grid(row=1, column=2, padx=5)
        ctk.CTkButton(frame, text="Скачать plantuml.jar", command=self.download_plantuml).grid(row=1, column=3, padx=5)

        # Download progress label
        self.download_progress_label = ctk.CTkLabel(frame, textvariable=self.download_progress_var, text_color="blue")
        self.download_progress_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0,10))

        # Output dir
        ctk.CTkLabel(frame, text="Папка вывода:").grid(row=3, column=0, sticky="w", pady=10)
        self.dir_var = ctk.StringVar(value=self.config_data.get("output_dir", str(IMAGES_DIR)))
        self.dir_entry = ctk.CTkEntry(frame, textvariable=self.dir_var, width=400)
        self.dir_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=10)
        ctk.CTkButton(frame, text="Выбрать...", command=self.choose_dir).grid(row=3, column=2, padx=5, pady=10)

        # Improve prompt checkbox
        self.improve_prompt_var = ctk.BooleanVar(value=self.config_data.get("improve_prompt", False))
        self.improve_cb = ctk.CTkCheckBox(frame, text="Улучшить промт", variable=self.improve_prompt_var)
        self.improve_cb.grid(row=4, column=0, columnspan=4, sticky="w")

        # Max retries
        ctk.CTkLabel(frame, text="Макс. попыток генерации схемы:").grid(row=5, column=0, sticky="w", pady=10)
        self.max_retries_var = ctk.StringVar(value=str(self.config_data.get("max_retries", 5)))
        self.max_retries_entry = ctk.CTkEntry(frame, textvariable=self.max_retries_var, width=60)
        self.max_retries_entry.grid(row=5, column=1, sticky="w", padx=5, pady=10)

        # Prompt improvements inputs
        ctk.CTkLabel(frame, text="Промт для улучшения (часть 1):").grid(row=6, column=0, sticky="nw", pady=(20,5))
        self.prompt_improve_1 = ctk.CTkTextbox(frame, height=80)
        self.prompt_improve_1.grid(row=6, column=1, columnspan=3, sticky="ew", pady=(20,5), padx=(0,10))
        self.prompt_improve_1.insert("0.0", self.config_data.get("prompt_improve_1", ""))
        bind_ctrl_v(self.prompt_improve_1)

        ctk.CTkLabel(frame, text="Промт для улучшения (часть 2):").grid(row=7, column=0, sticky="nw", pady=5)
        self.prompt_improve_2 = ctk.CTkTextbox(frame, height=80)
        self.prompt_improve_2.grid(row=7, column=1, columnspan=3, sticky="ew", pady=5, padx=(0,10))
        self.prompt_improve_2.insert("0.0", self.config_data.get("prompt_improve_2", ""))
        bind_ctrl_v(self.prompt_improve_2)

        # Buttons for methodology management and folder cleaning
        btn_meth_frame = ctk.CTkFrame(frame)
        btn_meth_frame.grid(row=8, column=0, columnspan=4, pady=10, sticky="ew")
        ctk.CTkButton(btn_meth_frame, text="Добавить методологию", command=self.open_methodology_editor).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Удалить методологии", command=self.open_methodology_delete).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Очистить папку с изображениями", command=self.clear_images).pack(side="left", padx=10)
        ctk.CTkButton(btn_meth_frame, text="Сбросить настройки", command=self.reset_settings).pack(side="left", padx=10)

        # Save/Cancel buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=9, column=0, columnspan=4, pady=20)
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.on_save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Отмена", command=self.destroy).pack(side="left", padx=10)

        frame.columnconfigure(1, weight=1)
        self.update_theme_label()

    def change_theme(self):
        theme = self.theme_var.get()
        ctk.set_appearance_mode(theme)
        self.update_theme_label()
        self.config_data["theme"] = theme
        self.save_callback(self.config_data)

    def update_theme_label(self):
        theme = self.theme_var.get()
        self.theme_label.configure(text="Тёмная тема" if theme == "dark" else "Светлая тема")

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
            "prompt_improve_2": "",
            "theme": "dark"
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
        self.theme_var.set(self.config_data["theme"])
        ctk.set_appearance_mode(self.config_data["theme"])
        self.update_theme_label()

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
        self.config_data["theme"] = self.theme_var.get()
        self.save_callback(self.config_data)
        self.destroy()
