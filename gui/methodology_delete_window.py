import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import os

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
