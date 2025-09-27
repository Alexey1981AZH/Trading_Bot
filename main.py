"""Графический интерфейс торгового бота на Tkinter."""
from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict

CONFIG_FILE = Path("config.json")


class TradingBotGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Trading Bot")
        self.root.geometry("720x600")

        self.vars: Dict[str, tk.Variable] = {
            "symbol": tk.StringVar(value="SBER"),
            "timeframe": tk.StringVar(value="5"),
            "position_size": tk.StringVar(value="10"),
            "stop_loss": tk.StringVar(value="2.0"),
            "take_profit": tk.StringVar(value="4.0"),
            "sma_fast": tk.StringVar(value="9"),
            "sma_slow": tk.StringVar(value="21"),
            "rsi_period": tk.StringVar(value="14"),
            "rsi_lower": tk.StringVar(value="30"),
            "rsi_upper": tk.StringVar(value="70"),
            "breakout_lookback": tk.StringVar(value="20"),
            "api_token": tk.StringVar(value=""),
        }

        self.status_var = tk.StringVar(value="Статус: отключено")
        self.status_color = "#d9534f"
        self.robot_running = False

        self._build_layout()
        self.load_config(show_message=False, log=False)

    def _build_layout(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, anchor=tk.N)

        self._add_entry(form_frame, "Инструмент", "symbol", row=0)
        self._add_entry(form_frame, "Таймфрейм (мин)", "timeframe", row=1)
        self._add_entry(form_frame, "Размер позиции", "position_size", row=2)
        self._add_entry(form_frame, "Stop Loss (%)", "stop_loss", row=3)
        self._add_entry(form_frame, "Take Profit (%)", "take_profit", row=4)
        self._add_entry(form_frame, "API Token", "api_token", row=5, show="*")

        sma_frame = ttk.LabelFrame(main_frame, text="SMA")
        sma_frame.pack(fill=tk.X, pady=8)
        self._add_entry(sma_frame, "Быстрая", "sma_fast", row=0)
        self._add_entry(sma_frame, "Медленная", "sma_slow", row=1)

        rsi_frame = ttk.LabelFrame(main_frame, text="RSI")
        rsi_frame.pack(fill=tk.X, pady=8)
        self._add_entry(rsi_frame, "Период", "rsi_period", row=0)
        self._add_entry(rsi_frame, "Нижний уровень", "rsi_lower", row=1)
        self._add_entry(rsi_frame, "Верхний уровень", "rsi_upper", row=2)

        breakout_frame = ttk.LabelFrame(main_frame, text="Пробой уровня")
        breakout_frame.pack(fill=tk.X, pady=8)
        self._add_entry(breakout_frame, "Длина окна", "breakout_lookback", row=0)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Запустить робота", command=self.start_robot).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Остановить робота", command=self.stop_robot).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Сохранить конфиг", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Загрузить конфиг", command=lambda: self.load_config()).pack(side=tk.LEFT, padx=5)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, anchor="w", bg=self.status_color, fg="white", padx=6, pady=4)
        self.status_label.pack(fill=tk.X)

        log_frame = ttk.LabelFrame(main_frame, text="Логи")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_text = tk.Text(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _add_entry(self, parent: ttk.Frame, label: str, key: str, *, row: int, show: str | None = None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        entry = ttk.Entry(parent, textvariable=self.vars[key], show=show)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=4, padx=6)
        parent.grid_columnconfigure(1, weight=1)

    def load_config(self, *, show_message: bool = True, log: bool = True) -> None:
        if not CONFIG_FILE.exists():
            if show_message:
                messagebox.showinfo("Информация", "Файл config.json не найден.")
            return

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError) as exc:
            messagebox.showerror("Ошибка", f"Не удалось загрузить конфиг: {exc}")
            return

        for key, value in data.items():
            var = self.vars.get(key)
            if var is not None:
                var.set(str(value))

        if show_message:
            messagebox.showinfo("Информация", "Конфиг загружен.")
        if log:
            self.append_log("Конфиг загружен из config.json.")

    def _collect_config(self) -> Dict[str, str]:
        return {key: var.get() for key, var in self.vars.items()}

    def save_config(self) -> None:
        config = self._collect_config()
        try:
            with CONFIG_FILE.open("w", encoding="utf-8") as file:
                json.dump(config, file, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфиг: {exc}")
            return
        self.append_log("Конфиг сохранён.")

    def start_robot(self) -> None:
        if self.robot_running:
            messagebox.showinfo("Информация", "Робот уже запущен.")
            return
        self.robot_running = True
        self._set_status("Статус: подключение", "#f0ad4e")
        # TODO: реализовать реальный запуск и проверку подключения к API
        self.root.after(500, lambda: self._set_status("Статус: подключено", "#5cb85c"))
        self.append_log("Робот запущен с параметрами:")
        for key, value in self._collect_config().items():
            self.append_log(f"  {key}: {value}")

    def stop_robot(self) -> None:
        if not self.robot_running:
            messagebox.showinfo("Информация", "Робот ещё не запущен.")
            return
        self.robot_running = False
        self._set_status("Статус: остановлено", "#d9534f")
        self.append_log("Робот остановлен.")

    def append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def _set_status(self, text: str, color: str) -> None:
        self.status_var.set(text)
        self.status_color = color
        self.status_label.configure(bg=color)


def main() -> None:
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
