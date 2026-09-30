# -*- coding: utf-8 -*-
"""
Клавіатурний тренажер для дітей "Спритні пальчики" / "Smart Fingers"
Розроблено спеціально для легкого навчання сліпому та швидкому друку дітьми.
Повністю автономний застосунок: працює на будь-якому ПК без встановленого Python.
"""

import sys
import os
import json
import time
import random
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

# Спроба увімкнути High-DPI масштабування для чіткого тексту на екранах Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Звуковий рушій через winsound на Windows
try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False

# Шляхи до файлів
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # Якщо скомпільовано в .exe
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
ICON_FILE = os.path.join(BASE_DIR, "icon.ico")


# --- Звуковий менеджер (фоновий потік, щоб інтерфейс ніколи не гальмував) ---
class SoundManager:
    def __init__(self):
        self.enabled = True
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            sound_type = self.queue.get()
            if not self.enabled or not HAS_WINSOUND:
                self.queue.task_done()
                continue
            try:
                if sound_type == "correct":
                    winsound.Beep(650, 60)
                elif sound_type == "wrong":
                    winsound.Beep(260, 90)
                elif sound_type == "streak":
                    winsound.Beep(523, 50)
                    winsound.Beep(659, 50)
                    winsound.Beep(784, 80)
                elif sound_type == "complete":
                    winsound.Beep(523, 60)
                    winsound.Beep(659, 60)
                    winsound.Beep(784, 60)
                    winsound.Beep(1046, 120)
            except Exception:
                pass
            self.queue.task_done()

    def play(self, sound_type):
        if self.enabled and HAS_WINSOUND:
            self.queue.put(sound_type)

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled


# --- Збереження та завантаження прогресу учнів ---
class ProgressManager:
    def __init__(self):
        self.data = self.load()

    def load(self):
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "students": {},
            "last_student": "Юний Чемпіон",
            "sound_enabled": True
        }

    def save(self):
        try:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_student(self, name, avatar="🚀"):
        if name not in self.data["students"]:
            self.data["students"][name] = {
                "avatar": avatar,
                "stars": 0,
                "score": 0,
                "total_typed": 0,
                "correct_typed": 0,
                "best_arcade_score": 0,
                "words_typed": 0,
                "achievements": []
            }
            self.save()
        return self.data["students"][name]


# --- Словники та навчальні набори ---
CONTENT = {
    "UA": {
        "levels": [
            {
                "id": "home",
                "name": "Домашній ряд (Ф І В А / О Л Д Ж)",
                "desc": "Початкова позиція пальчиків",
                "chars": ["Ф", "І", "В", "А", "П", "Р", "О", "Л", "Д", "Ж", "Є"]
            },
            {
                "id": "top",
                "name": "Верхній ряд (Й Ц У К Е Н...)",
                "desc": "Тренуємо рух пальців угору",
                "chars": ["Й", "Ц", "У", "К", "Е", "Н", "Г", "Ш", "Щ", "З", "Х", "Ї"]
            },
            {
                "id": "bottom",
                "name": "Нижній ряд (Я Ч С М И Т...)",
                "desc": "Тренуємо рух пальців униз",
                "chars": ["Я", "Ч", "С", "М", "И", "Т", "Ь", "Б", "Ю"]
            },
            {
                "id": "digits",
                "name": "Цифри та знаки (1 2 3 ...)",
                "desc": "Цифри верхнього ряду",
                "chars": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
            },
            {
                "id": "all_letters",
                "name": "Весь алфавіт (Усі літери)",
                "desc": "Майстерність усього поля клавіатури",
                "chars": list("АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ")
            }
        ],
        "words": [
            ("КІТ", "🐱"), ("ПЕС", "🐶"), ("СОНЦЕ", "☀️"), ("ДІМ", "🏠"),
            ("ЯБЛУКО", "🍎"), ("РАКЕТА", "🚀"), ("ЗІРКА", "⭐️"), ("ВЕСЕЛКА", "🌈"),
            ("КВІТКА", "🌸"), ("АВТО", "🚗"), ("КНИГА", "📚"), ("РИБКА", "🐟"),
            ("ЖАБКА", "🐸"), ("ЛЕВ", "🦁"), ("ДЕРЕВО", "🌲"), ("КУЛЬКА", "🎈"),
            ("М'ЯЧ", "⚽"), ("БДЖОЛА", "🐝"), ("КАВУН", "🍉"), ("МОРКВА", "🥕"),
            ("ГРИБОК", "🍄"), ("МІСЯЦЬ", "🌙"), ("ЛІТАК", "✈️"), ("ЧОВЕН", "⛵"),
            ("РОВЕР", "🚲"), ("ФАРБИ", "🎨"), ("ПОДАРУНОК", "🎁"), ("МЕД", "🍯")
        ],
        "sentences": [
            "Ми любимо вчитися і грати!",
            "Котик спить на теплому сонечку.",
            "Яскрава ракета летить у космос.",
            "Веселка має сім чарівних кольорів.",
            "У лісі ростуть смачні грибочки.",
            "Діти весело грають у м'яч у дворі.",
            "Спритні пальчики друкують швидко й легко!",
            "Книга — це найкращий друг кожної дитини."
        ]
    },
    "EN": {
        "levels": [
            {
                "id": "home",
                "name": "Home Row (A S D F / J K L ;)",
                "desc": "Base finger position",
                "chars": ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"]
            },
            {
                "id": "top",
                "name": "Top Row (Q W E R T Y...)",
                "desc": "Moving fingers up",
                "chars": ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
            },
            {
                "id": "bottom",
                "name": "Bottom Row (Z X C V B...)",
                "desc": "Moving fingers down",
                "chars": ["Z", "X", "C", "V", "B", "N", "M"]
            },
            {
                "id": "digits",
                "name": "Digits (1 2 3 ...)",
                "desc": "Top digit keys",
                "chars": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
            },
            {
                "id": "all_letters",
                "name": "All Letters (A to Z)",
                "desc": "Full keyboard practice",
                "chars": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            }
        ],
        "words": [
            ("CAT", "🐱"), ("DOG", "🐶"), ("SUN", "☀️"), ("HOME", "🏠"),
            ("APPLE", "🍎"), ("ROCKET", "🚀"), ("STAR", "⭐️"), ("RAINBOW", "🌈"),
            ("FLOWER", "🌸"), ("CAR", "🚗"), ("BOOK", "📚"), ("FISH", "🐟"),
            ("FROG", "🐸"), ("LION", "🦁"), ("TREE", "🌲"), ("BALLOON", "🎈"),
            ("BALL", "⚽"), ("BEE", "🐝"), ("MELON", "🍉"), ("MOON", "🌙"),
            ("PLANE", "✈️"), ("BOAT", "⛵"), ("BIKE", "🚲"), ("GIFT", "🎁")
        ],
        "sentences": [
            "We love to learn and play together!",
            "The cute cat is sleeping in the sun.",
            "A fast rocket flies into space.",
            "The rainbow has seven beautiful colors.",
            "Quick fingers type fast and easily!",
            "Reading books makes you smart and happy."
        ]
    }
}

