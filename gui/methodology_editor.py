import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
from utils.text_utils import bind_ctrl_v

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
