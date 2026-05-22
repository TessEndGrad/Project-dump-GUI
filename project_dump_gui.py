#!/usr/bin/env python3
"""
project_dump_gui.py — GUI-приложение для сборки дампа проекта (tkinter).
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# ──────────────────────────────────────────────
#  Настройки по умолчанию
# ──────────────────────────────────────────────

DEFAULT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".env", ".md", ".txt",
    ".sh", ".bash", ".sql", ".rs", ".go", ".java", ".c", ".cpp",
    ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".dart", ".vue",
    ".svelte", ".xml", ".ini", ".cfg", ".conf"
}

DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".npm", ".yarn",
    "venv", ".venv", "env", ".env", "virtualenv",
    "dist", "build", ".next", ".nuxt", ".output",
    ".idea", ".vscode",
    "coverage", ".coverage", "htmlcov",
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock",
    "*.pyc", "*.pyo",
}

# ──────────────────────────────────────────────
#  Логика сборки дампа
# ──────────────────────────────────────────────

def should_ignore_dir(dirname, ignore_dirs):
    return dirname in ignore_dirs or dirname.startswith(".")

def should_ignore_file(filename, ignore_files):
    if filename in ignore_files:
        return True
    for pattern in ignore_files:
        if pattern.startswith("*") and filename.endswith(pattern[1:]):
            return True
    return False

def is_text_file(filename, extensions):
    _, ext = os.path.splitext(filename)
    return ext.lower() in extensions

def read_file_safe(filepath):
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return "[Не удалось прочитать файл — возможно, бинарный]"

def collect_files(root_dir, extensions, ignore_dirs, ignore_files):
    result = []
    root_dir = os.path.abspath(root_dir)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = sorted([
            d for d in dirnames if not should_ignore_dir(d, ignore_dirs)
        ])
        for filename in sorted(filenames):
            if should_ignore_file(filename, ignore_files):
                continue
            if not is_text_file(filename, extensions):
                continue
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)
            content = read_file_safe(filepath)
            result.append((rel_path, content))
    return result

def build_tree(files, root_name):
    lines = [f"{root_name}/"]
    all_entries = set()
    for rel_path, _ in files:
        parts = rel_path.replace("\\", "/").split("/")
        for i in range(len(parts)):
            all_entries.add(tuple(parts[:i+1]))

    def render(prefix_tuple, indent=""):
        children = sorted([
            e for e in all_entries
            if len(e) == len(prefix_tuple) + 1 and e[:len(prefix_tuple)] == prefix_tuple
        ])
        out = []
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            out.append(f"{indent}{connector}{child[-1]}")
            extension = "    " if is_last else "│   "
            out.extend(render(child, indent + extension))
        return out

    lines.extend(render(()))
    return "\n".join(lines)

def build_dump(project_dir, extensions, ignore_dirs, ignore_files, log_fn):
    root_name = os.path.basename(os.path.abspath(project_dir)) or "project"
    log_fn(f"📂 Сканирование: {project_dir}")
    files = collect_files(project_dir, extensions, ignore_dirs, ignore_files)
    log_fn(f"📄 Найдено файлов: {len(files)}")

    lines = []
    lines.append("=" * 60)
    lines.append(f"  ДАМП ПРОЕКТА: {root_name}")
    lines.append(f"  Файлов: {len(files)}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("📁 СТРУКТУРА ПРОЕКТА")
    lines.append("-" * 60)
    lines.append(build_tree(files, root_name))
    lines.append("")
    lines.append("=" * 60)
    lines.append("")
    lines.append("📄 СОДЕРЖИМОЕ ФАЙЛОВ")
    lines.append("=" * 60)
    lines.append("")

    for rel_path, content in files:
        lines.append(f"{rel_path}-------")
        lines.append(content if content.endswith("\n") else content + "\n")
        lines.append("-" * 26)
        lines.append("")
        log_fn(f"  ✓ {rel_path}")

    return "\n".join(lines), len(files)

# ──────────────────────────────────────────────
#  GUI
# ──────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Dump — Дамп проекта для LLM")
        self.geometry("780x620")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")
        self._build_ui()

    # ── UI ──────────────────────────────────────

    def _build_ui(self):
        PAD = 12
        BG = "#1e1e2e"
        CARD = "#2a2a3e"
        ACCENT = "#7c6af7"
        FG = "#cdd6f4"
        FG2 = "#a6adc8"
        ENTRY_BG = "#313244"
        BTN_BG = "#7c6af7"
        BTN_FG = "#ffffff"
        BTN_HOV = "#9580ff"

        self._colors = dict(bg=BG, card=CARD, accent=ACCENT, fg=FG, fg2=FG2,
                            entry_bg=ENTRY_BG, btn_bg=BTN_BG, btn_fg=BTN_FG, btn_hov=BTN_HOV)

        # ── Заголовок
        hdr = tk.Frame(self, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🗂  Project Dump", font=("Segoe UI", 14, "bold"),
                 bg=ACCENT, fg="#ffffff", pady=10).pack(side="left", padx=PAD)

        # ── Основная зона
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # ── Левая панель (настройки)
        left = tk.Frame(main, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground="#45475a", width=340)
        left.pack(side="left", fill="y", padx=(0, PAD//2))
        left.pack_propagate(False)

        self._section(left, "📁  Папка проекта")
        proj_row = tk.Frame(left, bg=CARD)
        proj_row.pack(fill="x", padx=10, pady=(0, 10))
        self.var_proj = tk.StringVar()
        tk.Entry(proj_row, textvariable=self.var_proj, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 9),
                 bd=4).pack(side="left", fill="x", expand=True)
        self._btn(proj_row, "…", self._browse_project, small=True).pack(side="left", padx=(4, 0))

        self._section(left, "💾  Выходной файл")
        out_row = tk.Frame(left, bg=CARD)
        out_row.pack(fill="x", padx=10, pady=(0, 10))
        self.var_out = tk.StringVar(value="project_dump.txt")
        tk.Entry(out_row, textvariable=self.var_out, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 9),
                 bd=4).pack(side="left", fill="x", expand=True)
        self._btn(out_row, "…", self._browse_output, small=True).pack(side="left", padx=(4, 0))

        self._section(left, "🔧  Расширения (через пробел или запятую)")
        self.txt_exts = tk.Text(left, height=4, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                                relief="flat", font=("Consolas", 8), bd=4, wrap="word")
        self.txt_exts.pack(fill="x", padx=10, pady=(0, 10))
        self.txt_exts.insert("1.0", " ".join(sorted(DEFAULT_EXTENSIONS)))

        self._section(left, "🚫  Игнорировать папки")
        self.txt_ignore = tk.Text(left, height=4, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                                  relief="flat", font=("Consolas", 8), bd=4, wrap="word")
        self.txt_ignore.pack(fill="x", padx=10, pady=(0, 10))
        self.txt_ignore.insert("1.0", " ".join(sorted(DEFAULT_IGNORE_DIRS)))

        # Кнопка запуска
        self.btn_run = self._btn(left, "▶  Создать дамп", self._run, big=True)
        self.btn_run.pack(fill="x", padx=10, pady=10)

        # Прогресс
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Accent.Horizontal.TProgressbar",
                        troughcolor=ENTRY_BG, background=ACCENT,
                        thickness=6, borderwidth=0)
        self.progress = ttk.Progressbar(left, mode="indeterminate",
                                        style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=10, pady=(0, 6))

        self.lbl_status = tk.Label(left, text="Готов к работе", bg=CARD, fg=FG2,
                                   font=("Segoe UI", 8), anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=(0, 10))

        # ── Правая панель (лог + предпросмотр)
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # Вкладка Лог
        tab_log = tk.Frame(nb, bg=BG)
        nb.add(tab_log, text="  📋 Лог  ")
        self.log_box = scrolledtext.ScrolledText(
            tab_log, bg="#181825", fg="#a6e3a1", insertbackground=FG,
            font=("Consolas", 9), relief="flat", state="disabled",
            wrap="none", bd=0)
        self.log_box.pack(fill="both", expand=True)

        # Вкладка Предпросмотр
        tab_prev = tk.Frame(nb, bg=BG)
        nb.add(tab_prev, text="  👁 Предпросмотр  ")
        self.prev_box = scrolledtext.ScrolledText(
            tab_prev, bg="#181825", fg=FG, insertbackground=FG,
            font=("Consolas", 9), relief="flat", state="disabled",
            wrap="none", bd=0)
        self.prev_box.pack(fill="both", expand=True)

        # ── Нижняя панель
        bot = tk.Frame(self, bg="#181825", height=32)
        bot.pack(fill="x", side="bottom")
        self.lbl_info = tk.Label(bot, text="", bg="#181825", fg=FG2,
                                 font=("Segoe UI", 8))
        self.lbl_info.pack(side="left", padx=PAD)
        self._btn(bot, "📋 Копировать", self._copy_result, small=True).pack(side="right", padx=PAD, pady=4)

        self._result_text = ""

    def _section(self, parent, title):
        c = self._colors
        tk.Label(parent, text=title, bg=c["card"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold"), anchor="w",
                 pady=6).pack(fill="x", padx=10)

    def _btn(self, parent, text, cmd, small=False, big=False):
        c = self._colors
        font = ("Segoe UI", 9, "bold") if big else ("Segoe UI", 9)
        padx, pady = (8, 4) if small else (12, 8)
        b = tk.Button(parent, text=text, command=cmd, bg=c["btn_bg"], fg=c["btn_fg"],
                      activebackground=c["btn_hov"], activeforeground=c["btn_fg"],
                      relief="flat", font=font, padx=padx, pady=pady, bd=0, cursor="hand2")
        b.bind("<Enter>", lambda e: b.configure(bg=c["btn_hov"]))
        b.bind("<Leave>", lambda e: b.configure(bg=c["btn_bg"]))
        return b

    # ── Действия ────────────────────────────────

    def _browse_project(self):
        path = filedialog.askdirectory(title="Выберите папку проекта")
        if path:
            self.var_proj.set(path)
            # Авто-имя выходного файла
            name = os.path.basename(path) or "project"
            self.var_out.set(os.path.join(path, f"{name}_dump.txt"))

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить дамп как...",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.var_out.set(path)

    def _parse_extensions(self):
        raw = self.txt_exts.get("1.0", "end").strip()
        raw = raw.replace(",", " ")
        parts = raw.split()
        exts = set()
        for p in parts:
            p = p.strip()
            if p and not p.startswith("."):
                p = "." + p
            if p:
                exts.add(p.lower())
        return exts or DEFAULT_EXTENSIONS

    def _parse_ignore_dirs(self):
        raw = self.txt_ignore.get("1.0", "end").strip()
        raw = raw.replace(",", " ")
        parts = raw.split()
        return set(p.strip() for p in parts if p.strip()) or DEFAULT_IGNORE_DIRS

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, msg):
        self.lbl_status.configure(text=msg)

    def _run(self):
        project_dir = self.var_proj.get().strip()
        output_file = self.var_out.get().strip()

        if not project_dir:
            messagebox.showwarning("Нет папки", "Пожалуйста, выберите папку проекта.")
            return
        if not os.path.isdir(project_dir):
            messagebox.showerror("Ошибка", f"Папка не найдена:\n{project_dir}")
            return
        if not output_file:
            messagebox.showwarning("Нет файла", "Укажите имя выходного файла.")
            return

        # Очистить лог и предпросмотр
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.prev_box.configure(state="normal")
        self.prev_box.delete("1.0", "end")
        self.prev_box.configure(state="disabled")

        extensions = self._parse_extensions()
        ignore_dirs = self._parse_ignore_dirs()

        self.btn_run.configure(state="disabled", text="⏳  Обработка...")
        self.progress.start(12)
        self._set_status("Сканирование файлов...")

        def worker():
            try:
                dump_text, count = build_dump(
                    project_dir, extensions, ignore_dirs,
                    DEFAULT_IGNORE_FILES, self._log
                )
                # Сохранить файл
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(dump_text)
                self._result_text = dump_text
                self.after(0, lambda: self._on_done(count, output_file, dump_text))
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, count, output_file, dump_text):
        self.progress.stop()
        self.btn_run.configure(state="normal", text="▶  Создать дамп")
        self._set_status(f"✅  Готово — {count} файлов")
        self.lbl_info.configure(
            text=f"✅  {count} файлов → {os.path.basename(output_file)}  "
                 f"({len(dump_text):,} символов)"
        )
        self._log(f"\n✅ Сохранено: {output_file}")
        self._log(f"   Всего символов: {len(dump_text):,}")

        # Предпросмотр (первые 8000 символов)
        preview = dump_text[:8000] + ("\n\n... [обрезано для предпросмотра]" if len(dump_text) > 8000 else "")
        self.prev_box.configure(state="normal")
        self.prev_box.delete("1.0", "end")
        self.prev_box.insert("1.0", preview)
        self.prev_box.configure(state="disabled")

    def _on_error(self, msg):
        self.progress.stop()
        self.btn_run.configure(state="normal", text="▶  Создать дамп")
        self._set_status("❌  Ошибка")
        self._log(f"❌ Ошибка: {msg}")
        messagebox.showerror("Ошибка", msg)

    def _copy_result(self):
        if not self._result_text:
            messagebox.showinfo("Пусто", "Сначала создайте дамп.")
            return
        self.clipboard_clear()
        self.clipboard_append(self._result_text)
        self.lbl_info.configure(text="📋  Скопировано в буфер обмена!")


if __name__ == "__main__":
    app = App()
    app.mainloop()