# Розкладки клавіатури з координатами та зонами пальців
FINGER_COLORS = {
    "LP": "#FFB3BA",  # Лівий мізинець (Pink)
    "LR": "#FFDFBA",  # Лівий безіменний (Peach)
    "LM": "#FFFFBA",  # Лівий середній (Light Yellow)
    "LI": "#BAFFC9",  # Лівий вказівний (Mint)
    "RI": "#BAE1FF",  # Правий вказівний (Sky Blue)
    "RM": "#C7CEEA",  # Правий середній (Periwinkle)
    "RR": "#E2BAFF",  # Правий безіменний (Lavender)
    "RP": "#FFBAEC",  # Правий мізинець (Rose)
    "TH": "#E2ECE9"   # Великі пальці (Пробіл)
}

FINGER_NAMES_UA = {
    "LP": "Лівий мізинець",
    "LR": "Лівий безіменний",
    "LM": "Лівий середній",
    "LI": "Лівий вказівний",
    "RI": "Правий вказівний",
    "RM": "Правий середній",
    "RR": "Правий безіменний",
    "RP": "Правий мізинець",
    "TH": "Великий палець (Пробіл)"
}

FINGER_NAMES_EN = {
    "LP": "Left Pinky",
    "LR": "Left Ring",
    "LM": "Left Middle",
    "LI": "Left Index",
    "RI": "Right Index",
    "RM": "Right Middle",
    "RR": "Right Ring",
    "RP": "Right Pinky",
    "TH": "Thumb (Spacebar)"
}

# Клавіатурні ряди (символ, пальцева зона, відносна ширина дефолт=1.0)
KEYBOARD_LAYOUTS = {
    "UA": [
        # Ряд цифр
        [("'", "LP"), ("1", "LP"), ("2", "LR"), ("3", "LM"), ("4", "LI"), ("5", "LI"),
         ("6", "RI"), ("7", "RI"), ("8", "RM"), ("9", "RR"), ("0", "RP"), ("-", "RP"), ("=", "RP")],
        # Ряд 1
        [("Й", "LP"), ("Ц", "LR"), ("У", "LM"), ("К", "LI"), ("Е", "LI"),
         ("Н", "RI"), ("Г", "RI"), ("Ш", "RM"), ("Щ", "RR"), ("З", "RP"), ("Х", "RP"), ("Ї", "RP")],
        # Ряд 2 (Домашній)
        [("Ф", "LP"), ("І", "LR"), ("В", "LM"), ("А", "LI"), ("П", "LI"),
         ("Р", "RI"), ("О", "RI"), ("Л", "RM"), ("Д", "RR"), ("Ж", "RP"), ("Є", "RP")],
        # Ряд 3
        [("Я", "LP"), ("Ч", "LR"), ("С", "LM"), ("М", "LI"), ("И", "LI"),
         ("Т", "RI"), ("Ь", "RI"), ("Б", "RM"), ("Ю", "RR"), (".", "RP"), (",", "RP")],
        # Пробіл
        [("ПРОБІЛ", "TH", 5.5)]
    ],
    "EN": [
        # Digits row
        [("`", "LP"), ("1", "LP"), ("2", "LR"), ("3", "LM"), ("4", "LI"), ("5", "LI"),
         ("6", "RI"), ("7", "RI"), ("8", "RM"), ("9", "RR"), ("0", "RP"), ("-", "RP"), ("=", "RP")],
        # Row 1
        [("Q", "LP"), ("W", "LR"), ("E", "LM"), ("R", "LI"), ("T", "LI"),
         ("Y", "RI"), ("U", "RI"), ("I", "RM"), ("O", "RR"), ("P", "RP"), ("[", "RP"), ("]", "RP")],
        # Row 2 (Home)
        [("A", "LP"), ("S", "LR"), ("D", "LM"), ("F", "LI"), ("G", "LI"),
         ("H", "RI"), ("J", "RI"), ("K", "RM"), ("L", "RR"), (";", "RP"), ("'", "RP")],
        # Row 3
        [("Z", "LP"), ("X", "LR"), ("C", "LM"), ("V", "LI"), ("B", "LI"),
         ("N", "RI"), ("M", "RI"), (",", "RM"), (".", "RR"), ("/", "RP")],
        # Spacebar
        [("SPACE", "TH", 5.5)]
    ]
}


class KidsKeyboardTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Клавіатурний тренажер для дітей • Спритні пальчики 🚀")
        self.geometry("980x700")
        self.minsize(880, 640)
        self.configure(bg="#EEF2F6")

        # Встановлення іконки вікна
        if os.path.exists(ICON_FILE):
            try:
                self.iconbitmap(ICON_FILE)
            except Exception:
                pass

        # Менеджери
        self.sound = SoundManager()
        self.progress = ProgressManager()

        # Поточний стан
        self.lang = "UA"  # "UA" або "EN"
        self.mode = "letters"  # "letters", "words", "arcade", "sentences"
        self.current_student_name = self.progress.data.get("last_student", "Юний Чемпіон")
        self.current_avatar = "🚀"
        self.student_data = self.progress.get_student(self.current_student_name, self.current_avatar)

        # Ігрові змінні
        self.target_char = ""
        self.target_word = ""
        self.word_index = 0
        self.current_emoji = "⭐️"
        self.selected_level_index = 0
        self.streak = 0
        self.session_typed = 0
        self.session_correct = 0

        # Змінні режиму "Падаючі літери" (Аркада)
        self.arcade_running = False
        self.arcade_items = []  # [{ "char": "А", "x": 100, "y": 20, "speed": 2.5, "id": tag }]
        self.arcade_score = 0
        self.arcade_lives = 3

        # Створення компонентів інтерфейсу
        self.build_ui()
        self.select_mode("letters")

        # Глобальний слухач клавіатури
        self.bind("<Key>", self.handle_key_press)

    def build_ui(self):
        # 1. Верхня панель (Шапка програми)
        header_frame = tk.Frame(self, bg="#3A6073", height=65)
        header_frame.pack(side="top", fill="x")

        # Ліва частина шапки: Профіль учня
        profile_frame = tk.Frame(header_frame, bg="#3A6073")
        profile_frame.pack(side="left", padx=15, pady=8)

        self.avatar_btn = tk.Button(
            profile_frame, text=self.current_avatar, font=("Segoe UI Emoji", 18),
            bg="#2E4C5D", fg="white", bd=0, relief="flat", padx=6, pady=2,
            cursor="hand2", command=self.change_avatar_dialog
        )
        self.avatar_btn.pack(side="left", padx=(0, 8))

        name_col = tk.Frame(profile_frame, bg="#3A6073")
        name_col.pack(side="left")

        self.name_label = tk.Label(
            name_col, text=self.current_student_name, font=("Segoe UI", 12, "bold"),
            bg="#3A6073", fg="white", cursor="hand2"
        )
        self.name_label.pack(anchor="w")
        self.name_label.bind("<Button-1>", lambda e: self.change_name_dialog())

        self.stats_label = tk.Label(
            name_col, text="Зірочки: ⭐ 0  |  Точність: 100%",
            font=("Segoe UI", 9), bg="#3A6073", fg="#D0E3F0"
        )
        self.stats_label.pack(anchor="w")

        # Центр шапки: Назва та маскот
        center_frame = tk.Frame(header_frame, bg="#3A6073")
        center_frame.pack(side="left", expand=True)

        self.title_banner = tk.Label(
            center_frame, text="🚀 Спритні пальчики 🌟",
            font=("Segoe UI", 16, "bold"), bg="#3A6073", fg="#FDE047"
        )
        self.title_banner.pack()

        # Права частина шапки: Мова, Звук, Рекорди
        right_frame = tk.Frame(header_frame, bg="#3A6073")
        right_frame.pack(side="right", padx=15, pady=8)

        # Перемикач мови
        self.lang_btn = tk.Button(
            right_frame, text="🇺🇦 Укр", font=("Segoe UI", 10, "bold"),
            bg="#2563EB", fg="white", relief="flat", padx=10, pady=4,
            cursor="hand2", command=self.toggle_language
        )
        self.lang_btn.pack(side="left", padx=4)

        # Перемикач звуку
        self.sound_btn = tk.Button(
            right_frame, text="🔊", font=("Segoe UI Emoji", 12),
            bg="#16A34A", fg="white", relief="flat", padx=8, pady=2,
            cursor="hand2", command=self.toggle_sound
        )
        self.sound_btn.pack(side="left", padx=4)

        # Кнопка рекордів
        records_btn = tk.Button(
            right_frame, text="🏆 Рекорди", font=("Segoe UI", 10, "bold"),
            bg="#F59E0B", fg="white", relief="flat", padx=8, pady=4,
            cursor="hand2", command=self.show_records_window
        )
        records_btn.pack(side="left", padx=4)

        # 2. Панель вибору режимів (Tabs)
        mode_bar = tk.Frame(self, bg="#E2E8F0", height=45)
        mode_bar.pack(side="top", fill="x")

        self.mode_buttons = {}
        modes = [
            ("letters", "🔤 Літери та ряди"),
            ("words", "🐱 Веселі слова"),
            ("arcade", "☄️ Падаючі літери"),
            ("sentences", "📖 Речення")
        ]

        for m_id, m_text in modes:
            btn = tk.Button(
                mode_bar, text=m_text, font=("Segoe UI", 10, "bold"),
                bg="#E2E8F0", fg="#475569", bd=0, relief="flat", padx=16, pady=8,
                cursor="hand2", command=lambda mid=m_id: self.select_mode(mid)
            )
            btn.pack(side="left", padx=2, pady=2)
            self.mode_buttons[m_id] = btn

        # 3. Головна робоча зона (Картка завдань)
        self.work_area = tk.Frame(self, bg="#EEF2F6")
        self.work_area.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # 4. Нижня зона: Віртуальна інтерактивна клавіатура
        self.kbd_frame = tk.Frame(self, bg="#CBD5E1", height=230)
        self.kbd_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 10))

        # Панель підказки пальця над клавіатурою
        hint_bar = tk.Frame(self.kbd_frame, bg="#CBD5E1")
        hint_bar.pack(side="top", fill="x", pady=(4, 2))

        self.finger_hint_label = tk.Label(
            hint_bar, text="👉 Натискай: [Вказівний палець]",
            font=("Segoe UI", 11, "bold"), bg="#CBD5E1", fg="#1E293B"
        )
        self.finger_hint_label.pack(side="left", padx=20)

        self.streak_label = tk.Label(
            hint_bar, text="🔥 Серія: 0",
            font=("Segoe UI", 11, "bold"), bg="#CBD5E1", fg="#EA580C"
        )
        self.streak_label.pack(side="right", padx=20)

        # Canvas для клавіатури
        self.kbd_canvas = tk.Canvas(self.kbd_frame, bg="#F1F5F9", height=190, bd=0, highlightthickness=0)
        self.kbd_canvas.pack(fill="both", expand=True, padx=6, pady=4)
        self.kbd_canvas.bind("<Configure>", lambda e: self.draw_keyboard())

        self.key_rects = {}  # { char: [rect_id, text_id, base_color] }

        # Оновлення статистики
        self.update_stats_display()

    # --- Зміна режимів навчання ---
    def select_mode(self, mode_id):
        # Зупинити аркаду, якщо вона працювала
        if self.mode == "arcade" and mode_id != "arcade":
            self.arcade_running = False

        self.mode = mode_id
        for mid, btn in self.mode_buttons.items():
            if mid == mode_id:
                btn.configure(bg="#FFFFFF", fg="#2563EB", relief="groove")
            else:
                btn.configure(bg="#E2E8F0", fg="#475569", relief="flat")

        # Очистити робочу зону
        for widget in self.work_area.winfo_children():
            widget.destroy()

        self.streak = 0
        self.streak_label.configure(text="🔥 Серія: 0")

        if mode_id == "letters":
            self.setup_letters_view()
        elif mode_id == "words":
            self.setup_words_view()
        elif mode_id == "arcade":
            self.setup_arcade_view()
        elif mode_id == "sentences":
            self.setup_sentences_view()

        self.draw_keyboard()

    # --- РЕЖИМ 1: ЛІТЕРИ ТА РЯДИ ---
    def setup_letters_view(self):
        # Верхня панель: вибір підрівня
        sublevels_frame = tk.Frame(self.work_area, bg="#EEF2F6")
        sublevels_frame.pack(fill="x", pady=(0, 10))

        tk.Label(sublevels_frame, text="Оберіть ряд:", font=("Segoe UI", 10, "bold"), bg="#EEF2F6", fg="#334155").pack(side="left", padx=5)

        levels = CONTENT[self.lang]["levels"]
        self.level_var = tk.StringVar(value=levels[self.selected_level_index]["name"])
        level_combo = ttk.Combobox(
            sublevels_frame, textvariable=self.level_var,
            values=[lvl["name"] for lvl in levels], state="readonly", width=35, font=("Segoe UI", 10)
        )
        level_combo.pack(side="left", padx=5)
        level_combo.bind("<<ComboboxSelected>>", self.on_level_selected)

        # Картка з великою літерою
        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

        self.mascot_msg = tk.Label(
            card, text="Натисни літеру на клавіатурі! 👇",
            font=("Segoe UI", 12), bg="#FFFFFF", fg="#64748B"
        )
        self.mascot_msg.pack(pady=(10, 0))

        self.big_char_label = tk.Label(
            card, text="?", font=("Arial", 78, "bold"),
            bg="#FFFFFF", fg="#2563EB"
        )
        self.big_char_label.pack(expand=True)

        self.feedback_label = tk.Label(
            card, text="", font=("Segoe UI", 14, "bold"),
            bg="#FFFFFF", fg="#16A34A"
        )
        self.feedback_label.pack(pady=(0, 15))

        self.next_letter()

    def on_level_selected(self, event=None):
        name = self.level_var.get()
        levels = CONTENT[self.lang]["levels"]
        for idx, lvl in enumerate(levels):
            if lvl["name"] == name:
                self.selected_level_index = idx
                break
        self.next_letter()

    def next_letter(self):
        levels = CONTENT[self.lang]["levels"]
        chars = levels[self.selected_level_index]["chars"]
        # Уникаємо повторення однієї й тієї самої літери поспіль
        new_char = random.choice(chars)
        while len(chars) > 1 and new_char == self.target_char:
            new_char = random.choice(chars)

        self.target_char = new_char
        self.big_char_label.configure(text=self.target_char, fg="#2563EB")
        self.update_finger_hint(self.target_char)
        self.highlight_keyboard_key(self.target_char)

    # --- РЕЖИМ 2: ВЕСЕЛІ СЛОВА З ЕМОДЗІ ---
    def setup_words_view(self):
        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

        self.word_emoji_label = tk.Label(
            card, text="🐱", font=("Segoe UI Emoji", 54),
            bg="#FFFFFF"
        )
        self.word_emoji_label.pack(pady=(15, 0))

        # Контейнер для літер слова
        self.word_chars_frame = tk.Frame(card, bg="#FFFFFF")
        self.word_chars_frame.pack(expand=True, pady=10)
        self.word_char_labels = []

        self.word_feedback_label = tk.Label(
            card, text="Вводь літеру за літерою!", font=("Segoe UI", 13, "bold"),
            bg="#FFFFFF", fg="#64748B"
        )
        self.word_feedback_label.pack(pady=(0, 15))

        self.next_word()

    def next_word(self):
        words = CONTENT[self.lang]["words"]
        word, emoji = random.choice(words)
        self.target_word = word
        self.current_emoji = emoji
        self.word_index = 0

        self.word_emoji_label.configure(text=emoji)

        # Очистити старі літери
        for lbl in self.word_char_labels:
            lbl.destroy()
        self.word_char_labels = []

        # Створити нові картки для кожної літери слова
        for ch in self.target_word:
            lbl = tk.Label(
                self.word_chars_frame, text=ch, font=("Segoe UI", 36, "bold"),
                bg="#F1F5F9", fg="#64748B", width=2, relief="solid", bd=1
            )
            lbl.pack(side="left", padx=4)
            self.word_char_labels.append(lbl)

        self.update_word_highlight()

    def update_word_highlight(self):
        if self.word_index < len(self.target_word):
            curr_char = self.target_word[self.word_index]
            self.target_char = curr_char
            self.word_char_labels[self.word_index].configure(
                bg="#FEF08A", fg="#854D0E", relief="ridge", bd=2
            )
            self.update_finger_hint(curr_char)
            self.highlight_keyboard_key(curr_char)
            self.word_feedback_label.configure(
                text=f"Наступна літера: '{curr_char}'", fg="#3B82F6"
            )
        else:
            # Слово завершено!
            self.target_char = ""
            self.sound.play("complete")
            self.student_data["stars"] += 2
            self.student_data["words_typed"] += 1
            self.update_stats_display()
            self.word_feedback_label.configure(
                text="🎉 Чудово! Слово зібрано! +2 ⭐", fg="#16A34A"
            )
            self.after(900, self.next_word)

    # --- РЕЖИМ 3: ПАДАЮЧІ ЛІТЕРИ (АРКАДНА МІНІ-ГРА) ---
    def setup_arcade_view(self):
        card = tk.Frame(self.work_area, bg="#0F172A", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

        # Верхня панель гри: Бали, Життя, Кнопка старту
        arcade_bar = tk.Frame(card, bg="#1E293B")
        arcade_bar.pack(fill="x", padx=10, pady=5)

        self.arcade_score_lbl = tk.Label(
            arcade_bar, text="Бали: 0", font=("Segoe UI", 12, "bold"),
            bg="#1E293B", fg="#FDE047"
        )
        self.arcade_score_lbl.pack(side="left", padx=10)

        self.arcade_lives_lbl = tk.Label(
            arcade_bar, text="Життя: ❤️❤️❤️", font=("Segoe UI", 12, "bold"),
            bg="#1E293B", fg="#F87171"
        )
        self.arcade_lives_lbl.pack(side="left", padx=10)

        self.arcade_btn = tk.Button(
            arcade_bar, text="▶️ Почати гру", font=("Segoe UI", 10, "bold"),
            bg="#10B981", fg="white", relief="flat", padx=12, pady=3,
            cursor="hand2", command=self.toggle_arcade
        )
        self.arcade_btn.pack(side="right", padx=10)

        # Canvas гри
        self.arcade_canvas = tk.Canvas(card, bg="#0B132B", bd=0, highlightthickness=0)
        self.arcade_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.arcade_running = False
        self.arcade_items = []
        self.arcade_score = 0
        self.arcade_lives = 3

    def toggle_arcade(self):
        if not self.arcade_running:
            self.arcade_running = True
            self.arcade_score = 0
            self.arcade_lives = 3
            self.arcade_items.clear()
            self.arcade_canvas.delete("all")
            self.arcade_btn.configure(text="⏸️ Пауза", bg="#EF4444")
            self.arcade_score_lbl.configure(text="Бали: 0")
            self.arcade_lives_lbl.configure(text="Життя: ❤️❤️❤️")
            self.spawn_arcade_char()
            self.arcade_loop()
        else:
            self.arcade_running = False
            self.arcade_btn.configure(text="▶️ Продовжити", bg="#10B981")

    def spawn_arcade_char(self):
        if not self.arcade_running:
            return
        w = self.arcade_canvas.winfo_width() or 600
        x = random.randint(50, max(50, w - 60))
        # Обираємо випадкову літеру з поточного алфавіту
        levels = CONTENT[self.lang]["levels"]
        pool = levels[self.selected_level_index]["chars"]
        char = random.choice(pool)

        # Малюємо коло-метеорит та літеру
        tag = f"star_{random.randint(1000, 9999)}"
        circle_id = self.arcade_canvas.create_oval(
            x - 22, -45, x + 22, -1, fill="#F59E0B", outline="#FDE047", width=2, tags=tag
        )
        text_id = self.arcade_canvas.create_text(
            x, -23, text=char, fill="#FFFFFF", font=("Segoe UI", 16, "bold"), tags=tag
        )

        item = {
            "char": char,
            "x": x,
            "y": -23,
            "speed": random.uniform(1.2, 2.2),
            "tag": tag,
            "circle_id": circle_id,
            "text_id": text_id
        }
        self.arcade_items.append(item)

        # Наступний метеорит через інтервал
        if self.arcade_running:
            self.after(random.randint(1800, 2600), self.spawn_arcade_char)

    def arcade_loop(self):
        if not self.arcade_running:
            return

        h = self.arcade_canvas.winfo_height() or 300
        to_remove = []

        # Якщо є хоча б один об'єкт на полі, підсвітимо найнижчий на клавіатурі
        lowest_item = None
        max_y = -999

        for item in self.arcade_items:
            item["y"] += item["speed"]
            self.arcade_canvas.move(item["tag"], 0, item["speed"])
            if item["y"] > max_y:
                max_y = item["y"]
                lowest_item = item

            # Торкнувся дна
            if item["y"] > h - 10:
                to_remove.append(item)
                self.arcade_canvas.delete(item["tag"])
                self.arcade_lives -= 1
                self.sound.play("wrong")
                lives_text = "❤️" * max(0, self.arcade_lives) + "🖤" * (3 - max(0, self.arcade_lives))
                self.arcade_lives_lbl.configure(text=f"Життя: {lives_text}")
                if self.arcade_lives <= 0:
                    self.end_arcade_game()
                    return

        for item in to_remove:
            if item in self.arcade_items:
                self.arcade_items.remove(item)

        if lowest_item:
            self.target_char = lowest_item["char"]
            self.update_finger_hint(self.target_char)
            self.highlight_keyboard_key(self.target_char)
        else:
            self.target_char = ""

        if self.arcade_running:
            self.after(35, self.arcade_loop)

    def end_arcade_game(self):
        self.arcade_running = False
        self.arcade_btn.configure(text="🔄 Спробувати ще раз", bg="#10B981")
        if self.arcade_score > self.student_data.get("best_arcade_score", 0):
            self.student_data["best_arcade_score"] = self.arcade_score
            self.progress.save()
            msg = f"🏆 НОВИЙ РЕКОРД! Ти набрав {self.arcade_score} очок!"
        else:
            msg = f"Гру завершено! Твій результат: {self.arcade_score} очок."

        self.arcade_canvas.create_text(
            self.arcade_canvas.winfo_width() / 2, self.arcade_canvas.winfo_height() / 2,
            text=msg, fill="#FDE047", font=("Segoe UI", 16, "bold")
        )

    # --- РЕЖИМ 4: РЕЧЕННЯ ---
    def setup_sentences_view(self):
        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

        tk.Label(
            card, text="📖 Друкуємо веселі речення:", font=("Segoe UI", 13, "bold"),
            bg="#FFFFFF", fg="#334155"
        ).pack(pady=(12, 5))

        self.sentence_canvas = tk.Canvas(card, bg="#F8FAFC", height=70, bd=1, relief="solid")
        self.sentence_canvas.pack(fill="x", padx=25, pady=10)

        self.sent_feedback = tk.Label(
            card, text="Друкуй символи по порядку!", font=("Segoe UI", 12),
            bg="#FFFFFF", fg="#64748B"
        )
        self.sent_feedback.pack(pady=5)

        self.next_sentence()

    def next_sentence(self):
        sentences = CONTENT[self.lang]["sentences"]
        self.target_sentence = random.choice(sentences)
        self.sentence_index = 0
        self.render_sentence_text()

    def render_sentence_text(self):
        self.sentence_canvas.delete("all")
        typed_part = self.target_sentence[:self.sentence_index]
        curr_char = self.target_sentence[self.sentence_index] if self.sentence_index < len(self.target_sentence) else ""
        rest_part = self.target_sentence[self.sentence_index + 1:] if self.sentence_index < len(self.target_sentence) else ""

        # Зелена надрукована частина
        self.sentence_canvas.create_text(
            30, 35, anchor="w", text=typed_part,
            font=("Consolas", 18, "bold"), fill="#16A34A"
        )

        # Визначаємо поточну літеру
        if curr_char:
            self.target_char = "ПРОБІЛ" if curr_char == " " else curr_char.upper()
            self.update_finger_hint(self.target_char)
            self.highlight_keyboard_key(self.target_char)

            # Малюємо жовту підсвітку під поточною літерою
            # Вимірюємо ширину через canvas
            # Приблизне розміщення
            all_text_so_far = typed_part + curr_char
            self.sentence_canvas.create_text(
                30, 35, anchor="w",
                text=typed_part + curr_char + rest_part,
                font=("Consolas", 18), fill="#94A3B8"
            )
            # Перемальовуємо вже надруковані зеленим
            self.sentence_canvas.create_text(
                30, 35, anchor="w", text=typed_part,
                font=("Consolas", 18, "bold"), fill="#16A34A"
            )
        else:
            # Завершено речення!
            self.sound.play("complete")
            self.student_data["stars"] += 5
            self.update_stats_display()
            self.sent_feedback.configure(text="🎉 Чудово! Речення завершено! +5 ⭐", fg="#16A34A")
            self.after(1200, self.next_sentence)

    # --- ВІЗУАЛЬНА ІНТЕРАКТИВНА КЛАВІАТУРА ---
    def draw_keyboard(self):
        self.kbd_canvas.delete("all")
        self.key_rects.clear()

        w = self.kbd_canvas.winfo_width()
        h = self.kbd_canvas.winfo_height()
        if w < 200 or h < 100:
            return

        layout = KEYBOARD_LAYOUTS[self.lang]
        num_rows = len(layout)
        row_h = (h - 20) / num_rows
        key_margin = 3

        for r_idx, row in enumerate(layout):
            y1 = 8 + r_idx * row_h
            y2 = y1 + row_h - key_margin

            # Підрахунок загальної ширини рядка в одиницях
            total_units = sum(item[2] if len(item) > 2 else 1.0 for item in row)
            unit_w = (w - 30) / max(13.5, total_units)

            # Центрування рядка
            row_pixel_w = total_units * unit_w
            x_cursor = (w - row_pixel_w) / 2

            for item in row:
                char = item[0]
                finger_code = item[1]
                key_w_units = item[2] if len(item) > 2 else 1.0
                x1 = x_cursor
                x2 = x1 + key_w_units * unit_w - key_margin
                x_cursor += key_w_units * unit_w

                base_color = FINGER_COLORS.get(finger_code, "#FFFFFF")

                # Малюємо скруглену клавішу
                rect_id = self.create_rounded_rect(
                    self.kbd_canvas, x1, y1, x2, y2, radius=8,
                    fill=base_color, outline="#94A3B8", width=1.5
                )

                # Текст клавіші
                font_size = 10 if len(char) > 2 else 12
                font_weight = "bold" if len(char) == 1 else "normal"
                text_id = self.kbd_canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=char, fill="#1E293B", font=("Segoe UI", font_size, font_weight)
                )

                self.key_rects[char.upper()] = {
                    "rect": rect_id,
                    "text": text_id,
                    "base_color": base_color,
                    "finger": finger_code
                }

        # Якщо є активна цільова літера, підсвітити її
        if self.target_char:
            self.highlight_keyboard_key(self.target_char)

    def create_rounded_rect(self, canvas, x1, y1, x2, y2, radius=8, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def highlight_keyboard_key(self, char):
        # Скидаємо всі клавіші до їхніх базових кольорів
        for k_char, data in self.key_rects.items():
            self.kbd_canvas.itemconfig(data["rect"], fill=data["base_color"], outline="#94A3B8", width=1.5)

        char_key = char.upper()
        if char_key in self.key_rects:
            data = self.key_rects[char_key]
            # Яскраве сяйво: золотистий колір та товста обводка
            self.kbd_canvas.itemconfig(data["rect"], fill="#FBBF24", outline="#D97706", width=3)
            self.kbd_canvas.tag_raise(data["rect"])
            self.kbd_canvas.tag_raise(data["text"])

    def flash_key(self, char, is_correct):
        char_key = char.upper()
        if char_key in self.key_rects:
            data = self.key_rects[char_key]
            flash_color = "#4ADE80" if is_correct else "#F87171"
            self.kbd_canvas.itemconfig(data["rect"], fill=flash_color, outline="#FFFFFF", width=3)
            # Повертаємо колір через 160мс
            self.after(160, lambda: self.highlight_keyboard_key(self.target_char) if self.target_char else self.kbd_canvas.itemconfig(data["rect"], fill=data["base_color"], outline="#94A3B8", width=1.5))

    def update_finger_hint(self, char):
        char_key = char.upper()
        finger_dict = FINGER_NAMES_UA if self.lang == "UA" else FINGER_NAMES_EN
        if char_key in self.key_rects:
            finger_code = self.key_rects[char_key]["finger"]
            finger_name = finger_dict.get(finger_code, "")
            self.finger_hint_label.configure(
                text=f"👉 Палець: {finger_name}", fg="#0369A1"
            )
        else:
            self.finger_hint_label.configure(text="👉 Натискай потрібну клавішу", fg="#1E293B")

    # --- ОБРОБНИК НАТИСКАННЯ КЛАВІШ ---
    def handle_key_press(self, event):
        # Якщо відкрито діалог або поле введення - не перехоплювати
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return

        typed_raw = event.char
        keysym = event.keysym

        # Обробка пробілу
        if keysym == "space":
            typed = " "
            display_typed = "ПРОБІЛ"
        elif typed_raw:
            typed = typed_raw
            display_typed = typed.upper()
        else:
            return

        self.session_typed += 1
        self.student_data["total_typed"] += 1

        # Обробка за режимами
        if self.mode == "letters":
            self.process_letters_input(display_typed)
        elif self.mode == "words":
            self.process_words_input(typed)
        elif self.mode == "arcade":
            self.process_arcade_input(display_typed)
        elif self.mode == "sentences":
            self.process_sentences_input(typed)

    def process_letters_input(self, typed):
        target = self.target_char.upper()
        if typed == target:
            # ПРАВИЛЬНО!
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.streak += 1
            self.student_data["stars"] += 1
            self.student_data["score"] += 10 + (self.streak * 2)

            self.flash_key(target, True)
            if self.streak % 10 == 0:
                self.sound.play("streak")
                self.feedback_label.configure(text=f"🔥 СУПЕР! Серія {self.streak}! 🔥", fg="#EA580C")
            else:
                self.sound.play("correct")
                praises = ["Молодець! 👏", "Чудово! 🌟", "Так тримати! 🚀", "Точно в ціль! 🎯"]
                self.feedback_label.configure(text=random.choice(praises), fg="#16A34A")

            self.streak_label.configure(text=f"🔥 Серія: {self.streak}")
            self.update_stats_display()
            self.next_letter()
        else:
            # НЕПРАВИЛЬНО
            self.streak = 0
            self.streak_label.configure(text="🔥 Серія: 0")
            self.sound.play("wrong")
            self.flash_key(typed, False)
            self.feedback_label.configure(
                text=f"Спробуй ще! Потрібна '{target}', а натиснуто '{typed}'", fg="#DC2626"
            )

    def process_words_input(self, typed):
        if self.word_index >= len(self.target_word):
            return

        expected = self.target_word[self.word_index]
        if typed.upper() == expected.upper():
            # Правильна літера в слові
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.sound.play("correct")
            self.flash_key(expected, True)

            # Зелений колір на картці літери
            self.word_char_labels[self.word_index].configure(
                bg="#BBF7D0", fg="#166534", bd=1, relief="solid"
            )
            self.word_index += 1
            self.update_word_highlight()
        else:
            self.sound.play("wrong")
            self.flash_key(typed, False)
            self.word_feedback_label.configure(
                text=f"Увага! Натисни '{expected}', а не '{typed.upper()}'", fg="#DC2626"
            )

    def process_arcade_input(self, typed):
        if not self.arcade_running:
            return

        # Знаходимо найнижчий метеорит з такою літерою
        matched_item = None
        highest_y = -999
        for item in self.arcade_items:
            if item["char"].upper() == typed:
                if item["y"] > highest_y:
                    highest_y = item["y"]
                    matched_item = item

        if matched_item:
            # Збили зірку!
            self.sound.play("correct")
            self.flash_key(typed, True)
            self.arcade_items.remove(matched_item)
            self.arcade_canvas.delete(matched_item["tag"])
            self.arcade_score += 15
            self.arcade_score_lbl.configure(text=f"Бали: {self.arcade_score}")
        else:
            self.sound.play("wrong")
            self.flash_key(typed, False)

    def process_sentences_input(self, typed):
        if self.sentence_index >= len(self.target_sentence):
            return

        expected = self.target_sentence[self.sentence_index]
        # Для речень враховуємо регістр або підтримуємо простий ввід
        is_match = (typed == expected) or (typed.lower() == expected.lower())
        if is_match:
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.sound.play("correct")
            self.sentence_index += 1
            self.render_sentence_text()
        else:
            self.sound.play("wrong")
            self.sent_feedback.configure(
                text=f"Потрібно: '{expected}', натиснуто: '{typed}'", fg="#DC2626"
            )

    # --- ДІАЛОГИ ТА НАЛАШТУВАННЯ ---
    def toggle_language(self):
        self.lang = "EN" if self.lang == "UA" else "UA"
        flag_text = "🇬🇧 Eng" if self.lang == "EN" else "🇺🇦 Укр"
        self.lang_btn.configure(text=flag_text)
        self.selected_level_index = 0
        self.select_mode(self.mode)

    def toggle_sound(self):
        is_on = self.sound.toggle()
        self.progress.data["sound_enabled"] = is_on
        self.sound_btn.configure(
            text="🔊" if is_on else "🔇",
            bg="#16A34A" if is_on else "#94A3B8"
        )
        self.progress.save()

    def update_stats_display(self):
        total = self.student_data["total_typed"]
        correct = self.student_data["correct_typed"]
        accuracy = int((correct / total * 100)) if total > 0 else 100
        stars = self.student_data.get("stars", 0)
        self.stats_label.configure(text=f"Зірочки: ⭐ {stars}  |  Точність: {accuracy}%")
        self.progress.save()

    def change_avatar_dialog(self):
        win = tk.Toplevel(self)
        win.title("Обери свою аватарку")
        win.geometry("340x220")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Вибери улюбленого героя:", font=("Segoe UI", 12, "bold")).pack(pady=10)

        grid_frame = tk.Frame(win)
        grid_frame.pack(pady=5)

        avatars = ["🚀", "🐱", "🐶", "🦁", "🐼", "🦄", "🦊", "🤖"]
        for idx, av in enumerate(avatars):
            btn = tk.Button(
                grid_frame, text=av, font=("Segoe UI Emoji", 20),
                width=3, height=1, relief="ridge", bd=2, cursor="hand2",
                command=lambda a=av: self.set_avatar(a, win)
            )
            btn.grid(row=idx // 4, column=idx % 4, padx=6, pady=6)

    def set_avatar(self, av, win):
        self.current_avatar = av
        self.student_data["avatar"] = av
        self.avatar_btn.configure(text=av)
        self.progress.save()
        win.destroy()

    def change_name_dialog(self):
        win = tk.Toplevel(self)
        win.title("Ім'я учня")
        win.geometry("320x160")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Введіть ім'я учня:", font=("Segoe UI", 11, "bold")).pack(pady=10)
        entry = tk.Entry(win, font=("Segoe UI", 12), justify="center")
        entry.insert(0, self.current_student_name)
        entry.pack(pady=5, padx=20, fill="x")
        entry.focus_set()

        def save_name():
            new_name = entry.get().strip()
            if new_name:
                self.current_student_name = new_name
                self.progress.data["last_student"] = new_name
                self.student_data = self.progress.get_student(new_name, self.current_avatar)
                self.name_label.configure(text=new_name)
                self.avatar_btn.configure(text=self.student_data.get("avatar", "🚀"))
                self.update_stats_display()
                self.progress.save()
            win.destroy()

        save_btn = tk.Button(
            win, text="Зберегти", font=("Segoe UI", 10, "bold"),
            bg="#2563EB", fg="white", relief="flat", padx=15, pady=4,
            command=save_name
        )
        save_btn.pack(pady=10)
        entry.bind("<Return>", lambda e: save_name())

    def show_records_window(self):
        win = tk.Toplevel(self)
        win.title("🏆 Таблиця досягнень")
        win.geometry("450x380")
        win.resizable(False, False)

        tk.Label(
            win, text="🌟 Досягнення наших учнів 🌟",
            font=("Segoe UI", 14, "bold"), fg="#1E293B"
        ).pack(pady=10)

        tree_frame = tk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("name", "stars", "accuracy", "arcade")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        tree.heading("name", text="Учень")
        tree.heading("stars", text="⭐ Зірочки")
        tree.heading("accuracy", text="🎯 Точність")
        tree.heading("arcade", text="☄️ Рекорд гри")

        tree.column("name", width=140)
        tree.column("stars", width=70, anchor="center")
        tree.column("accuracy", width=80, anchor="center")
        tree.column("arcade", width=90, anchor="center")

        students = self.progress.data.get("students", {})
        for s_name, s_info in students.items():
            tot = s_info.get("total_typed", 0)
            cor = s_info.get("correct_typed", 0)
            acc = f"{int(cor / tot * 100)}%" if tot > 0 else "100%"
            stars = s_info.get("stars", 0)
            arc = s_info.get("best_arcade_score", 0)
            av = s_info.get("avatar", "🚀")
            tree.insert("", "end", values=(f"{av} {s_name}", stars, acc, arc))

        tree.pack(fill="both", expand=True)

        tk.Button(
            win, text="Закрити", font=("Segoe UI", 10, "bold"),
            bg="#64748B", fg="white", relief="flat", padx=15, pady=4,
            command=win.destroy
        ).pack(pady=10)


if __name__ == "__main__":
    app = KidsKeyboardTrainer()
    app.mainloop()
