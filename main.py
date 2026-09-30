# -*- coding: utf-8 -*-
"""
Клавіатурний тренажер для дітей "Спритні пальчики" / "Smart Fingers"
Розроблено спеціально для легкого навчання сліпому друку та гарячим клавішам.
Повністю автономний застосунок: працює на будь-якому ПК без встановленого Python.
"""

import sys
import os
import json
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
                elif sound_type == "hotkey_down":
                    winsound.Beep(440, 40)
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
                "hotkeys_mastered": 0,
                "achievements": []
            }
            self.save()
        return self.data["students"][name]


# --- Словники, навчальні набори та каталог гарячих клавіш ---
HOTKEYS_DATA = {
    "UA": [
        {
            "id": "ctrl_c",
            "keys": ["Ctrl", "C"],
            "keycodes": [67],
            "title": "Копіювати (запам'ятати)",
            "emoji": "📋",
            "desc": "Копіює виділений текст, картинку чи файл у пам'ять (буфер обміну).",
            "finger": "Ліва рука: мізинець на [Ctrl], вказівний на [C] (або укр. С)",
            "quiz_question": "Яка комбінація копіює виділений текст у пам'ять комп'ютера?",
            "sample_text": "🐱 Веселий Котик 🌟"
        },
        {
            "id": "ctrl_v",
            "keys": ["Ctrl", "V"],
            "keycodes": [86],
            "title": "Вставити (розмістити скопійоване)",
            "emoji": "📥",
            "desc": "Вставляє скопійований раніше текст чи картинку в нове місце.",
            "finger": "Ліва рука: мізинець на [Ctrl], вказівний на [V] (або укр. М)",
            "quiz_question": "Яка комбінація вставляє раніше скопійований текст?",
            "sample_text": "🚀 Космічна Ракета 🌠"
        },
        {
            "id": "ctrl_z",
            "keys": ["Ctrl", "Z"],
            "keycodes": [90],
            "title": "Чарівне скасування (Undo)",
            "emoji": "↩️",
            "desc": "Виправляє будь-яку випадкову помилку! Повертає дію назад.",
            "finger": "Ліва рука: мізинець на [Ctrl], безіменний на [Z] (або укр. Я)",
            "quiz_question": "Випадково видалили текст? Яка чарівна комбінація поверне все назад?",
            "sample_text": "🎨 Чарівний малюнок"
        },
        {
            "id": "ctrl_y",
            "keys": ["Ctrl", "Y"],
            "keycodes": [89],
            "title": "Повторити дію (Redo)",
            "emoji": "🔁",
            "desc": "Повторює дію, якщо ви скасували її занадто далеко.",
            "finger": "Ліва рука: мізинець на [Ctrl], права: вказівний на [Y] (укр. Н)",
            "quiz_question": "Яка комбінація повторює щойно скасовану дію?",
            "sample_text": "⚡ Швидка блискавка"
        },
        {
            "id": "ctrl_s",
            "keys": ["Ctrl", "S"],
            "keycodes": [83],
            "title": "Зберегти файл",
            "emoji": "💾",
            "desc": "Зберігає документ або малюнок, щоб нічого не загубилося.",
            "finger": "Ліва рука: мізинець на [Ctrl], безіменний на [S] (або укр. І)",
            "quiz_question": "Яка комбінація зберігає файл, малюнок або гру?",
            "sample_text": "📚 Моя цікава казка"
        },
        {
            "id": "ctrl_a",
            "keys": ["Ctrl", "A"],
            "keycodes": [65],
            "title": "Виділити все одразу",
            "emoji": "✨",
            "desc": "Виділяє весь текст на сторінці або всі файли в папці за одну секунду.",
            "finger": "Ліва рука: мізинець на [Ctrl], безіменний на [A] (або укр. Ф)",
            "quiz_question": "Як виділити весь текст або всі файли одразу?",
            "sample_text": "🌟 Усі слова на сторінці разом"
        },
        {
            "id": "ctrl_f",
            "keys": ["Ctrl", "F"],
            "keycodes": [70],
            "title": "Швидкий пошук",
            "emoji": "🔍",
            "desc": "Відкриває віконце пошуку слова на сторінці, у книзі чи в браузері.",
            "finger": "Ліва рука: мізинець на [Ctrl], вказівний на [F] (або укр. А)",
            "quiz_question": "Як швидко знайти потрібне слово у великому тексті чи в інтернеті?",
            "sample_text": "🔎 Шукаю секретний скарб"
        },
        {
            "id": "ctrl_x",
            "keys": ["Ctrl", "X"],
            "keycodes": [88],
            "title": "Вирізати (Cut)",
            "emoji": "✂️",
            "desc": "Забирає виділений фрагмент, щоб перенести його в інше місце.",
            "finger": "Ліва рука: мізинець на [Ctrl], середній на [X] (або укр. Ч)",
            "quiz_question": "Як вирізати текст чи малюнок для перенесення в інше місце?",
            "sample_text": "✂️ Відрізаний шматочок"
        },
        {
            "id": "win_d",
            "keys": ["Win", "D"],
            "keycodes": [68],
            "title": "Показати робочий стіл",
            "emoji": "🖥️",
            "desc": "Миттєво згортає всі вікна та показує чистий робочий стіл.",
            "finger": "Ліва рука: великий палець на [Win], середній на [D] (або укр. В)",
            "quiz_question": "Як в 1 клік згорнути всі вікна та відкрити робочий стіл?",
            "sample_text": "🖥️ Мій чистий екран"
        },
        {
            "id": "alt_tab",
            "keys": ["Alt", "Tab"],
            "keycodes": [9],
            "title": "Швидке перемикання вікон",
            "emoji": "🔀",
            "desc": "Дозволяє миттєво перемикатися між відкритими програмами.",
            "finger": "Ліва рука: великий на [Alt], мізинець на [Tab]",
            "quiz_question": "Яка комбінація дозволяє швидко перемикатися між відкритими вікнами?",
            "sample_text": "🔀 Перехід до іншої гри"
        },
        {
            "id": "ctrl_t",
            "keys": ["Ctrl", "T"],
            "keycodes": [84],
            "title": "Нова вкладка в інтернеті",
            "emoji": "🌐",
            "desc": "Відкриває нову чисту вкладку у браузері для пошуку чогось нового.",
            "finger": "Ліва рука: мізинець на [Ctrl], вказівний на [T] (або укр. Е)",
            "quiz_question": "Як у браузері відкрити нову вкладку для пошуку?",
            "sample_text": "🌐 Нова сторінка в інтернеті"
        },
        {
            "id": "ctrl_w",
            "keys": ["Ctrl", "W"],
            "keycodes": [87],
            "title": "Закрити поточну вкладку",
            "emoji": "✖️",
            "desc": "Закриває одну непотрібну вкладку у браузері.",
            "finger": "Ліва рука: мізинець на [Ctrl], безіменний на [W] (або укр. Ц)",
            "quiz_question": "Як швидко закрити поточну вкладку в інтернеті?",
            "sample_text": "✖️ Непотрібна вкладка"
        }
    ],
    "EN": [
        {
            "id": "ctrl_c",
            "keys": ["Ctrl", "C"],
            "keycodes": [67],
            "title": "Copy (Copy to clipboard)",
            "emoji": "📋",
            "desc": "Copies selected text, image or file into computer memory.",
            "finger": "Left hand: pinky on [Ctrl], index on [C]",
            "quiz_question": "Which shortcut copies selected text to clipboard?",
            "sample_text": "🐱 Cute Kitty Cat 🌟"
        },
        {
            "id": "ctrl_v",
            "keys": ["Ctrl", "V"],
            "keycodes": [86],
            "title": "Paste (Paste copied item)",
            "emoji": "📥",
            "desc": "Pastes the copied text or picture into the target place.",
            "finger": "Left hand: pinky on [Ctrl], index on [V]",
            "quiz_question": "Which shortcut pastes previously copied text?",
            "sample_text": "🚀 Space Rocket 🌠"
        },
        {
            "id": "ctrl_z",
            "keys": ["Ctrl", "Z"],
            "keycodes": [90],
            "title": "Magic Undo",
            "emoji": "↩️",
            "desc": "Fixes mistakes by undoing your last action!",
            "finger": "Left hand: pinky on [Ctrl], ring on [Z]",
            "quiz_question": "Accidentally deleted something? Which magic shortcut brings it back?",
            "sample_text": "🎨 Magic art piece"
        },
        {
            "id": "ctrl_s",
            "keys": ["Ctrl", "S"],
            "keycodes": [83],
            "title": "Save file",
            "emoji": "💾",
            "desc": "Saves your document or drawing so nothing is lost.",
            "finger": "Left hand: pinky on [Ctrl], ring on [S]",
            "quiz_question": "Which shortcut saves your document or artwork?",
            "sample_text": "📚 My fairy tale"
        },
        {
            "id": "ctrl_a",
            "keys": ["Ctrl", "A"],
            "keycodes": [65],
            "title": "Select All",
            "emoji": "✨",
            "desc": "Selects all text or files in a folder instantly.",
            "finger": "Left hand: pinky on [Ctrl], ring on [A]",
            "quiz_question": "How do you select all text or files at once?",
            "sample_text": "🌟 All words on the page"
        },
        {
            "id": "ctrl_f",
            "keys": ["Ctrl", "F"],
            "keycodes": [70],
            "title": "Quick Find",
            "emoji": "🔍",
            "desc": "Opens search box to find any word on web page or doc.",
            "finger": "Left hand: pinky on [Ctrl], index on [F]",
            "quiz_question": "Which shortcut helps you find words quickly?",
            "sample_text": "🔎 Finding treasure"
        },
        {
            "id": "win_d",
            "keys": ["Win", "D"],
            "keycodes": [68],
            "title": "Show Desktop",
            "emoji": "🖥️",
            "desc": "Minimizes all windows and shows your clean desktop.",
            "finger": "Left hand: thumb on [Win], middle on [D]",
            "quiz_question": "How to minimize all windows and show desktop in 1 click?",
            "sample_text": "🖥️ Desktop view"
        },
        {
            "id": "alt_tab",
            "keys": ["Alt", "Tab"],
            "keycodes": [9],
            "title": "Switch Windows",
            "emoji": "🔀",
            "desc": "Instantly switch between your opened applications.",
            "finger": "Left hand: thumb on [Alt], pinky on [Tab]",
            "quiz_question": "Which shortcut switches between open application windows?",
            "sample_text": "🔀 Switch to next app"
        }
    ]
}

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

