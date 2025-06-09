import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import threading
import shutil
import time
from io import BytesIO

from db.database import Database
from utils.dirs import ensure_dirs, IMAGES_DIR, METHODOLOGIES_DIR, PLANTUML_JAR_PATH
from utils.config import load_config, save_config
from utils.plantuml import extract_plantuml_code, generate_plantuml_diagram
from utils.text_utils import bind_ctrl_v
from gui.code_viewer import CodeViewer
from gui.settings_window import SettingsWindow
from g4f import ChatCompletion

class PlantUMLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PlantGPT")
        self.geometry("1200x820")

        ensure_dirs()

        self.config_data = load_config()
        ctk.set_appearance_mode(self.config_data.get("theme", "dark"))

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
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def clear_prompt(self):
        self.prompt_text.delete("0.0", "end")

    def clear_prompt(self):
        self.prompt_text.delete("0.0", "end")

    def open_settings(self):
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
            messagebox.showinfo("Экспорт завершён", msg)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")

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
            messagebox.showerror("Ошибка", "Укажите корректный пути к plantuml.jar в настройках")
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
        print("Отправка запроса ChatGPT...")

        threading.Thread(target=self.worker_thread_retry, args=(prompt, output_dir, filename, jar_path, max_retries), daemon=True).start()

    def worker_thread_retry(self, prompt, output_dir, filename, jar_path, max_retries):
        current_prompt = prompt
        self.failed_attempts = 0
        self.after(0, lambda: self.fail_label_var.set(f"Неудачных попыток: {self.failed_attempts}"))
        for attempt in range(1, max_retries + 1):
            try:
                response = ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": current_prompt}]
                )
                self.after(0, lambda: print(f"Ответ получен (попытка {attempt})."))
                plantuml_code = extract_plantuml_code(response)
                if not plantuml_code:
                    self.after(0, lambda: print("Код PlantUML не найден в ответе."))
                    self.after(0, lambda: messagebox.showerror("Ошибка", "Код PlantUML не найден в ответе."))
                    self.after(0, lambda: self.progress.stop())
                    self.after(0, lambda: self.gen_button.configure(state="normal"))
                    return

                self.after(0, lambda: print("Извлечён код PlantUML."))
                self.after(0, lambda: print("Генерация схемы..."))
                png_path = generate_plantuml_diagram(plantuml_code, output_dir, filename, jar_path)
                self.after(0, lambda: print(f"Схема успешно сгенерирована: {png_path}"))

                dest_img_path = os.path.join(IMAGES_DIR, f"{filename}.png")
                with open(png_path, "rb") as f_src:
                    data = f_src.read()
                with open(dest_img_path, "wb") as f_dst:
                    f_dst.write(data)

                self.db.add_scheme(filename, plantuml_code, str(dest_img_path))
                self.after(0, lambda: print("Схема и код сохранены в базе данных."))
                self.after(0, lambda: messagebox.showinfo("Генерация завершена", f"Схема успешно сохранена:\n{dest_img_path}"))

                self.after(0, lambda: self.load_scheme_list())
                self.after(0, lambda: self.safe_show_preview(str(dest_img_path)))
                self.after(0, lambda: self.progress.stop())
                self.after(0, lambda: self.gen_button.configure(state="normal"))
                return

            except RuntimeError as e:
                err_text = str(e)
                if "Some diagram description contains errors" in err_text or "diagram description contains errors" in err_text.lower():
                    self.failed_attempts += 1
                    self.after(0, lambda: self.fail_label_var.set(f"Неудачных попыток: {self.failed_attemps}"))
                    self.after(0, lambda: print(f"Ошибка PlantUML: {err_text}"))
                    self.after(0, lambda: print("Попытка исправить код с помощью GPT..."))
                    current_prompt = (
                        current_prompt
                        + "\n\nКод PlantUML содержит ошибки. Пожалуйста, исправь и выведи корректный, рабочий код."
                    )
                    time.sleep(1)
                    continue
                else:
                    self.after(0, lambda: print(f"Ошибка PlantUML: {err_text}"))
                    self.after(0, lambda: messagebox.showerror("Ошибка PlantUML", err_text))
                    break
            except Exception as e:
                self.after(0, lambda: print(f"Ошибка: {e}"))
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
                break
        self.after(0, lambda: self.progress.stop())
        self.after(0, lambda: self.gen_button.configure(state="normal"))

    def safe_show_preview(self, image_path):
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

    def on_closing(self):
        self.db.close()
        self.save_config()
        self.destroy()
