# -*- coding: utf-8 -*-
"""
Клавіатурний тренажер для дітей "Спритні пальчики" / "Smart Fingers"
Розроблено спеціально для легкого навчання сліпому друку малих і великих літер, слів та гарячих клавіш.
Повна підтримка української літери 'ґ' / 'Ґ' як окремою клавішею, так і комбінацією Ctrl + Alt + Г (або AltGr + Г).
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
            "id": "ctrl_alt_g",
            "keys": ["Ctrl", "Alt", "Г"],
            "keycodes": [85],
            "title": "Українська літера «ґ» (якщо немає кнопки)",
            "emoji": "🔤",
            "desc": "Секретна комбінація Windows: друкує літеру «ґ» (або правий AltGr + г), якщо на твоїй клавіатурі немає окремої кнопки.",
            "finger": "Ліва рука: [Ctrl] + [Alt] + вказівний на [г] (або правий AltGr + [г])",
            "quiz_question": "Як надрукувати українську літеру «ґ», якщо для неї немає окремої кнопки на клавіатурі?",
            "sample_text": "Маленький ґудзик та весела дзиґа"
        },
        {
            "id": "shift_letter",
            "keys": ["Shift", "Літера"],
            "keycodes": [],
            "title": "Велика літера (Shift + буква)",
            "emoji": "🔠",
            "desc": "Затисни Shift мізинцем, щоб надрукувати ВЕЛИКУ літеру на початку речення чи імені.",
            "finger": "Протилежний мізинець на [Shift] + потрібна літера",
            "quiz_question": "Яку клавішу треба затиснути, щоб надрукувати ВЕЛИКУ літеру?",
            "sample_text": "Україна — рідний край"
        },
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
            "id": "win_shift_s",
            "keys": ["Win", "Shift", "S"],
            "keycodes": [83],
            "title": "Знімок екрана (Ножиці)",
            "emoji": "📸",
            "desc": "Дозволяє виділити та сфотографувати будь-яку частину екрана комп'ютера.",
            "finger": "Ліва рука: великий на [Win], мізинець на [Shift], безіменний на [S]",
            "quiz_question": "Яка комбінація робить швидкий знімок (скріншот) екрана?",
            "sample_text": "📸 Фото моєї перемоги"
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
        }
    ],
    "EN": [
        {
            "id": "shift_letter",
            "keys": ["Shift", "Letter"],
            "keycodes": [],
            "title": "Capital Letter (Shift + letter)",
            "emoji": "🔠",
            "desc": "Hold Shift with your pinky finger to type a CAPITAL letter.",
            "finger": "Opposite pinky on [Shift] + target letter key",
            "quiz_question": "Which key do you hold to type a CAPITAL letter?",
            "sample_text": "London is a big city"
        },
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
        }
    ]
}

CONTENT = {
    "UA": {
        "levels": [
            {
                "id": "home",
                "name": "Домашній ряд (Ф І В А / О Л Д Ж)",
                "desc": "Базова позиція пальчиків",
                "chars": ["ф", "і", "в", "а", "п", "р", "о", "л", "д", "ж", "є"]
            },
            {
                "id": "top",
                "name": "Верхній ряд (Й Ц У К Е Н...)",
                "desc": "Тренуємо рух пальців угору",
                "chars": ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ї"]
            },
            {
                "id": "bottom",
                "name": "Нижній ряд (Я Ч С М И Т... Ґ)",
                "desc": "Тренуємо рух пальців униз та літеру ґ",
                "chars": ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "ґ"]
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
                "chars": list("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя")
            }
        ],
        "words": [
            ("Кіт", "🐱"), ("Пес", "🐶"), ("Сонце", "☀️"), ("Дім", "🏠"),
            ("Ґава", "🐦"), ("Ґудзик", "🔘"), ("Дзиґа", "🌀"), ("Аґрус", "🍈"), ("Ґанок", "🏡"),
            ("Яблуко", "🍎"), ("Ракета", "🚀"), ("Зірка", "⭐️"), ("Веселка", "🌈"),
            ("Квітка", "🌸"), ("Авто", "🚗"), ("Книга", "📚"), ("Рибка", "🐟"),
            ("Жабка", "🐸"), ("Лев", "🦁"), ("Дерево", "🌲"), ("Кулька", "🎈"),
            ("М'яч", "⚽"), ("Бджола", "🐝"), ("Кавун", "🍉"), ("Морква", "🥕"),
            ("Грибок", "🍄"), ("Місяць", "🌙"), ("Літак", "✈️"), ("Човен", "⛵"),
            ("Ровер", "🚲"), ("Фарби", "🎨"), ("Подарунок", "🎁"), ("Мед", "🍯")
        ],
        "sentences": [
            "Ми любимо вчитися і грати!",
            "Ґава сидить на високому ґанку.",
            "Дзиґа швидко крутиться на підлозі.",
            "У саду дозрів смачний солодкий аґрус.",
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
                "chars": ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";"]
            },
            {
                "id": "top",
                "name": "Top Row (Q W E R T Y...)",
                "desc": "Moving fingers up",
                "chars": ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"]
            },
            {
                "id": "bottom",
                "name": "Bottom Row (Z X C V B...)",
                "desc": "Moving fingers down",
                "chars": ["z", "x", "c", "v", "b", "n", "m"]
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
                "chars": list("abcdefghijklmnopqrstuvwxyz")
            }
        ],
        "words": [
            ("Cat", "🐱"), ("Dog", "🐶"), ("Sun", "☀️"), ("Home", "🏠"),
            ("Apple", "🍎"), ("Rocket", "🚀"), ("Star", "⭐️"), ("Rainbow", "🌈"),
            ("Flower", "🌸"), ("Car", "🚗"), ("Book", "📚"), ("Fish", "🐟"),
            ("Frog", "🐸"), ("Lion", "🦁"), ("Tree", "🌲"), ("Balloon", "🎈"),
            ("Ball", "⚽"), ("Bee", "🐝"), ("Melon", "🍉"), ("Moon", "🌙"),
            ("Plane", "✈️"), ("Boat", "⛵"), ("Bike", "🚲"), ("Gift", "🎁")
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
    "MOD": "#D8B4FE"  # Модифікатори Shift/Ctrl/Alt/Win
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

# Повна реалістична розкладка з літерою Ґ, Shift, Ctrl, Alt, Win для навчання
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
        # Ряд 3: з окремою клавішею Ґ біля лівого Shift
        [("Shift", "MOD", 1.4), ("Ґ", "LP", 0.9), ("Я", "LP"), ("Ч", "LR"), ("С", "LM"), ("М", "LI"), ("И", "LI"),
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
        self.geometry("1040x720")
        self.minsize(940, 660)
        self.configure(bg="#EEF2F6")

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
        self.mode = "letters"  # "letters", "words", "hotkeys", "arcade", "sentences"
        self.case_mode = "mixed"  # "mixed", "lower", "upper"
        self.current_student_name = self.progress.data.get("last_student", "Юний Чемпіон")
        self.current_avatar = "🚀"
        self.student_data = self.progress.get_student(self.current_student_name, self.current_avatar)

        # Ігрові змінні
        self.target_chars = []  # список активних клавіш для підсвічування на віртуальній клавіатурі
        self.target_char = "а"  # точний символ з урахуванням регістру
        self.target_word = "Кіт"
        self.word_index = 0
        self.current_emoji = "🐱"
        self.selected_level_index = 0
        self.streak = 0
        self.session_typed = 0
        self.session_correct = 0

        # Стан затиснутих клавіш модифікаторів
        self.shift_held = False
        self.ctrl_held = False
        self.alt_held = False
        self.win_held = False

        # Змінні режиму гарячих клавіш
        self.hotkeys_submode = "practice"
        self.current_hotkey_idx = 0

        # Змінні аркадної гри
        self.arcade_running = False
        self.arcade_items = []
        self.arcade_score = 0
        self.arcade_lives = 3

        # Створення компонентів інтерфейсу
        self.build_ui()
        self.select_mode("letters")

        # Слухачі подій клавіатури
        self.bind("<KeyPress>", self.handle_key_down)
        self.bind("<KeyRelease>", self.handle_key_up)

    def build_ui(self):
        # 1. Верхня панель (Шапка)
        header_frame = tk.Frame(self, bg="#3A6073", height=65)
        header_frame.pack(side="top", fill="x")

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

        center_frame = tk.Frame(header_frame, bg="#3A6073")
        center_frame.pack(side="left", expand=True)

        self.title_banner = tk.Label(
            center_frame, text="🚀 Спритні пальчики 🌟",
            font=("Segoe UI", 16, "bold"), bg="#3A6073", fg="#FDE047"
        )
        self.title_banner.pack()

        right_frame = tk.Frame(header_frame, bg="#3A6073")
        right_frame.pack(side="right", padx=15, pady=8)

        self.lang_btn = tk.Button(
            right_frame, text="🇺🇦 Укр", font=("Segoe UI", 10, "bold"),
            bg="#2563EB", fg="white", relief="flat", padx=10, pady=4,
            cursor="hand2", command=self.toggle_language
        )
        self.lang_btn.pack(side="left", padx=4)

        self.sound_btn = tk.Button(
            right_frame, text="🔊", font=("Segoe UI Emoji", 12),
            bg="#16A34A", fg="white", relief="flat", padx=8, pady=2,
            cursor="hand2", command=self.toggle_sound
        )
        self.sound_btn.pack(side="left", padx=4)

        records_btn = tk.Button(
            right_frame, text="🏆 Рекорди", font=("Segoe UI", 10, "bold"),
            bg="#F59E0B", fg="white", relief="flat", padx=8, pady=4,
            cursor="hand2", command=self.show_records_window
        )
        records_btn.pack(side="left", padx=4)

        # 2. Панель вибору режимів
        mode_bar = tk.Frame(self, bg="#E2E8F0", height=45)
        mode_bar.pack(side="top", fill="x")

        self.mode_buttons = {}
        modes = [
            ("letters", "🔤 Літери (Малі та Великі)"),
            ("words", "🐱 Веселі слова"),
            ("hotkeys", "⚡ Гарячі клавіші"),
            ("arcade", "☄️ Падаючі літери"),
            ("sentences", "📖 Речення")
        ]

        for m_id, m_text in modes:
            btn = tk.Button(
                mode_bar, text=m_text, font=("Segoe UI", 10, "bold"),
                bg="#E2E8F0", fg="#475569", bd=0, relief="flat", padx=12, pady=8,
                cursor="hand2", command=lambda mid=m_id: self.select_mode(mid)
            )
            btn.pack(side="left", padx=2, pady=2)
            self.mode_buttons[m_id] = btn

        # 3. Головна робоча зона
        self.work_area = tk.Frame(self, bg="#EEF2F6")
        self.work_area.pack(side="top", fill="both", expand=True, padx=20, pady=8)

        # 4. Нижня зона: Віртуальна інтерактивна клавіатура
        self.kbd_frame = tk.Frame(self, bg="#CBD5E1", height=230)
        self.kbd_frame.pack(side="bottom", fill="x", padx=15, pady=(0, 10))

        hint_bar = tk.Frame(self.kbd_frame, bg="#CBD5E1")
        hint_bar.pack(side="top", fill="x", pady=(4, 2))

        self.finger_hint_label = tk.Label(
            hint_bar, text="👉 Підказка пальчиків",
            font=("Segoe UI", 11, "bold"), bg="#CBD5E1", fg="#1E293B"
        )
        self.finger_hint_label.pack(side="left", padx=20)

        self.streak_label = tk.Label(
            hint_bar, text="🔥 Серія: 0",
            font=("Segoe UI", 11, "bold"), bg="#CBD5E1", fg="#EA580C"
        )
        self.streak_label.pack(side="right", padx=20)

        self.kbd_canvas = tk.Canvas(self.kbd_frame, bg="#F1F5F9", height=190, bd=0, highlightthickness=0)
        self.kbd_canvas.pack(fill="both", expand=True, padx=6, pady=4)
        self.kbd_canvas.bind("<Configure>", lambda e: self.draw_keyboard())

        self.key_rects = {}  # { char: [ {rect, text, base_color, finger, base_char} ] }

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

    # --- РЕЖИМ 1: ЛІТЕРИ ТА РЯДИ (МАЛІ ТА ВЕЛИКІ) ---
    def setup_letters_view(self):
        sublevels_frame = tk.Frame(self.work_area, bg="#EEF2F6")
        sublevels_frame.pack(fill="x", pady=(0, 6))

        tk.Label(sublevels_frame, text="Ряд:", font=("Segoe UI", 10, "bold"), bg="#EEF2F6", fg="#334155").pack(side="left", padx=4)

        levels = CONTENT[self.lang]["levels"]
        self.level_var = tk.StringVar(value=levels[self.selected_level_index]["name"])
        level_combo = ttk.Combobox(
            sublevels_frame, textvariable=self.level_var,
            values=[lvl["name"] for lvl in levels], state="readonly", width=30, font=("Segoe UI", 10)
        )
        level_combo.pack(side="left", padx=4)
        level_combo.bind("<<ComboboxSelected>>", self.on_level_selected)

        tk.Label(sublevels_frame, text="Регістр:", font=("Segoe UI", 10, "bold"), bg="#EEF2F6", fg="#334155").pack(side="left", padx=(15, 4))

        case_options = [
            ("mixed", "🔀 Малі та великі (Упереміш)"),
            ("lower", "🔤 Лише малі (а, б, в...)"),
            ("upper", "🔠 Лише великі (Shift + а...)")
        ]
        self.case_var = tk.StringVar(value=dict(case_options).get(self.case_mode, case_options[0][1]))
        case_combo = ttk.Combobox(
            sublevels_frame, textvariable=self.case_var,
            values=[opt[1] for opt in case_options], state="readonly", width=28, font=("Segoe UI", 10)
        )
        case_combo.pack(side="left", padx=4)

        def on_case_change(e):
            val = self.case_var.get()
            for opt_id, opt_text in case_options:
                if opt_text == val:
                    self.case_mode = opt_id
                    break
            self.next_letter()

        case_combo.bind("<<ComboboxSelected>>", on_case_change)

        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

        self.letter_type_badge = tk.Label(
            card, text="🔹 МАЛА ЛІТЕРА", font=("Segoe UI", 11, "bold"),
            bg="#E0F2FE", fg="#0369A1", padx=14, pady=3, relief="solid", bd=1
        )
        self.letter_type_badge.pack(pady=(10, 0))

        self.big_char_label = tk.Label(
            card, text="?", font=("Arial", 74, "bold"),
            bg="#FFFFFF", fg="#2563EB"
        )
        self.big_char_label.pack(expand=True)

        self.combo_hint_frame = tk.Frame(card, bg="#FFFFFF")
        self.combo_hint_frame.pack(pady=(0, 4))

        self.combo_hint_label = tk.Label(
            self.combo_hint_frame, text="", font=("Segoe UI", 12, "bold"),
            bg="#FEF3C7", fg="#92400E", padx=16, pady=4, relief="ridge", bd=2
        )
        self.combo_hint_label.pack()

        self.feedback_label = tk.Label(
            card, text="", font=("Segoe UI", 13, "bold"),
            bg="#FFFFFF", fg="#16A34A"
        )
        self.feedback_label.pack(pady=(0, 10))

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

        base_char = random.choice(chars)
        while len(chars) > 1 and base_char.lower() == self.target_char.lower():
            base_char = random.choice(chars)

        if base_char.isalpha():
            if self.case_mode == "lower":
                char = base_char.lower()
            elif self.case_mode == "upper":
                char = base_char.upper()
            else:
                char = random.choice([base_char.lower(), base_char.upper()])
        else:
            char = base_char

        self.target_char = char
        self.update_letter_display()

    def update_letter_display(self):
        char = self.target_char
        is_upper = char.isupper()

        # Спеціальна обробка української літери 'ґ' / 'Ґ' з підказкою Ctrl + Alt + Г
        if char.lower() == "ґ":
            if is_upper:
                self.big_char_label.configure(text=char, fg="#4338CA")
                self.letter_type_badge.configure(
                    text="⭐ ВЕЛИКА ЛІТЕРА «Ґ»", bg="#EDE9FE", fg="#5B21B6"
                )
                combo_text = "👉 [ Shift ] + [ ґ ]   АБО:   [ Ctrl ] + [ Alt ] + [ Shift ] + [ г ]"
                self.combo_hint_label.configure(
                    text=combo_text, bg="#FEF3C7", fg="#92400E"
                )
                self.target_chars = ["SHIFT", "Ґ", "CTRL", "ALT", "Г"]
                self.finger_hint_label.configure(
                    text="👉 [Shift]+[ґ] АБО затисни [Ctrl]+[Alt]+[Shift] та натисни [г]!", fg="#4338CA"
                )
            else:
                self.big_char_label.configure(text=char, fg="#2563EB")
                self.letter_type_badge.configure(
                    text="🔹 МАЛА ЛІТЕРА «ґ»", bg="#E0F2FE", fg="#0369A1"
                )
                combo_text = "👉 Кнопка [ ґ ]   АБО комбінація:   [ Ctrl ] + [ Alt ] + [ г ] (AltGr + г)"
                self.combo_hint_label.configure(
                    text=combo_text, bg="#FEF3C7", fg="#92400E"
                )
                self.target_chars = ["Ґ", "CTRL", "ALT", "Г"]
                self.finger_hint_label.configure(
                    text="👉 Натисни [ ґ ] АБО затисни [Ctrl] + [Alt] та натисни [г] (якщо немає кнопки)!", fg="#0369A1"
                )
            self.highlight_keyboard_keys(self.target_chars)
            return

        # Звичайні літери
        if is_upper:
            self.big_char_label.configure(text=char, fg="#4338CA")
            self.letter_type_badge.configure(
                text="⭐ ВЕЛИКА ЛІТЕРА (ПОТРІБЕН SHIFT!)",
                bg="#EDE9FE", fg="#5B21B6"
            )
            combo_text = f"👉 Комбінація: [ Shift ]  +  [ {char.lower()} ]"
            self.combo_hint_label.configure(
                text=combo_text, bg="#FEF3C7", fg="#92400E"
            )
            self.target_chars = ["SHIFT", char.upper()]
            self.update_finger_hint_for_char(char, is_uppercase=True)
        elif char.islower():
            self.big_char_label.configure(text=char, fg="#2563EB")
            self.letter_type_badge.configure(
                text="🔹 МАЛА ЛІТЕРА (БЕЗ SHIFT)",
                bg="#E0F2FE", fg="#0369A1"
            )
            combo_text = f"👉 Звичайна клавіша: [ {char} ] (без Shift)"
            self.combo_hint_label.configure(
                text=combo_text, bg="#F1F5F9", fg="#334155"
            )
            self.target_chars = [char.upper()]
            self.update_finger_hint_for_char(char, is_uppercase=False)
        else:
            self.big_char_label.configure(text=char, fg="#0F172A")
            self.letter_type_badge.configure(
                text="🔢 СИМВОЛ / ЦИФРА",
                bg="#F1F5F9", fg="#334155"
            )
            self.combo_hint_label.configure(
                text=f"👉 Клавіша: [ {char} ]", bg="#F1F5F9", fg="#334155"
            )
            self.target_chars = [char.upper()]
            self.update_finger_hint_for_char(char, is_uppercase=False)

        self.highlight_keyboard_keys(self.target_chars)

    def update_finger_hint_for_char(self, char, is_uppercase=False):
        if char.lower() == "ґ":
            if is_uppercase:
                self.finger_hint_label.configure(
                    text="👉 Натисни [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г] (якщо немає кнопки)!", fg="#4338CA"
                )
            else:
                self.finger_hint_label.configure(
                    text="👉 Натисни [ґ] АБО [Ctrl]+[Alt]+[г] (якщо на клавіатурі немає окремої кнопки)!", fg="#0369A1"
                )
            return

        char_key = char.upper()
        finger_dict = FINGER_NAMES_UA if self.lang == "UA" else FINGER_NAMES_EN
        if char_key in self.key_rects:
            finger_code = self.key_rects[char_key][0]["finger"]
            finger_name = finger_dict.get(finger_code, "")

            if is_uppercase:
                if finger_code.startswith("L"):
                    shift_side = "Правий мізинець на [Shift]" if self.lang == "UA" else "Right Pinky on [Shift]"
                else:
                    shift_side = "Лівий мізинець на [Shift]" if self.lang == "UA" else "Left Pinky on [Shift]"
                self.finger_hint_label.configure(
                    text=f"👉 {shift_side}  +  {finger_name} на [{char.lower()}]", fg="#4338CA"
                )
            else:
                self.finger_hint_label.configure(
                    text=f"👉 Палець: {finger_name} (просто натисни [{char}])", fg="#0369A1"
                )
        else:
            self.finger_hint_label.configure(text="👉 Натискай потрібну клавішу", fg="#1E293B")

    # --- РЕЖИМ 2: ВЕСЕЛІ СЛОВА (З ВЕЛИКОЇ ЛІТЕРИ ТА МАЛИМИ) ---
    def setup_words_view(self):
        card = tk.Frame(self.work_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

        self.word_emoji_label = tk.Label(
            card, text="🐱", font=("Segoe UI Emoji", 50),
            bg="#FFFFFF"
        )
        self.word_emoji_label.pack(pady=(10, 0))

        self.word_chars_frame = tk.Frame(card, bg="#FFFFFF")
        self.word_chars_frame.pack(expand=True, pady=8)
        self.word_char_labels = []

        self.word_combo_badge = tk.Label(
            card, text="", font=("Segoe UI", 11, "bold"),
            bg="#FEF3C7", fg="#92400E", padx=14, pady=3, relief="solid", bd=1
        )
        self.word_combo_badge.pack(pady=(0, 4))

        self.word_feedback_label = tk.Label(
            card, text="Вводь літери слова по черзі!", font=("Segoe UI", 12, "bold"),
            bg="#FFFFFF", fg="#64748B"
        )
        self.word_feedback_label.pack(pady=(0, 10))

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
                self.word_chars_frame, text=ch, font=("Segoe UI", 34, "bold"),
                bg="#F1F5F9", fg="#64748B", width=2, relief="solid", bd=1
            )
            lbl.pack(side="left", padx=4)
            self.word_char_labels.append(lbl)

        self.update_word_highlight()

    def update_word_highlight(self):
        if self.word_index < len(self.target_word):
            curr_char = self.target_word[self.word_index]
            self.target_char = curr_char
            is_upper = curr_char.isupper()

            self.word_char_labels[self.word_index].configure(
                bg="#FEF08A", fg="#854D0E", relief="ridge", bd=2
            )

            if curr_char.lower() == "ґ":
                if is_upper:
                    self.target_chars = ["SHIFT", "Ґ", "CTRL", "ALT", "Г"]
                    self.word_combo_badge.configure(
                        text="⭐ ВЕЛИКА [ Ґ ]: [ Shift ] + [ ґ ] АБО [ Ctrl ] + [ Alt ] + [ Shift ] + [ г ]",
                        bg="#FEF3C7", fg="#92400E"
                    )
                    self.finger_hint_label.configure(
                        text="👉 [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г] (якщо немає кнопки)!", fg="#4338CA"
                    )
                else:
                    self.target_chars = ["Ґ", "CTRL", "ALT", "Г"]
                    self.word_combo_badge.configure(
                        text="🔹 Літера [ ґ ]: кнопка [ ґ ] АБО [ Ctrl ] + [ Alt ] + [ г ]",
                        bg="#E0F2FE", fg="#0369A1"
                    )
                    self.finger_hint_label.configure(
                        text="👉 Кнопка [ґ] АБО [Ctrl]+[Alt]+[г] (якщо немає кнопки)!", fg="#0369A1"
                    )
                self.word_feedback_label.configure(
                    text=f"Введи літеру '{curr_char}' ([ґ] або Ctrl+Alt+г)!", fg="#2563EB"
                )
            elif is_upper:
                self.target_chars = ["SHIFT", curr_char.upper()]
                self.word_combo_badge.configure(
                    text=f"⭐ Перша літера ВЕЛИКА! Затисни: [ Shift ] + [ {curr_char.lower()} ]",
                    bg="#FEF3C7", fg="#92400E"
                )
                self.update_finger_hint_for_char(curr_char, is_uppercase=True)
                self.word_feedback_label.configure(
                    text=f"Затисни Shift і натисни '{curr_char.lower()}'!", fg="#4338CA"
                )
            else:
                self.target_chars = [curr_char.upper()]
                self.word_combo_badge.configure(
                    text=f"🔹 Мала літера: просто [ {curr_char} ] (без Shift)",
                    bg="#E0F2FE", fg="#0369A1"
                )
                self.update_finger_hint_for_char(curr_char, is_uppercase=False)
                self.word_feedback_label.configure(
                    text=f"Наступна літера: '{curr_char}'", fg="#2563EB"
                )

            self.highlight_keyboard_keys(self.target_chars)
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

        nav_frame = tk.Frame(card, bg="#FFFFFF")
        nav_frame.pack(fill="x", padx=15, pady=(6, 4))

        tk.Button(
            nav_frame, text="⬅️ Попередня", font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9", fg="#334155", relief="flat", padx=10, pady=3,
            cursor="hand2", command=self.prev_hotkey
        ).pack(side="left")

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

        keys_display_frame = tk.Frame(card, bg="#FFFFFF")
        keys_display_frame.pack(pady=(6, 2))

        for idx, k in enumerate(hk["keys"]):
            if idx > 0:
                tk.Label(
                    keys_display_frame, text="+", font=("Segoe UI", 24, "bold"),
                    bg="#FFFFFF", fg="#94A3B8"
                ).pack(side="left", padx=6)

            badge = tk.Label(
                keys_display_frame, text=f" {k} ", font=("Segoe UI", 20, "bold"),
                bg="#E0E7FF", fg="#3730A3", bd=2, relief="solid", padx=10, pady=3
            )
            badge.pack(side="left", padx=4)

        tk.Label(
            card, text=f"{hk['emoji']} {hk['title']}",
            font=("Segoe UI", 14, "bold"), bg="#FFFFFF", fg="#1E293B"
        ).pack(pady=(2, 1))

        tk.Label(
            card, text=hk["desc"],
            font=("Segoe UI", 10), bg="#FFFFFF", fg="#64748B"
        ).pack(pady=(0, 4))

        self.hk_status_box = tk.Frame(card, bg="#FEF3C7", bd=1, relief="solid")
        self.hk_status_box.pack(fill="x", padx=40, pady=4)

        mod_name = hk['keys'][0]
        self.hk_status_label = tk.Label(
            self.hk_status_box, text=f"⏳ Затисни клавішу [{mod_name}]...",
            font=("Segoe UI", 11, "bold"), bg="#FEF3C7", fg="#B45309", pady=5
        )
        self.hk_status_label.pack()

        # Інтерактивне поле — адаптується до поточної комбінації клавіш
        sandbox_card = tk.Frame(card, bg="#F8FAFC", bd=2, relief="ridge", padx=16, pady=6)
        sandbox_card.pack(anchor="center", pady=(6, 6))

        hk_id = hk["id"]

        # ---------- Ctrl+C / Ctrl+V — копіювання та вставка ----------
        if hk_id in ("ctrl_c", "ctrl_v"):
            tk.Label(
                sandbox_card, text="🧪 Випробуй: скопіюй зразок (Ctrl+C) та встав (Ctrl+V)",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            row1 = tk.Frame(sandbox_card, bg="#F8FAFC")
            row1.pack(fill="x", pady=2)
            tk.Label(row1, text="📋 Зразок:", font=("Segoe UI", 10, "bold"),
                     bg="#F8FAFC", fg="#475569", width=13, anchor="e").pack(side="left", padx=(0, 6))
            sample_entry = tk.Entry(row1, font=("Segoe UI", 11), width=30, justify="center")
            sample_entry.insert(0, hk["sample_text"])
            sample_entry.pack(side="left", padx=4)

            row2 = tk.Frame(sandbox_card, bg="#F8FAFC")
            row2.pack(fill="x", pady=2)
            tk.Label(row2, text="📥 Сюди встав:", font=("Segoe UI", 10, "bold"),
                     bg="#F8FAFC", fg="#475569", width=13, anchor="e").pack(side="left", padx=(0, 6))
            target_entry = tk.Entry(row2, font=("Segoe UI", 11), width=30, justify="center")
            target_entry.pack(side="left", padx=4)

            self.practice_sample_entry = sample_entry
            self.practice_target_entry = target_entry

            def copy_action():
                try:
                    sel = sample_entry.selection_get()
                except Exception:
                    sel = sample_entry.get()
                if not sel:
                    sel = hk["sample_text"]
                self.clipboard_clear()
                self.clipboard_append(sel)
                self.flash_key("CTRL", True)
                self.flash_key("C", True)
                self.sound.play("correct")
                self.sandbox_msg.configure(
                    text="📋 Скопійовано! Тепер перейди у поле «Сюди встав» і натисни Ctrl + V!",
                    fg="#16A34A"
                )

            def paste_action():
                try:
                    clip_text = self.clipboard_get()
                except Exception:
                    clip_text = ""
                if clip_text:
                    target_entry.delete(0, tk.END)
                    target_entry.insert(0, clip_text)
                    self.flash_key("CTRL", True)
                    self.flash_key("V", True)
                    self.sound.play("complete")
                    self.sandbox_msg.configure(
                        text="🎉 УРА! Текст успішно вставлено! Молодець!",
                        fg="#16A34A"
                    )
                else:
                    self.sound.play("wrong")
                    self.sandbox_msg.configure(
                        text="⚠️ Буфер порожній! Спочатку скопіюй зразок — Ctrl + C!",
                        fg="#DC2626"
                    )

            tk.Button(row1, text="📋 Ctrl+C", font=("Segoe UI", 9, "bold"),
                      bg="#E0E7FF", fg="#3730A3", relief="flat", padx=8, pady=2,
                      cursor="hand2", command=copy_action).pack(side="left", padx=4)
            tk.Button(row2, text="📥 Ctrl+V", font=("Segoe UI", 9, "bold"),
                      bg="#DCFCE7", fg="#166534", relief="flat", padx=8, pady=2,
                      cursor="hand2", command=paste_action).pack(side="left", padx=4)

            hint_text = "💡 Клікни у зразок → Ctrl+C → клікни у поле вставки → Ctrl+V"

            def handle_entry_shortcuts(event, widget):
                is_ctrl = self.ctrl_held or bool(event.state & 0x0004)
                if is_ctrl and (event.keycode == 67 or event.char == '\x03' or event.keysym.lower() in ('c', 'ukrainian_es', 'cyrillic_es', 'с')):
                    copy_action()
                    return "break"
                elif is_ctrl and (event.keycode == 86 or event.char == '\x16' or event.keysym.lower() in ('v', 'ukrainian_em', 'cyrillic_em', 'м')):
                    paste_action()
                    return "break"
                elif is_ctrl and (event.keycode == 65 or event.char == '\x01' or event.keysym.lower() in ('a', 'ukrainian_ef', 'cyrillic_ef', 'ф')):
                    widget.select_range(0, tk.END)
                    return "break"

            sample_entry.bind("<KeyPress>", lambda e: handle_entry_shortcuts(e, sample_entry))
            sample_entry.bind("<FocusIn>", lambda e: sample_entry.select_range(0, tk.END))
            target_entry.bind("<KeyPress>", lambda e: handle_entry_shortcuts(e, target_entry))

        # ---------- Ctrl+A — виділити все ----------
        elif hk_id == "ctrl_a":
            tk.Label(
                sandbox_card, text="🧪 Випробуй: виділи весь текст натисканням Ctrl+A",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            test_entry = tk.Entry(sandbox_card, font=("Segoe UI", 11), width=40, justify="center")
            test_entry.insert(0, hk["sample_text"])
            test_entry.pack(anchor="center", pady=4)
            self.practice_sample_entry = test_entry

            def on_select_all(event):
                is_ctrl = self.ctrl_held or bool(event.state & 0x0004)
                if is_ctrl and (event.keycode == 65 or event.char == '\x01' or event.keysym.lower() in ('a', 'ukrainian_ef', 'cyrillic_ef', 'ф')):
                    test_entry.select_range(0, tk.END)
                    self.sandbox_msg.configure(text="🎉 Весь текст виділено! Чудово!", fg="#16A34A")
                    self.sound.play("correct")
                    return "break"

            test_entry.bind("<KeyPress>", on_select_all)
            test_entry.bind("<FocusIn>", lambda e: None)
            hint_text = "💡 Клікни у поле, потім натисни Ctrl + A"

        # ---------- Ctrl+Z / Ctrl+Y — скасування / повторення ----------
        elif hk_id in ("ctrl_z", "ctrl_y"):
            action_word = "скасування (Undo)" if hk_id == "ctrl_z" else "повторення (Redo)"
            tk.Label(
                sandbox_card, text=f"🧪 Випробуй: введи текст, потім спробуй {action_word}",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            test_text = tk.Text(sandbox_card, font=("Segoe UI", 11), width=40, height=2,
                                wrap="word", undo=True, maxundo=20)
            test_text.insert("1.0", hk["sample_text"])
            test_text.pack(anchor="center", pady=4)

            def on_undo_redo(event):
                is_ctrl = self.ctrl_held or bool(event.state & 0x0004)
                if is_ctrl and (event.keycode == 90 or event.keysym.lower() in ('z', 'я')):
                    try:
                        test_text.edit_undo()
                        if hk_id == "ctrl_z":
                            self.sandbox_msg.configure(text="↩️ Скасовано! Ctrl+Z працює!", fg="#16A34A")
                            self.sound.play("correct")
                        else:
                            self.sandbox_msg.configure(text="↩️ Скасовано! Тепер натисни Ctrl+Y для повторення!", fg="#2563EB")
                    except tk.TclError:
                        self.sandbox_msg.configure(text="Немає що скасовувати. Спочатку зміни текст!", fg="#B45309")
                    return "break"
                elif is_ctrl and (event.keycode == 89 or event.keysym.lower() in ('y', 'н')):
                    try:
                        test_text.edit_redo()
                        if hk_id == "ctrl_y":
                            self.sandbox_msg.configure(text="🔁 Повторено! Ctrl+Y працює!", fg="#16A34A")
                            self.sound.play("correct")
                        else:
                            self.sandbox_msg.configure(text="🔁 Повторено дію!", fg="#16A34A")
                    except tk.TclError:
                        self.sandbox_msg.configure(text="Немає що повторювати. Спочатку скасуй дію (Ctrl+Z)!", fg="#B45309")
                    return "break"

            test_text.bind("<KeyPress>", on_undo_redo)
            extra = "Ctrl+Z" if hk_id == "ctrl_z" else "спочатку Ctrl+Z, потім Ctrl+Y"
            hint_text = f"💡 Зміни текст у полі, потім натисни {extra}"

        # ---------- Ctrl+F — пошук ----------
        elif hk_id == "ctrl_f":
            tk.Label(
                sandbox_card, text="🧪 Випробуй: знайди слово у тексті (Ctrl+F)",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            long_text = "У чарівному лісі жив маленький їжачок. Він любив збирати гриби та ягоди. " \
                        "Одного дня їжачок знайшов секретну стежку до чарівного озера."
            text_label = tk.Label(
                sandbox_card, text=long_text, font=("Segoe UI", 10), bg="#FFFFFF",
                fg="#334155", wraplength=450, justify="left", bd=1, relief="solid", padx=8, pady=6
            )
            text_label.pack(anchor="center", pady=4)

            search_frame = tk.Frame(sandbox_card, bg="#F8FAFC")
            search_frame.pack(anchor="center", pady=2)
            tk.Label(search_frame, text="🔍 Шукати:", font=("Segoe UI", 10, "bold"),
                     bg="#F8FAFC", fg="#475569").pack(side="left", padx=(0, 6))
            search_entry = tk.Entry(search_frame, font=("Segoe UI", 11), width=20, justify="center")
            search_entry.pack(side="left", padx=4)

            def do_search(*_):
                word = search_entry.get().strip().lower()
                if word and word in long_text.lower():
                    self.sandbox_msg.configure(text=f"🎉 Знайдено слово «{word}» у тексті!", fg="#16A34A")
                    self.sound.play("correct")
                elif word:
                    self.sandbox_msg.configure(text=f"🔍 Слово «{word}» не знайдено. Спробуй інше!", fg="#B45309")

            search_entry.bind("<Return>", do_search)
            tk.Button(search_frame, text="🔎 Знайти", font=("Segoe UI", 9, "bold"),
                      bg="#E0E7FF", fg="#3730A3", relief="flat", padx=8, cursor="hand2",
                      command=do_search).pack(side="left", padx=4)

            hint_text = "💡 Введи слово (наприклад «їжачок») і натисни Enter або кнопку"

        # ---------- Ctrl+S — збереження ----------
        elif hk_id == "ctrl_s":
            tk.Label(
                sandbox_card, text="🧪 Випробуй: «збережи» свій текст (Ctrl+S)",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            save_entry = tk.Entry(sandbox_card, font=("Segoe UI", 11), width=40, justify="center")
            save_entry.insert(0, hk["sample_text"])
            save_entry.pack(anchor="center", pady=4)

            self.save_indicator = tk.Label(
                sandbox_card, text="📄 Не збережено", font=("Segoe UI", 10, "bold"),
                bg="#FEF3C7", fg="#B45309", padx=10, pady=3
            )
            self.save_indicator.pack(anchor="center", pady=2)

            def on_save(event=None):
                is_ctrl = False
                if event:
                    is_ctrl = self.ctrl_held or bool(event.state & 0x0004)
                    if is_ctrl and (event.keycode == 83 or event.keysym.lower() in ('s', 'і')):
                        pass
                    else:
                        return
                self.save_indicator.configure(text="💾 Збережено! ✅", bg="#DCFCE7", fg="#166534")
                self.sandbox_msg.configure(text="🎉 Файл «збережено»! Ctrl+S працює!", fg="#16A34A")
                self.sound.play("correct")
                return "break"

            save_entry.bind("<KeyPress>", on_save)
            hint_text = "💡 Зміни текст у полі, потім натисни Ctrl + S"

        # ---------- Ctrl+T — нова вкладка ----------
        elif hk_id == "ctrl_t":
            tk.Label(
                sandbox_card, text="🧪 Натисни Ctrl+T — ця комбінація працює у браузері",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            tk.Label(
                sandbox_card, text="🌐 У браузері (Chrome, Edge) ця комбінація\nвідкриє нову порожню вкладку для пошуку!",
                font=("Segoe UI", 11), bg="#F8FAFC", fg="#475569", justify="center"
            ).pack(anchor="center", pady=6)

            hint_text = "💡 Натисни комбінацію на клавіатурі для перевірки"

        # ---------- Ctrl+Alt+Г — літера ґ ----------
        elif hk_id == "ctrl_alt_g":
            tk.Label(
                sandbox_card, text="🧪 Випробуй: введи літеру «ґ» комбінацією Ctrl+Alt+Г",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            g_entry = tk.Entry(sandbox_card, font=("Segoe UI", 14), width=30, justify="center")
            g_entry.pack(anchor="center", pady=4)

            def on_g_key(event):
                if event.char and event.char in ("ґ", "Ґ"):
                    self.sandbox_msg.configure(
                        text=f"🎉 Чудово! Літера «{event.char}» надрукована!", fg="#16A34A"
                    )
                    self.sound.play("correct")

            g_entry.bind("<KeyPress>", on_g_key)
            hint_text = "💡 Клікни у поле і натисни Ctrl + Alt + Г (або AltGr + Г)"

        # ---------- Shift + літера — велика літера ----------
        elif hk_id == "shift_letter":
            tk.Label(
                sandbox_card, text="🧪 Випробуй: введи велику літеру через Shift",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            shift_entry = tk.Entry(sandbox_card, font=("Segoe UI", 14), width=30, justify="center")
            shift_entry.pack(anchor="center", pady=4)

            def on_shift_letter(event):
                if event.char and event.char.isalpha():
                    if event.char.isupper():
                        self.sandbox_msg.configure(
                            text=f"🎉 Молодець! Велика літера «{event.char}» — Shift працює!", fg="#16A34A"
                        )
                        self.sound.play("correct")
                    else:
                        self.sandbox_msg.configure(
                            text=f"Це мала літера «{event.char}». Затисни Shift і спробуй ще!", fg="#B45309"
                        )

            shift_entry.bind("<KeyPress>", on_shift_letter)
            hint_text = "💡 Клікни у поле, затисни Shift і натисни будь-яку літеру"

        # ---------- Усі інші — загальне інтерактивне поле ----------
        else:
            combo_str = " + ".join(hk["keys"])
            tk.Label(
                sandbox_card, text=f"🧪 Натисни комбінацію {combo_str} на клавіатурі!",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#334155"
            ).pack(anchor="center", pady=(0, 5))

            tk.Label(
                sandbox_card, text=f"{hk['emoji']} {hk['desc']}",
                font=("Segoe UI", 10), bg="#F8FAFC", fg="#475569",
                wraplength=450, justify="center"
            ).pack(anchor="center", pady=6)

            hint_text = f"💡 Натисни {combo_str} на клавіатурі для перевірки"

        # Рядок статусу / підказки
        self.sandbox_msg = tk.Label(
            sandbox_card, text=hint_text,
            font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg="#475569"
        )
        self.sandbox_msg.pack(anchor="center", pady=(4, 2))


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
        keys_to_highlight = [k.upper() for k in hk["keys"] if k.upper() not in ("ЛІТЕРА", "LETTER")]
        self.target_chars = keys_to_highlight
        self.finger_hint_label.configure(
            text=f"👉 {hk['finger']}", fg="#4338CA"
        )
        self.highlight_keyboard_keys(self.target_chars)

    def render_hotkeys_quiz(self):
        for w in self.hotkeys_content_area.winfo_children():
            w.destroy()
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        q_item = random.choice(hotkeys_list)
        self.current_quiz_target = q_item

        card = tk.Frame(self.hotkeys_content_area, bg="#FFFFFF", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

        tk.Label(
            card, text="🏆 Вікторина знавця гарячих клавіш! 🌟",
            font=("Segoe UI", 15, "bold"), bg="#FFFFFF", fg="#2563EB"
        ).pack(pady=(10, 4))

        tk.Label(
            card, text=q_item["quiz_question"],
            font=("Segoe UI", 13, "bold"), bg="#FFFFFF", fg="#1E293B", wraplength=700
        ).pack(pady=(4, 10))

        distractors = [x for x in hotkeys_list if x["id"] != q_item["id"]]
        random.shuffle(distractors)
        options = [q_item] + distractors[:3]
        random.shuffle(options)

        options_frame = tk.Frame(card, bg="#FFFFFF")
        options_frame.pack(expand=True, pady=4)

        colors = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"]
        for idx, opt in enumerate(options):
            combo_str = " + ".join(opt["keys"])
            btn_text = f"{opt['emoji']}  {combo_str}"
            btn = tk.Button(
                options_frame, text=btn_text, font=("Segoe UI", 11, "bold"),
                bg=colors[idx % len(colors)], fg="white", width=30, height=2,
                relief="flat", cursor="hand2", bd=0,
                command=lambda chosen=opt: self.check_quiz_answer(chosen, q_item)
            )
            btn.grid(row=idx // 2, column=idx % 2, padx=10, pady=6)

        self.quiz_feedback = tk.Label(
            card, text="Обери правильну комбінацію мишкою або натисни її на клавіатурі!",
            font=("Segoe UI", 11), bg="#FFFFFF", fg="#64748B"
        )
        self.quiz_feedback.pack(pady=(2, 8))

        keys_to_highlight = [k.upper() for k in q_item["keys"] if k.upper() not in ("ЛІТЕРА", "LETTER")]
        self.target_chars = keys_to_highlight
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
            font=("Segoe UI", 12, "bold"), bg="#FFFFFF", fg="#1E293B"
        ).pack(anchor="w", padx=15, pady=(8, 6))

        for hk in hotkeys_list:
            row_frame = tk.Frame(scroll_content, bg="#F8FAFC", bd=1, relief="solid")
            row_frame.pack(fill="x", expand=True, padx=15, pady=3)

            badge_text = " + ".join(hk["keys"])
            badge = tk.Label(
                row_frame, text=badge_text, font=("Segoe UI", 10, "bold"),
                bg="#E0E7FF", fg="#3730A3", width=14, pady=3
            )
            badge.pack(side="left", padx=6, pady=5)

            info_frame = tk.Frame(row_frame, bg="#F8FAFC")
            info_frame.pack(side="left", fill="both", expand=True, padx=6)

            tk.Label(
                info_frame, text=f"{hk['emoji']} {hk['title']}",
                font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#0F172A"
            ).pack(anchor="w")

            tk.Label(
                info_frame, text=hk["desc"] + " | " + hk["finger"],
                font=("Segoe UI", 9), bg="#F8FAFC", fg="#64748B"
            ).pack(anchor="w")

    # --- РЕЖИМ 4: ПАДАЮЧІ ЛІТЕРИ (АРКАДНА МІНІ-ГРА) ---
    def setup_arcade_view(self):
        card = tk.Frame(self.work_area, bg="#0F172A", bd=2, relief="ridge")
        card.pack(fill="both", expand=True, pady=4)

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

        # Вибір складності з прикольними назвами
        self.arcade_difficulties = {
            "easy":   {"label": "🐢 Равлик",    "speed": (0.7, 1.3), "spawn": (2400, 3200), "lives": 5, "bg": "#10B981"},
            "medium": {"label": "🐇 Зайчик",   "speed": (1.1, 2.0), "spawn": (1800, 2600), "lives": 3, "bg": "#F59E0B"},
            "hard":   {"label": "🚀 Блискавка", "speed": (1.8, 3.0), "spawn": (1000, 1600), "lives": 2, "bg": "#EF4444"},
        }
        self.arcade_difficulty = "medium"

        diff_frame = tk.Frame(card, bg="#1E293B")
        diff_frame.pack(fill="x", padx=10, pady=(0, 4))

        tk.Label(
            diff_frame, text="Складність:", font=("Segoe UI", 10, "bold"),
            bg="#1E293B", fg="#94A3B8"
        ).pack(side="left", padx=(10, 6))

        self.arcade_diff_btns = {}
        for diff_id, diff in self.arcade_difficulties.items():
            btn = tk.Button(
                diff_frame, text=diff["label"], font=("Segoe UI", 9, "bold"),
                bg=diff["bg"] if diff_id == self.arcade_difficulty else "#334155",
                fg="white", relief="flat", padx=10, pady=2, cursor="hand2",
                command=lambda d=diff_id: self.set_arcade_difficulty(d)
            )
            btn.pack(side="left", padx=4)
            self.arcade_diff_btns[diff_id] = btn

        self.arcade_canvas = tk.Canvas(card, bg="#0B132B", bd=0, highlightthickness=0)
        self.arcade_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.arcade_running = False
        self.arcade_items = []
        self.arcade_score = 0
        self.arcade_lives = 3

    def set_arcade_difficulty(self, diff_id):
        if self.arcade_running:
            return
        self.arcade_difficulty = diff_id
        for d_id, btn in self.arcade_diff_btns.items():
            if d_id == diff_id:
                btn.configure(bg=self.arcade_difficulties[d_id]["bg"])
            else:
                btn.configure(bg="#334155")

    def toggle_arcade(self):
        if not self.arcade_running:
            self.arcade_running = True
            self.arcade_score = 0
            diff = self.arcade_difficulties[self.arcade_difficulty]
            self.arcade_lives = diff["lives"]
            self.arcade_items.clear()
            self.arcade_canvas.delete("all")
            self.arcade_btn.configure(text="⏸️ Пауза", bg="#EF4444")
            self.arcade_score_lbl.configure(text="Бали: 0")
            lives_text = "❤️" * self.arcade_lives
            self.arcade_lives_lbl.configure(text=f"Життя: {lives_text}")
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
        raw_char = random.choice(pool)

        is_upper = raw_char.isalpha() and (random.random() < 0.35)
        char = raw_char.upper() if is_upper else raw_char.lower()

        tag = f"star_{random.randint(1000, 9999)}"
        circle_color = "#8B5CF6" if is_upper else "#F59E0B"
        outline_color = "#C4B5FD" if is_upper else "#FDE047"

        circle_id = self.arcade_canvas.create_oval(
            x - 24, -48, x + 24, 0, fill=circle_color, outline=outline_color, width=2.5, tags=tag
        )
        display_text = f"★{char}" if is_upper else char
        text_id = self.arcade_canvas.create_text(
            x, -24, text=display_text, fill="#FFFFFF", font=("Segoe UI", 15, "bold"), tags=tag
        )

        item = {
            "char": char,
            "is_upper": is_upper,
            "x": x,
            "y": -24,
            "speed": random.uniform(*self.arcade_difficulties[self.arcade_difficulty]["speed"]),
            "tag": tag,
            "circle_id": circle_id,
            "text_id": text_id
        }
        self.arcade_items.append(item)

        if self.arcade_running:
            spawn_range = self.arcade_difficulties[self.arcade_difficulty]["spawn"]
            self.after(random.randint(*spawn_range), self.spawn_arcade_char)

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
                lives_max = self.arcade_difficulties[self.arcade_difficulty]["lives"]
                lives_text = "❤️" * max(0, self.arcade_lives) + "🖤" * (lives_max - max(0, self.arcade_lives))
                self.arcade_lives_lbl.configure(text=f"Життя: {lives_text}")
                if self.arcade_lives <= 0:
                    self.end_arcade_game()
                    return

        for item in to_remove:
            if item in self.arcade_items:
                self.arcade_items.remove(item)

        if lowest_item:
            self.target_char = lowest_item["char"]
            if lowest_item["char"].lower() == "ґ":
                if lowest_item["is_upper"]:
                    self.target_chars = ["SHIFT", "Ґ", "CTRL", "ALT", "Г"]
                    self.finger_hint_label.configure(
                        text="👉 ВЕЛИКА [ Ґ ]: [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г]! (+25 балів)", fg="#C084FC"
                    )
                else:
                    self.target_chars = ["Ґ", "CTRL", "ALT", "Г"]
                    self.finger_hint_label.configure(
                        text="👉 Літера [ ґ ]: кнопка [ґ] АБО [Ctrl]+[Alt]+[г]! (+15 балів)", fg="#0369A1"
                    )
            elif lowest_item["is_upper"]:
                self.target_chars = ["SHIFT", self.target_char.upper()]
                self.finger_hint_label.configure(
                    text=f"👉 ВЕЛИКА ЛІТЕРА: затисни [Shift] + [{self.target_char.lower()}]! (+25 балів)", fg="#C084FC"
                )
            else:
                self.target_chars = [self.target_char.upper()]
                self.finger_hint_label.configure(
                    text=f"👉 Мала літера: [{self.target_char}]", fg="#0369A1"
                )
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
        card.pack(fill="both", expand=True, pady=4)

        tk.Label(
            card, text="📖 Друкуємо речення з великими та малими літерами:",
            font=("Segoe UI", 12, "bold"), bg="#FFFFFF", fg="#334155"
        ).pack(pady=(10, 4))

        self.sentence_canvas = tk.Canvas(card, bg="#F8FAFC", height=70, bd=1, relief="solid")
        self.sentence_canvas.pack(fill="x", padx=25, pady=8)

        self.sent_combo_badge = tk.Label(
            card, text="", font=("Segoe UI", 11, "bold"),
            bg="#FEF3C7", fg="#92400E", padx=12, pady=2, relief="solid", bd=1
        )
        self.sent_combo_badge.pack(pady=(0, 4))

        self.sent_feedback = tk.Label(
            card, text="Друкуй символи по порядку!", font=("Segoe UI", 12),
            bg="#FFFFFF", fg="#64748B"
        )
        self.sent_feedback.pack(pady=4)

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

        if curr_char:
            self.target_char = curr_char
            is_upper = curr_char.isupper()

            if curr_char.lower() == "ґ":
                if is_upper:
                    self.target_chars = ["SHIFT", "Ґ", "CTRL", "ALT", "Г"]
                    self.sent_combo_badge.configure(
                        text="⭐ ВЕЛИКА [ Ґ ]: [ Shift ] + [ ґ ] АБО [ Ctrl ] + [ Alt ] + [ Shift ] + [ г ]",
                        bg="#FEF3C7", fg="#92400E"
                    )
                    self.finger_hint_label.configure(
                        text="👉 [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г] (якщо немає кнопки)!", fg="#4338CA"
                    )
                else:
                    self.target_chars = ["Ґ", "CTRL", "ALT", "Г"]
                    self.sent_combo_badge.configure(
                        text="🔹 Літера [ ґ ]: кнопка [ ґ ] АБО [ Ctrl ] + [ Alt ] + [ г ]",
                        bg="#E0F2FE", fg="#0369A1"
                    )
                    self.finger_hint_label.configure(
                        text="👉 Кнопка [ґ] АБО [Ctrl]+[Alt]+[г] (якщо немає кнопки)!", fg="#0369A1"
                    )
            elif is_upper:
                self.target_chars = ["SHIFT", curr_char.upper()]
                self.sent_combo_badge.configure(
                    text=f"⭐ ВЕЛИКА ЛІТЕРА: [ Shift ] + [ {curr_char.lower()} ]",
                    bg="#FEF3C7", fg="#92400E"
                )
                self.update_finger_hint_for_char(curr_char, is_uppercase=True)
            elif curr_char == " ":
                self.target_chars = ["ПРОБІЛ" if self.lang == "UA" else "SPACE"]
                self.sent_combo_badge.configure(
                    text="👉 ПРОБІЛ (великий палець)", bg="#F1F5F9", fg="#334155"
                )
                self.finger_hint_label.configure(text="👉 Натискай Пробіл", fg="#1E293B")
            else:
                self.target_chars = [curr_char.upper()]
                self.sent_combo_badge.configure(
                    text=f"🔹 Мала літера: просто [ {curr_char} ] (без Shift)",
                    bg="#E0F2FE", fg="#0369A1"
                )
                self.update_finger_hint_for_char(curr_char, is_uppercase=False)

            self.highlight_keyboard_keys(self.target_chars)

            self.sentence_canvas.create_text(
                25, 35, anchor="w",
                text=typed_part + curr_char + rest_part,
                font=("Consolas", 18), fill="#94A3B8"
            )
            self.sentence_canvas.create_text(
                25, 35, anchor="w", text=typed_part,
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
            unit_w = (w - 28) / max(14.8, total_units)

            row_pixel_w = total_units * unit_w
            x_cursor = (w - row_pixel_w) / 2

            for item in row:
                base_char = item[0]
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

                if len(base_char) == 1 and base_char.isalpha():
                    display_text = base_char.upper() if self.shift_held else base_char.lower()
                else:
                    display_text = base_char

                font_size = 9 if len(base_char) > 2 else 12
                font_weight = "bold" if len(base_char) <= 2 else "normal"
                text_id = self.kbd_canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=display_text, fill="#1E293B", font=("Segoe UI", font_size, font_weight)
                )

                key_data = {
                    "rect": rect_id,
                    "text": text_id,
                    "base_color": base_color,
                    "finger": finger_code,
                    "base_char": base_char
                }
                char_key = base_char.upper()
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

    def update_keyboard_keycap_labels(self):
        for k_char, data_list in self.key_rects.items():
            for data in data_list:
                base = data["base_char"]
                if len(base) == 1 and base.isalpha():
                    new_text = base.upper() if self.shift_held else base.lower()
                    self.kbd_canvas.itemconfig(data["text"], text=new_text)

    def highlight_keyboard_keys(self, char_list):
        for k_char, data_list in self.key_rects.items():
            for data in data_list:
                self.kbd_canvas.itemconfig(data["rect"], fill=data["base_color"], outline="#94A3B8", width=1.5)

        normalized_list = [c.upper() for c in char_list]
        for c in normalized_list:
            if c in self.key_rects:
                for data in self.key_rects[c]:
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

    # --- ОБРОБНИКИ НАТИСКАННЯ ТА ВІДПУСКАННЯ КЛАВІШ ---
    def handle_key_down(self, event):
        sym = event.keysym

        # Відстеження модифікаторів
        if sym in ("Shift_L", "Shift_R"):
            if not self.shift_held:
                self.shift_held = True
                self.update_keyboard_keycap_labels()
                self.highlight_keyboard_keys(self.target_chars)
            return
        elif sym in ("Control_L", "Control_R"):
            self.ctrl_held = True
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
                return
        elif sym in ("Alt_L", "Alt_R"):
            self.alt_held = True
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
                return
        elif sym in ("Super_L", "Super_R", "Win_L", "Win_R"):
            self.win_held = True

        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return

        typed_raw = event.char
        keysym = event.keysym

        # Спеціальна обробка комбінації Ctrl + Alt + Г для української літери 'ґ' / 'Ґ'
        is_ctrl_alt = (self.ctrl_held and self.alt_held) or (
            (event.state & 0x0004) and (event.state & 0x20000 or event.state & 0x0008)
        )
        is_g_key = (
            (event.keycode == 85)
            or (event.char and event.char.lower() in ("г", "ґ", "\x15"))
            or (event.keysym.lower() in ("u", "ukrainian_ghe", "cyrillic_ghe", "ukrainian_ghev", "ґ"))
        )

        if is_ctrl_alt and is_g_key:
            is_upper = self.shift_held or bool(event.state & 0x0001)
            typed = "Ґ" if is_upper else "ґ"
            self.flash_key("CTRL", True)
            self.flash_key("ALT", True)
            self.flash_key("Г", True)
            if is_upper:
                self.flash_key("SHIFT", True)
            self.flash_key("Ґ", True)
        elif self.mode == "hotkeys":
            self.process_hotkeys_input(event)
            return
        elif keysym == "space":
            typed = " "
        elif typed_raw:
            typed = typed_raw
        else:
            return

        self.session_typed += 1
        self.student_data["total_typed"] += 1

        if self.mode == "letters":
            self.process_letters_input(typed)
        elif self.mode == "words":
            self.process_words_input(typed)
        elif self.mode == "arcade":
            self.process_arcade_input(typed)
        elif self.mode == "sentences":
            self.process_sentences_input(typed)

    def handle_key_up(self, event):
        sym = event.keysym
        if sym in ("Shift_L", "Shift_R"):
            self.shift_held = False
            self.update_keyboard_keycap_labels()
            self.highlight_keyboard_keys(self.target_chars)
        elif sym in ("Control_L", "Control_R"):
            self.ctrl_held = False
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
        elif sym in ("Alt_L", "Alt_R"):
            self.alt_held = False
            if self.mode == "hotkeys":
                self.on_hotkey_modifier_change()
        elif sym in ("Super_L", "Super_R", "Win_L", "Win_R"):
            self.win_held = False

    def on_hotkey_modifier_change(self):
        self.highlight_keyboard_keys(self.target_chars)
        if self.hotkeys_submode == "practice" and hasattr(self, "hk_status_label"):
            hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
            hk = hotkeys_list[self.current_hotkey_idx]
            if self.ctrl_held or self.alt_held or self.shift_held:
                self.sound.play("hotkey_down")
                self.hk_status_box.configure(bg="#DCFCE7")
                self.hk_status_label.configure(
                    text=f"🟢 Чудово! [{hk['keys'][0]}] затиснуто! Тепер натисни другу клавішу!",
                    bg="#DCFCE7", fg="#15803D"
                )
            else:
                self.hk_status_box.configure(bg="#FEF3C7")
                self.hk_status_label.configure(
                    text=f"⏳ Затисни клавішу [{hk['keys'][0]}]...",
                    bg="#FEF3C7", fg="#B45309"
                )

    def process_hotkeys_input(self, event):
        hotkeys_list = HOTKEYS_DATA.get(self.lang, HOTKEYS_DATA["UA"])
        if self.hotkeys_submode == "practice":
            hk = hotkeys_list[self.current_hotkey_idx]
            target_keycodes = hk.get("keycodes", [])

            # 1. Спеціальна комбінація Ctrl + Alt + Г для літери ґ
            if hk["id"] == "ctrl_alt_g":
                is_ctrl_alt = (self.ctrl_held and self.alt_held) or (
                    (event.state & 0x0004) and (event.state & 0x20000 or event.state & 0x0008)
                )
                is_g_key = (
                    (event.keycode == 85)
                    or (event.char and event.char.lower() in ("г", "ґ", "\x15"))
                    or (event.keysym.lower() in ("u", "ukrainian_ghe", "cyrillic_ghe", "ukrainian_ghev", "ґ"))
                )
                if is_ctrl_alt and is_g_key:
                    self.sound.play("complete")
                    self.flash_key("CTRL", True)
                    self.flash_key("ALT", True)
                    self.flash_key("Г", True)
                    self.flash_key("Ґ", True)
                    self.student_data["stars"] += 2
                    self.student_data["hotkeys_mastered"] += 1
                    self.update_stats_display()
                    self.hk_status_box.configure(bg="#BBF7D0")
                    self.hk_status_label.configure(
                        text="🎉 УРА! Надруковано літеру «ґ» комбінацією Ctrl + Alt + Г! +2 ⭐",
                        bg="#BBF7D0", fg="#166534"
                    )
                    self.after(1200, self.next_hotkey)
                return

            # 2. Спеціальна комбінація Shift + будь-яка літера
            if hk["id"] == "shift_letter":
                if self.shift_held and event.char and event.char.isalpha():
                    self.sound.play("complete")
                    self.flash_key("SHIFT", True)
                    self.flash_key(event.char.upper(), True)
                    self.student_data["stars"] += 2
                    self.student_data["hotkeys_mastered"] += 1
                    self.update_stats_display()
                    self.hk_status_box.configure(bg="#BBF7D0")
                    self.hk_status_label.configure(
                        text=f"🎉 Чудово! Надруковано ВЕЛИКУ літеру '{event.char}' через Shift! +2 ⭐",
                        bg="#BBF7D0", fg="#166534"
                    )
                    self.after(1200, self.next_hotkey)
                return

            req_mod = hk["keys"][0].upper()
            mod_matched = False
            if req_mod == "CTRL" and (self.ctrl_held or (event.state & 0x0004)):
                mod_matched = True
            elif req_mod == "ALT" and (self.alt_held or (event.state & 0x20000) or (event.state & 0x0008)):
                mod_matched = True
            elif req_mod == "WIN" and self.win_held:
                mod_matched = True

            target_key = hk["keys"][-1].upper()
            key_matched = (event.keycode in target_keycodes) or (event.keysym.upper() == target_key)

            if mod_matched and key_matched:
                self.sound.play("complete")
                for k in hk["keys"]:
                    self.flash_key(k, True)
                self.student_data["stars"] += 2
                self.student_data["hotkeys_mastered"] += 1
                self.update_stats_display()

                # Автоматична дія для пісочниці при натисканні гарячої клавіші
                if hk["id"] == "ctrl_c":
                    try:
                        self.clipboard_clear()
                        self.clipboard_append(hk["sample_text"])
                        if hasattr(self, "sandbox_msg"):
                            self.sandbox_msg.configure(
                                text="📋 Скопійовано в буфер! Тепер перейди в поле вставки і натисни Ctrl + V!",
                                fg="#16A34A"
                            )
                    except Exception:
                        pass
                elif hk["id"] == "ctrl_v":
                    try:
                        clip_text = self.clipboard_get()
                        if hasattr(self, "practice_target_entry"):
                            self.practice_target_entry.delete(0, tk.END)
                            self.practice_target_entry.insert(0, clip_text)
                        if hasattr(self, "sandbox_msg"):
                            self.sandbox_msg.configure(
                                text="🎉 УРА! Текст успішно вставлено комбінацією Ctrl + V! +2 ⭐",
                                fg="#16A34A"
                            )
                    except Exception:
                        pass

                self.hk_status_box.configure(bg="#BBF7D0")
                self.hk_status_label.configure(
                    text=f"🎉 УРА! Комбінація {' + '.join(hk['keys'])} успішно виконана! +2 ⭐",
                    bg="#BBF7D0", fg="#166534"
                )
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
            elif req_mod == "SHIFT" and self.shift_held:
                mod_matched = True

            if mod_matched and ((event.keycode in target_keycodes) or (event.keysym.upper() == q_item["keys"][-1].upper())):
                self.check_quiz_answer(q_item, q_item)

    # --- ПЕРЕВІРКА ВВЕДЕННЯ ЛІТЕР ---
    def process_letters_input(self, typed):
        target = self.target_char

        # 1. ТОЧНИЙ ЗБІГ ЛІТЕРИ ТА РЕГІСТРУ
        if typed == target:
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.streak += 1
            self.student_data["stars"] += 1
            self.student_data["score"] += 10 + (self.streak * 2)

            self.flash_key(target, True)
            if target.isupper():
                self.flash_key("SHIFT", True)
            if target.lower() == "ґ":
                self.flash_key("CTRL", True)
                self.flash_key("ALT", True)
                self.flash_key("Г", True)

            if self.streak % 10 == 0:
                self.sound.play("streak")
                self.feedback_label.configure(text=f"🔥 СУПЕР! Серія {self.streak}! 🔥", fg="#EA580C")
            else:
                self.sound.play("correct")
                if target.lower() == "ґ":
                    praises = ["Чудово! Влучне введення літери Ґ! 👏", "Молодець! Літеру Ґ підкорено! 🌟"]
                elif target.isupper():
                    praises = ["Супер-комбо зі Shift! 🌟", "Чудова велика літера! 👏", "Влучно! 🎯"]
                else:
                    praises = ["Молодець! 👏", "Чудово! 🌟", "Так тримати! 🚀"]
                self.feedback_label.configure(text=random.choice(praises), fg="#16A34A")

            self.streak_label.configure(text=f"🔥 Серія: {self.streak}")
            self.update_stats_display()
            self.next_letter()

        # 2. ЛІТЕРА ПРАВИЛЬНА, АЛЕ НЕ ТОЙ РЕГІСТР
        elif typed.lower() == target.lower():
            self.streak = 0
            self.streak_label.configure(text="🔥 Серія: 0")
            self.sound.play("wrong")

            if target.lower() == "ґ":
                if target.isupper() and typed.islower():
                    self.feedback_label.configure(
                        text="⚠️ Потрібна ВЕЛИКА літера 'Ґ'! [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г]!",
                        fg="#D97706"
                    )
                else:
                    self.feedback_label.configure(
                        text="⚠️ Потрібна МАЛА літера 'ґ'! Натисни без Shift: [ґ] АБО [Ctrl]+[Alt]+[г]!",
                        fg="#D97706"
                    )
            elif target.isupper() and typed.islower():
                self.flash_key("SHIFT", False)
                self.feedback_label.configure(
                    text=f"⚠️ Майже! Потрібна ВЕЛИКА літера '{target}'! Затисни [Shift] + [{target.lower()}]!",
                    fg="#D97706"
                )
            else:
                self.flash_key(target, False)
                self.feedback_label.configure(
                    text=f"⚠️ Потрібна МАЛА літера '{target}'! Відпусти [Shift] (або вимкни CapsLock)!",
                    fg="#D97706"
                )

        # 3. ЗОВСІМ НЕ ТА ЛІТЕРА
        else:
            self.streak = 0
            self.streak_label.configure(text="🔥 Серія: 0")
            self.sound.play("wrong")
            self.flash_key(typed, False)
            if target.lower() == "ґ":
                self.feedback_label.configure(
                    text=f"Спробуй ще! Потрібна літера '{target}' (кнопка [ґ] або комбінація [Ctrl]+[Alt]+[г]), а натиснуто '{typed}'",
                    fg="#DC2626"
                )
            elif target.isupper():
                self.feedback_label.configure(
                    text=f"Спробуй ще! Потрібна ВЕЛИКА '{target}' ([Shift]+[{target.lower()}]), а натиснуто '{typed}'",
                    fg="#DC2626"
                )
            else:
                self.feedback_label.configure(
                    text=f"Спробуй ще! Потрібна мала '{target}', а натиснуто '{typed}'",
                    fg="#DC2626"
                )

    def process_words_input(self, typed):
        if self.word_index >= len(self.target_word):
            return

        expected = self.target_word[self.word_index]

        if typed == expected:
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.sound.play("correct")
            self.flash_key(expected, True)
            if expected.isupper():
                self.flash_key("SHIFT", True)
            if expected.lower() == "ґ":
                self.flash_key("CTRL", True)
                self.flash_key("ALT", True)
                self.flash_key("Г", True)

            self.word_char_labels[self.word_index].configure(
                bg="#BBF7D0", fg="#166534", bd=1, relief="solid"
            )
            self.word_index += 1
            self.update_word_highlight()
        elif typed.lower() == expected.lower():
            self.sound.play("wrong")
            if expected.lower() == "ґ":
                if expected.isupper():
                    self.word_feedback_label.configure(
                        text="⚠️ Потрібна ВЕЛИКА літера 'Ґ'! [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г]!",
                        fg="#D97706"
                    )
                else:
                    self.word_feedback_label.configure(
                        text="⚠️ Потрібна МАЛА літера 'ґ'! [ґ] АБО [Ctrl]+[Alt]+[г] (без Shift)!",
                        fg="#D97706"
                    )
            elif expected.isupper():
                self.flash_key("SHIFT", False)
                self.word_feedback_label.configure(
                    text=f"⚠️ Потрібна ВЕЛИКА літера '{expected}'! Затисни [Shift] + [{expected.lower()}]!",
                    fg="#D97706"
                )
            else:
                self.word_feedback_label.configure(
                    text=f"⚠️ Потрібна МАЛА літера '{expected}'! Відпусти [Shift]!",
                    fg="#D97706"
                )
        else:
            self.sound.play("wrong")
            self.flash_key(typed, False)
            if expected.lower() == "ґ":
                hint_str = "[ґ] або [Ctrl]+[Alt]+[г]"
            elif expected.isupper():
                hint_str = f"[Shift]+[{expected.lower()}]"
            else:
                hint_str = f"[{expected}]"
            self.word_feedback_label.configure(
                text=f"Увага! Натисни {hint_str}, а не '{typed}'", fg="#DC2626"
            )

    def process_arcade_input(self, typed):
        if not self.arcade_running:
            return

        matched_item = None
        highest_y = -999
        for item in self.arcade_items:
            if item["char"] == typed:
                if item["y"] > highest_y:
                    highest_y = item["y"]
                    matched_item = item

        if not matched_item:
            for item in self.arcade_items:
                if item["char"].lower() == typed.lower():
                    if item["y"] > highest_y:
                        highest_y = item["y"]
                        matched_item = item

        if matched_item:
            self.sound.play("correct")
            self.flash_key(typed, True)
            if matched_item["is_upper"]:
                self.flash_key("SHIFT", True)
                bonus = 25
            else:
                bonus = 15

            if matched_item["char"].lower() == "ґ":
                self.flash_key("CTRL", True)
                self.flash_key("ALT", True)
                self.flash_key("Г", True)

            self.arcade_items.remove(matched_item)
            self.arcade_canvas.delete(matched_item["tag"])
            self.arcade_score += bonus
            self.arcade_score_lbl.configure(text=f"Бали: {self.arcade_score}")
        else:
            self.sound.play("wrong")
            self.flash_key(typed, False)

    def process_sentences_input(self, typed):
        if self.sentence_index >= len(self.target_sentence):
            return

        expected = self.target_sentence[self.sentence_index]
        if typed == expected:
            self.session_correct += 1
            self.student_data["correct_typed"] += 1
            self.sound.play("correct")
            if expected.isupper():
                self.flash_key("SHIFT", True)
            if expected.lower() == "ґ":
                self.flash_key("CTRL", True)
                self.flash_key("ALT", True)
                self.flash_key("Г", True)
            self.sentence_index += 1
            self.render_sentence_text()
        elif typed.lower() == expected.lower():
            self.sound.play("wrong")
            if expected.lower() == "ґ":
                if expected.isupper():
                    self.sent_feedback.configure(
                        text="⚠️ Потрібна ВЕЛИКА 'Ґ'! [Shift]+[ґ] АБО [Ctrl]+[Alt]+[Shift]+[г]",
                        fg="#D97706"
                    )
                else:
                    self.sent_feedback.configure(
                        text="⚠️ Потрібна МАЛА 'ґ'! [ґ] АБО [Ctrl]+[Alt]+[г]",
                        fg="#D97706"
                    )
            elif expected.isupper():
                self.sent_feedback.configure(
                    text=f"⚠️ Потрібна ВЕЛИКА літера '{expected}'! Затисни [Shift] + [{expected.lower()}]",
                    fg="#D97706"
                )
            else:
                self.sent_feedback.configure(
                    text=f"⚠️ Потрібна МАЛА літера '{expected}' (без Shift)", fg="#D97706"
                )
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
