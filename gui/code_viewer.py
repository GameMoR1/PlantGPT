import customtkinter as ctk
import tkinter as tk
from utils.text_utils import bind_ctrl_v as bind_ctrl_v

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