# Кольори пальців
FINGER_COLORS = {
    "LP": "#FFB3BA",  # Лівий мізинець (Pink)
    "LR": "#FFDFBA",  # Лівий безіменний (Peach)
    "LM": "#FFFFBA",  # Лівий середній (Light Yellow)
    "LI": "#BAFFC9",  # Лівий вказівний (Mint)
    "RI": "#BAE1FF",  # Правий вказівний (Sky Blue)
    "RM": "#C7CEEA",  # Правий середній (Periwinkle)
    "RR": "#E2BAFF",  # Правий безіменний (Lavender)
    "RP": "#FFBAEC",  # Правий мізинець (Rose)
    "TH": "#E2ECE9",  # Великі пальці (Пробіл)
    "MOD": "#D8B4FE"  # Модифікатори Ctrl/Alt/Win/Shift
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
    "TH": "Великий палець (Пробіл)",
    "MOD": "Пальчик на модифікаторі"
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
    "TH": "Thumb (Spacebar)",
    "MOD": "Modifier Finger"
}

# Повна реалістична розкладка з Ctrl, Alt, Win, Shift для навчання гарячим клавішам
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
        [("Shift", "MOD", 1.4), ("Я", "LP"), ("Ч", "LR"), ("С", "LM"), ("М", "LI"), ("И", "LI"),
         ("Т", "RI"), ("Ь", "RI"), ("Б", "RM"), ("Ю", "RR"), (".", "RP"), (",", "RP"), ("Shift", "MOD", 1.4)],
        # Ряд 4 (Модифікатори та Пробіл)
        [("Ctrl", "MOD", 1.4), ("Win", "MOD", 1.1), ("Alt", "MOD", 1.1),
         ("ПРОБІЛ", "TH", 5.2),
         ("Alt", "MOD", 1.1), ("Win", "MOD", 1.1), ("Ctrl", "MOD", 1.4)]
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
        [("Shift", "MOD", 1.4), ("Z", "LP"), ("X", "LR"), ("C", "LM"), ("V", "LI"), ("B", "LI"),
         ("N", "RI"), ("M", "RI"), (",", "RM"), (".", "RR"), ("/", "RP"), ("Shift", "MOD", 1.4)],
        # Row 4 (Modifiers & Spacebar)
        [("Ctrl", "MOD", 1.4), ("Win", "MOD", 1.1), ("Alt", "MOD", 1.1),
         ("SPACE", "TH", 5.2),
         ("Alt", "MOD", 1.1), ("Win", "MOD", 1.1), ("Ctrl", "MOD", 1.4)]
    ]
}


class KidsKeyboardTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Клавіатурний тренажер для дітей • Спритні пальчики 🚀")
        self.geometry("1020x720")
        self.minsize(920, 660)
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
        self.mode = "letters"  # "letters", "words", "arcade", "sentences", "hotkeys"
        self.current_student_name = self.progress.data.get("last_student", "Юний Чемпіон")
        self.current_avatar = "🚀"
        self.student_data = self.progress.get_student(self.current_student_name, self.current_avatar)

        # Ігрові змінні
        self.target_chars = []  # список активних літер для підсвічування
        self.target_char = ""
        self.target_word = ""
        self.word_index = 0
        self.current_emoji = "⭐️"
        self.selected_level_index = 0
        self.streak = 0
        self.session_typed = 0
        self.session_correct = 0

        # Змінні режиму гарячих клавіш
        self.hotkeys_submode = "practice"  # "practice", "quiz", "handbook"
        self.current_hotkey_idx = 0
        self.ctrl_held = False
        self.alt_held = False
        self.shift_held = False
        self.win_held = False

        # Змінні режиму "Падаючі літери" (Аркада)
        self.arcade_running = False
        self.arcade_items = []
        self.arcade_score = 0
        self.arcade_lives = 3

        # Створення компонентів інтерфейсу
        self.build_ui()
        self.select_mode("letters")

        # Слухачі клавіатури (натискання та відпускання)
        self.bind("<KeyPress>", self.handle_key_down)
        self.bind("<KeyRelease>", self.handle_key_up)

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

        # Центр шапки: Назва
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
            ("hotkeys", "⚡ Гарячі клавіші"),
            ("arcade", "☄️ Падаючі літери"),
            ("sentences", "📖 Речення")
        ]

        for m_id, m_text in modes:
            btn = tk.Button(
                mode_bar, text=m_text, font=("Segoe UI", 10, "bold"),
                bg="#E2E8F0", fg="#475569", bd=0, relief="flat", padx=14, pady=8,
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

        self.key_rects = {}  # { char: [ {rect, text, base_color, finger} ] }

        # Оновлення статистики
        self.update_stats_display()

    # --- Зміна режимів навчання ---
    def select_mode(self, mode_id):
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
        elif mode_id == "hotkeys":
            self.setup_hotkeys_view()
        elif mode_id == "arcade":
            self.setup_arcade_view()
        elif mode_id == "sentences":
            self.setup_sentences_view()

        self.draw_keyboard()

    # --- РЕЖИМ 1: ЛІТЕРИ ТА РЯДИ ---
    def setup_letters_view(self):
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
        new_char = random.choice(chars)
        while len(chars) > 1 and new_char == self.target_char:
            new_char = random.choice(chars)

        self.target_char = new_char
        self.target_chars = [new_char]
        self.big_char_label.configure(text=self.target_char, fg="#2563EB")
        self.update_finger_hint(self.target_char)
        self.highlight_keyboard_keys(self.target_chars)

    # --- РЕЖИМ 2: ВЕСЕЛІ СЛОВА З ЕМОДЗІ ---
    def setup_words_view(self):
        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

        self.word_emoji_label = tk.Label(
            card, text="🐱", font=("Segoe UI Emoji", 54),
            bg="#FFFFFF"
        )
        self.word_emoji_label.pack(pady=(15, 0))

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

        for lbl in self.word_char_labels:
            lbl.destroy()
        self.word_char_labels = []

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
            self.target_chars = [curr_char]
            self.word_char_labels[self.word_index].configure(
                bg="#FEF08A", fg="#854D0E", relief="ridge", bd=2
            )
            self.update_finger_hint(curr_char)
            self.highlight_keyboard_keys(self.target_chars)
            self.word_feedback_label.configure(
                text=f"Наступна літера: '{curr_char}'", fg="#3B82F6"
            )
        else:
            self.target_char = ""
            self.target_chars = []
            self.sound.play("complete")
            self.student_data["stars"] += 2
            self.student_data["words_typed"] += 1
            self.update_stats_display()
            self.word_feedback_label.configure(
                text="🎉 Чудово! Слово зібрано! +2 ⭐", fg="#16A34A"
            )
            self.after(900, self.next_word)

    # --- РЕЖИМ 3: ГАРЯЧІ КЛАВІШІ (HOTKEYS) ---
    def setup_hotkeys_view(self):
        # Верхня панель підрежимів гарячих клавіш
        sub_bar = tk.Frame(self.work_area, bg="#EEF2F6")
        sub_bar.pack(fill="x", pady=(0, 6))

        submodes = [
            ("practice", "🎯 Тренажер комбінацій"),
            ("quiz", "❓ Вікторина знавця"),
            ("handbook", "📚 Довідник гарячих клавіш")
        ]

        self.hotkey_submode_btns = {}
        for sm_id, sm_title in submodes:
            btn = tk.Button(
                sub_bar, text=sm_title, font=("Segoe UI", 9, "bold"),
                bg="#FFFFFF" if sm_id == self.hotkeys_submode else "#E2E8F0",
                fg="#2563EB" if sm_id == self.hotkeys_submode else "#475569",
                relief="groove" if sm_id == self.hotkeys_submode else "flat",
                padx=12, pady=4, cursor="hand2",
                command=lambda sid=sm_id: self.switch_hotkeys_submode(sid)
            )
            btn.pack(side="left", padx=4)
            self.hotkey_submode_btns[sm_id] = btn

        self.hotkeys_content_area = tk.Frame(self.work_area, bg="#EEF2F6")
        self.hotkeys_content_area.pack(fill="both", expand=True)

        if self.hotkeys_submode == "practice":
            self.render_hotkeys_practice()
        elif self.hotkeys_submode == "quiz":
            self.render_hotkeys_quiz()
        elif self.hotkeys_submode == "handbook":
            self.render_hotkeys_handbook()

    def switch_hotkeys_submode(self, submode_id):
        self.hotkeys_submode = submode_id
        for sid, btn in self.hotkey_submode_btns.items():
            if sid == submode_id:
                btn.configure(bg="#FFFFFF", fg="#2563EB", relief="groove")
            else:
                btn.configure(bg="#E2E8F0", fg="#475569", relief="flat")

        for w in self.hotkeys_content_area.winfo_children():
            w.destroy()

        if submode_id == "practice":
            self.render_hotkeys_practice()
        elif submode_id == "quiz":
            self.render_hotkeys_quiz()
        elif submode_id == "handbook":
            self.render_hotkeys_handbook()

    def render_hotkeys_practice(self):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        if self.current_hotkey_idx >= len(hotkeys_list):
            self.current_hotkey_idx = 0
        hk = hotkeys_list[self.current_hotkey_idx]

        card = tk.Frame(self.hotkeys_content_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

        # Селектор та навігація зверху картки
        nav_frame = tk.Frame(card, bg="#FFFFFF")
        nav_frame.pack(fill="x", padx=15, pady=(8, 4))

        tk.Button(
            nav_frame, text="⬅️ Попередня", font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9", fg="#334155", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.prev_hotkey
        ).pack(side="left")

        # Комбобокс вибору комбінації
        hk_names = [f"{item['emoji']} {' + '.join(item['keys'])} : {item['title']}" for item in hotkeys_list]
        self.hk_select_var = tk.StringVar(value=hk_names[self.current_hotkey_idx])
        hk_combo = ttk.Combobox(
            nav_frame, textvariable=self.hk_select_var, values=hk_names,
            state="readonly", width=42, font=("Segoe UI", 9)
        )
        hk_combo.pack(side="left", padx=10)
        hk_combo.bind("<<ComboboxSelected>>", self.on_hotkey_combo_selected)

        tk.Button(
            nav_frame, text="Наступна ➡️", font=("Segoe UI", 9, "bold"),
            bg="#2563EB", fg="white", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.next_hotkey
        ).pack(side="right")

        # Візуалізація великих клавіш комбінації
        keys_display_frame = tk.Frame(card, bg="#FFFFFF")
        keys_display_frame.pack(pady=(10, 4))

        for idx, k in enumerate(hk["keys"]):
            if idx > 0:
                tk.Label(
                    keys_display_frame, text="+", font=("Segoe UI", 26, "bold"),
                    bg="#FFFFFF", fg="#94A3B8"
                ).pack(side="left", padx=8)

            badge = tk.Label(
                keys_display_frame, text=f" {k} ", font=("Segoe UI", 22, "bold"),
                bg="#E0E7FF", fg="#3730A3", bd=2, relief="solid", padx=12, pady=4
            )
            badge.pack(side="left", padx=4)

        # Опис та призначення
        tk.Label(
            card, text=f"{hk['emoji']} {hk['title']}",
            font=("Segoe UI", 15, "bold"), bg="#FFFFFF", fg="#1E293B"
        ).pack(pady=(4, 2))

        tk.Label(
            card, text=hk["desc"],
            font=("Segoe UI", 11), bg="#FFFFFF", fg="#64748B"
        ).pack(pady=(0, 6))

        # Панель статусу натискання в реальному часі
        self.hk_status_box = tk.Frame(card, bg="#FEF3C7", bd=1, relief="solid")
        self.hk_status_box.pack(fill="x", padx=40, pady=4)

        self.hk_status_label = tk.Label(
            self.hk_status_box, text=f"⏳ Затисни клавішу [{hk['keys'][0]}] лівою рукою...",
            font=("Segoe UI", 12, "bold"), bg="#FEF3C7", fg="#B45309", pady=6
        )
        self.hk_status_label.pack()

        # Міні-пісочниця (Інтерактивне поле для випробування дії)
        sandbox_frame = tk.Frame(card, bg="#F8FAFC", bd=1, relief="ridge")
        sandbox_frame.pack(fill="x", padx=40, pady=(6, 8))

        tk.Label(
            sandbox_frame, text="🧪 Інтерактивне поле для перевірки:",
            font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg="#475569"
        ).pack(anchor="w", padx=10, pady=(4, 2))

        sand_inner = tk.Frame(sandbox_frame, bg="#F8FAFC")
        sand_inner.pack(fill="x", padx=10, pady=(0, 6))

        tk.Label(sand_inner, text="Зразок:", font=("Segoe UI", 9), bg="#F8FAFC", fg="#64748B").pack(side="left")
        sample_entry = tk.Entry(sand_inner, font=("Segoe UI", 10), width=24)
        sample_entry.insert(0, hk["sample_text"])
        sample_entry.pack(side="left", padx=5)

        tk.Label(sand_inner, text="Сюди встав:", font=("Segoe UI", 9), bg="#F8FAFC", fg="#64748B").pack(side="left", padx=(10, 0))
        target_entry = tk.Entry(sand_inner, font=("Segoe UI", 10), width=24)
        target_entry.pack(side="left", padx=5)

        # Оновлення підсвічування на віртуальній клавіатурі
        self.update_hotkey_keyboard_guidance(hk)

    def on_hotkey_combo_selected(self, event=None):
        val = self.hk_select_var.get()
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        for idx, item in enumerate(hotkeys_list):
            if item["title"] in val:
                self.current_hotkey_idx = idx
                break
        self.switch_hotkeys_submode("practice")

    def prev_hotkey(self):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        self.current_hotkey_idx = (self.current_hotkey_idx - 1) % len(hotkeys_list)
        self.switch_hotkeys_submode("practice")

    def next_hotkey(self):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        self.current_hotkey_idx = (self.current_hotkey_idx + 1) % len(hotkeys_list)
        self.switch_hotkeys_submode("practice")

    def update_hotkey_keyboard_guidance(self, hk):
        # Підсвічуємо всі клавіші, які входять у комбінацію
        keys_to_highlight = [k.upper() for k in hk["keys"]]
        self.target_chars = keys_to_highlight
        self.finger_hint_label.configure(
            text=f"👉 {hk['finger']}", fg="#4338CA"
        )
        self.highlight_keyboard_keys(self.target_chars)

    # Вікторина гарячих клавіш (Quiz)
    def render_hotkeys_quiz(self):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        # Обираємо випадкове питання
        q_item = random.choice(hotkeys_list)
        self.current_quiz_target = q_item

        card = tk.Frame(self.hotkeys_content_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

        tk.Label(
            card, text="🏆 Вікторина супергероя клавіатури! 🌟",
            font=("Segoe UI", 15, "bold"), bg="#FFFFFF", fg="#2563EB"
        ).pack(pady=(12, 4))

        tk.Label(
            card, text=q_item["quiz_question"],
            font=("Segoe UI", 13, "bold"), bg="#FFFFFF", fg="#1E293B", wraplength=700
        ).pack(pady=(6, 12))

        # Формуємо 4 варіанти відповідей (1 правильний і 3 неправильних)
        distractors = [x for x in hotkeys_list if x["id"] != q_item["id"]]
        random.shuffle(distractors)
        options = [q_item] + distractors[:3]
        random.shuffle(options)

        options_frame = tk.Frame(card, bg="#FFFFFF")
        options_frame.pack(expand=True, pady=5)

        colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"]
        for idx, opt in enumerate(options):
            combo_str = " + ".join(opt["keys"])
            btn_text = f"{opt['emoji']}  {combo_str}\n({opt['title']})"
            btn = tk.Button(
                options_frame, text=btn_text, font=("Segoe UI", 11, "bold"),
                bg=colors[idx % len(colors)], fg="white", width=26, height=3,
                relief="flat", cursor="hand2", bd=0,
                command=lambda chosen=opt: self.check_quiz_answer(chosen, q_item)
            )
            btn.grid(row=idx // 2, column=idx % 2, padx=12, pady=8)

        self.quiz_feedback = tk.Label(
            card, text="Обери правильну комбінацію мишкою або натисни її на клавіатурі!",
            font=("Segoe UI", 11), bg="#FFFFFF", fg="#64748B"
        )
        self.quiz_feedback.pack(pady=(4, 10))

        # Підсвічуємо на клавіатурі правильну відповідь як підказку для навчання
        self.target_chars = [k.upper() for k in q_item["keys"]]
        self.finger_hint_label.configure(text=f"👉 Підказка: {q_item['finger']}", fg="#4338CA")
        self.highlight_keyboard_keys(self.target_chars)

    def check_quiz_answer(self, chosen, correct):
        if chosen["id"] == correct["id"]:
            self.sound.play("complete")
            self.student_data["stars"] += 3
            self.student_data["hotkeys_mastered"] += 1
            self.update_stats_display()
            self.quiz_feedback.configure(
                text=f"🎉 ПРАВИЛЬНО! Ти справжній майстер гарячих клавіш! +3 ⭐", fg="#16A34A"
            )
            self.after(1200, lambda: self.render_hotkeys_quiz() if self.hotkeys_submode == "quiz" else None)
        else:
            self.sound.play("wrong")
            self.quiz_feedback.configure(
                text=f"Спробуй ще! Правильна відповідь була: {' + '.join(correct['keys'])}", fg="#DC2626"
            )

    # Довідник гарячих клавіш (Handbook)
    def render_hotkeys_handbook(self):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])

        container = tk.Frame(self.hotkeys_content_area, bg="#FFFFFF", bd=2, relief="ridge")
        container.pack(fill="both", expand=True, pady=4)

        canvas = tk.Canvas(container, bg="#FFFFFF", bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg="#FFFFFF")

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        tk.Label(
            scroll_content, text="📚 Повний довідник корисних гарячих клавіш для дітей 🚀",
            font=("Segoe UI", 13, "bold"), bg="#FFFFFF", fg="#1E293B"
        ).pack(anchor="w", padx=15, pady=(10, 8))

        for hk in hotkeys_list:
            row_frame = tk.Frame(scroll_content, bg="#F8FAFC", bd=1, relief="solid")
            row_frame.pack(fill="x", expand=True, padx=15, pady=4)

            badge_text = " + ".join(hk["keys"])
            badge = tk.Label(
                row_frame, text=badge_text, font=("Segoe UI", 11, "bold"),
                bg="#E0E7FF", fg="#3730A3", width=14, pady=4
            )
            badge.pack(side="left", padx=8, pady=6)

            info_frame = tk.Frame(row_frame, bg="#F8FAFC")
            info_frame.pack(side="left", fill="both", expand=True, padx=6)

            tk.Label(
                info_frame, text=f"{hk['emoji']} {hk['title']}",
                font=("Segoe UI", 11, "bold"), bg="#F8FAFC", fg="#0F172A"
            ).pack(anchor="w")

            tk.Label(
                info_frame, text=hk["desc"] + " | " + hk["finger"],
                font=("Segoe UI", 9), bg="#F8FAFC", fg="#64748B"
            ).pack(anchor="w")

    # --- РЕЖИМ 4: ПАДАЮЧІ ЛІТЕРИ (АРКАДНА МІНІ-ГРА) ---
    def setup_arcade_view(self):
        card = tk.Frame(self.work_area, bg="#0F172A", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=5)

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
        levels = CONTENT[self.lang]["levels"]
        pool = levels[self.selected_level_index]["chars"]
        char = random.choice(pool)

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

        if self.arcade_running:
            self.after(random.randint(1800, 2600), self.spawn_arcade_char)

    def arcade_loop(self):
        if not self.arcade_running:
            return

        h = self.arcade_canvas.winfo_height() or 300
        to_remove = []
        lowest_item = None
        max_y = -999

        for item in self.arcade_items:
            item["y"] += item["speed"]
            self.arcade_canvas.move(item["tag"], 0, item["speed"])
            if item["y"] > max_y:
                max_y = item["y"]
                lowest_item = item

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
            self.target_chars = [self.target_char]
            self.update_finger_hint(self.target_char)
            self.highlight_keyboard_keys(self.target_chars)
        else:
            self.target_char = ""
            self.target_chars = []

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

    # --- РЕЖИМ 5: РЕЧЕННЯ ---
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

        self.sentence_canvas.create_text(
            30, 35, anchor="w", text=typed_part,
            font=("Consolas", 18, "bold"), fill="#16A34A"
        )

        if curr_char:
            self.target_char = "ПРОБІЛ" if curr_char == " " else curr_char.upper()
            self.target_chars = [self.target_char]
            self.update_finger_hint(self.target_char)
            self.highlight_keyboard_keys(self.target_chars)

            self.sentence_canvas.create_text(
                30, 35, anchor="w",
                text=typed_part + curr_char + rest_part,
                font=("Consolas", 18), fill="#94A3B8"
            )
            self.sentence_canvas.create_text(
                30, 35, anchor="w", text=typed_part,
                font=("Consolas", 18, "bold"), fill="#16A34A"
            )
        else:
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
        row_h = (h - 18) / num_rows
        key_margin = 3

        for r_idx, row in enumerate(layout):
            y1 = 6 + r_idx * row_h
            y2 = y1 + row_h - key_margin

            total_units = sum(item[2] if len(item) > 2 else 1.0 for item in row)
            unit_w = (w - 28) / max(13.8, total_units)

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

                rect_id = self.create_rounded_rect(
                    self.kbd_canvas, x1, y1, x2, y2, radius=7,
                    fill=base_color, outline="#94A3B8", width=1.5
                )

                font_size = 9 if len(char) > 2 else 12
                font_weight = "bold" if len(char) <= 2 else "normal"
                text_id = self.kbd_canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=char, fill="#1E293B", font=("Segoe UI", font_size, font_weight)
                )

                key_data = {
                    "rect": rect_id,
                    "text": text_id,
                    "base_color": base_color,
                    "finger": finger_code
                }
                char_key = char.upper()
                if char_key not in self.key_rects:
                    self.key_rects[char_key] = []
                self.key_rects[char_key].append(key_data)

        if self.target_chars:
            self.highlight_keyboard_keys(self.target_chars)

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

    def highlight_keyboard_keys(self, char_list):
        # Скидаємо всі клавіші до їхніх базових кольорів
        for k_char, data_list in self.key_rects.items():
            for data in data_list:
                self.kbd_canvas.itemconfig(data["rect"], fill=data["base_color"], outline="#94A3B8", width=1.5)

        normalized_list = [c.upper() for c in char_list]
        for c in normalized_list:
            if c in self.key_rects:
                for data in self.key_rects[c]:
                    # Якщо це модифікатор Ctrl/Alt/Shift/Win і він наразі затиснутий
                    is_held = (c == "CTRL" and self.ctrl_held) or (c == "ALT" and self.alt_held) or (c == "SHIFT" and self.shift_held)
                    fill_c = "#4ADE80" if is_held else "#FBBF24"
                    outline_c = "#15803D" if is_held else "#D97706"
                    self.kbd_canvas.itemconfig(data["rect"], fill=fill_c, outline=outline_c, width=3)
                    self.kbd_canvas.tag_raise(data["rect"])
                    self.kbd_canvas.tag_raise(data["text"])

    def flash_key(self, char, is_correct):
        char_key = char.upper()
        if char_key in self.key_rects:
            flash_color = "#4ADE80" if is_correct else "#F87171"
            for data in self.key_rects[char_key]:
                self.kbd_canvas.itemconfig(data["rect"], fill=flash_color, outline="#FFFFFF", width=3)
            self.after(160, lambda: self.highlight_keyboard_keys(self.target_chars))

    def update_finger_hint(self, char):
        char_key = char.upper()
        finger_dict = FINGER_NAMES_UA if self.lang == "UA" else FINGER_NAMES_EN
        if char_key in self.key_rects:
            finger_code = self.key_rects[char_key][0]["finger"]
            finger_name = finger_dict.get(finger_code, "")
            self.finger_hint_label.configure(
                text=f"👉 Палець: {finger_name}", fg="#0369A1"
            )
        else:
            self.finger_hint_label.configure(text="👉 Натискай потрібну клавішу", fg="#1E293B")

    # --- ОБРОБНИКИ НАТИСКАННЯ ТА ВІДПУСКАННЯ КЛАВІШ ---
    def handle_key_down(self, event):
        # Відстеження модифікаторів
        sym = event.keysym
        if sym in ("Control_L", "Control_R"):
            self.ctrl_held = True
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
                return
        elif sym in ("Alt_L", "Alt_R"):
            self.alt_held = True
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
                return
        elif sym in ("Shift_L", "Shift_R"):
            self.shift_held = True
        elif sym in ("Super_L", "Super_R", "Win_L", "Win_R"):
            self.win_held = True

        # Якщо фокус в полі введення - не перехоплювати звичайні клавіші
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return

        typed_raw = event.char
        keysym = event.keysym

        # Перевірка гарячих клавіш
        if self.mode == "hotkeys":
            self.process_hotkeys_input(event)
            return

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

        if self.mode == "letters":
            self.process_letters_input(display_typed)
        elif self.mode == "words":
            self.process_words_input(typed)
        elif self.mode == "arcade":
            self.process_arcade_input(display_typed)
        elif self.mode == "sentences":
            self.process_sentences_input(typed)

    def handle_key_up(self, event):
        sym = event.keysym
        if sym in ("Control_L", "Control_R"):
            self.ctrl_held = False
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
        elif sym in ("Alt_L", "Alt_R"):
            self.alt_held = False
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
        elif sym in ("Shift_L", "Shift_R"):
            self.shift_held = False
        elif sym in ("Super_L", "Super_R", "Win_L", "Win_R"):
            self.win_held = False

    def on_hotkey_modifier_change(self):
        # Оновлення підсвітки при затисканні/відпусканні Ctrl/Alt
        self.highlight_keyboard_keys(self.target_chars)
        if self.hotkeys_submode == "practice" and hasattr(self, "hk_status_label"):
            hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
            hk = hotkeys_list[self.current_hotkey_idx]
            if self.ctrl_held or self.alt_held:
                self.sound.play("hotkey_down")
                self.hk_status_box.configure(bg="#DCFCE7")
                self.hk_status_label.configure(
                    text=f"🟢 Чудово! [{hk['keys'][0]}] затиснуто! Тепер натисни [{hk['keys'][1]}]!",
                    bg="#DCFCE7", fg="#15803D"
                )
            else:
                self.hk_status_box.configure(bg="#FEF3C7")
                self.hk_status_label.configure(
                    text=f"⏳ Затисни клавішу [{hk['keys'][0]}] лівою рукою...",
                    bg="#FEF3C7", fg="#B45309"
                )

    def process_hotkeys_input(self, event):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        if self.hotkeys_submode == "practice":
            hk = hotkeys_list[self.current_hotkey_idx]
            target_key = hk["keys"][1].upper()
            target_keycodes = hk.get("keycodes", [])

            # Перевіряємо затиснення модифікатора (Ctrl або Alt)
            req_mod = hk["keys"][0].upper()
            mod_matched = False
            if req_mod == "CTRL" and (self.ctrl_held or (event.state & 0x0004)):
                mod_matched = True
            elif req_mod == "ALT" and (self.alt_held or (event.state & 0x20000) or (event.state & 0x0008)):
                mod_matched = True
            elif req_mod == "WIN" and self.win_held:
                mod_matched = True

            key_matched = (event.keycode in target_keycodes) or (event.keysym.upper() == target_key)

            if mod_matched and key_matched:
                # ВДАЛО ВИКОНАНО КОМБІНАЦІЮ!
                self.sound.play("complete")
                self.flash_key(hk["keys"][0], True)
                self.flash_key(hk["keys"][1], True)
                self.student_data["stars"] += 2
                self.student_data["hotkeys_mastered"] += 1
                self.update_stats_display()

                self.hk_status_box.configure(bg="#BBF7D0")
                self.hk_status_label.configure(
                    text=f"🎉 УРА! Комбінація {' + '.join(hk['keys'])} успішно виконана! +2 ⭐",
                    bg="#BBF7D0", fg="#166534"
                )
                # Автоматичний перехід до наступної комбінації через 1.2 сек
                self.after(1200, self.next_hotkey)
        elif self.hotkeys_submode == "quiz" and hasattr(self, "current_quiz_target"):
            q_item = self.current_quiz_target
            target_keycodes = q_item.get("keycodes", [])
            req_mod = q_item["keys"][0].upper()
            mod_matched = False
            if req_mod == "CTRL" and (self.ctrl_held or (event.state & 0x0004)):
                mod_matched = True
            elif req_mod == "ALT" and (self.alt_held or (event.state & 0x20000) or (event.state & 0x0008)):
                mod_matched = True

            if mod_matched and ((event.keycode in target_keycodes) or (event.keysym.upper() == q_item["keys"][1].upper())):
                self.check_quiz_answer(q_item, q_item)

    def process_letters_input(self, typed):
        target = self.target_char.upper()
        if typed == target:
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
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.sound.play("correct")
            self.flash_key(expected, True)

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

        matched_item = None
        highest_y = -999
        for item in self.arcade_items:
            if item["char"].upper() == typed:
                if item["y"] > highest_y:
                    highest_y = item["y"]
                    matched_item = item

        if matched_item:
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
        self.current_hotkey_idx = 0
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
        win.geometry("520x400")
        win.resizable(False, False)

        tk.Label(
            win, text="🌟 Досягнення наших учнів 🌟",
            font=("Segoe UI", 14, "bold"), fg="#1E293B"
        ).pack(pady=10)

        tree_frame = tk.Frame(win)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("name", "stars", "accuracy", "arcade", "hotkeys")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        tree.heading("name", text="Учень")
        tree.heading("stars", text="⭐ Зірочки")
        tree.heading("accuracy", text="🎯 Точність")
        tree.heading("arcade", text="☄️ Рекорд гри")
        tree.heading("hotkeys", text="⚡ Гарячі клавіші")

        tree.column("name", width=130)
        tree.column("stars", width=70, anchor="center")
        tree.column("accuracy", width=75, anchor="center")
        tree.column("arcade", width=85, anchor="center")
        tree.column("hotkeys", width=95, anchor="center")

        students = self.progress.data.get("students", {})
        for s_name, s_info in students.items():
            tot = s_info.get("total_typed", 0)
            cor = s_info.get("correct_typed", 0)
            acc = f"{int(cor / tot * 100)}%" if tot > 0 else "100%"
            stars = s_info.get("stars", 0)
            arc = s_info.get("best_arcade_score", 0)
            hk = s_info.get("hotkeys_mastered", 0)
            av = s_info.get("avatar", "🚀")
            tree.insert("", "end", values=(f"{av} {s_name}", stars, acc, arc, f"{hk} шт"))

        tree.pack(fill="both", expand=True)

        tk.Button(
            win, text="Закрити", font=("Segoe UI", 10, "bold"),
            bg="#64748B", fg="white", relief="flat", padx=15, pady=4,
            command=win.destroy
        ).pack(pady=10)


if __name__ == "__main__":
    app = KidsKeyboardTrainer()
    app.mainloop()
