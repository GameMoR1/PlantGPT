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
