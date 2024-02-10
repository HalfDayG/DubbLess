import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
import subprocess
import sys
from ttkthemes import ThemedStyle
import threading
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from PIL import Image, ImageTk, ImageGrab
import json
import webbrowser

# Файл для сохранения настроек
settings_file = "settings.json"

class ConsoleRedirector(object):
    def __init__(self, widget):
        self.widget = widget
        self.current_line = ''

    def write(self, text):
        if '\r' in text:
            self.current_line = text.rstrip('\r')
            self.widget.delete("end-1l linestart", "end-1l lineend")
            self.widget.insert("end-1c", self.current_line)
        else:
            self.current_line = ''
            self.widget.insert(tk.END, text)
        self.widget.see(tk.END)

    def flush(self):
        pass

# Создаем кнопку настроек
def resource_path(relative_path):
    """ Получить абсолютный путь к ресурсу, работает как для разработки, так и для одного исполняемого файла """
    try:
        # PyInstaller создает временную папку и сохраняет путь в переменной _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Функция для сохранения настроек в файл
def save_settings():
    settings = {
        "domain": domain_entry.get(),
        "token_vk": token_vk_entry.get(),
        "image_path": image_path_entry.get(),
        "source_path": source_path_entry.get(),
        "duplicate_path": duplicate_path_entry.get()
    }
    with open(settings_file, "w") as file:
        json.dump(settings, file)

# Функция для загрузки настроек из файла
def load_settings():
    # Значения по умолчанию
    default_settings = {
        "domain": "ijiranaidenagatorosan",
        "token_vk": "",
        "image_path": "images",
        "source_path": "source.txt",
        "duplicate_path": "."
    }

    if os.path.exists(settings_file):
        with open(settings_file, "r") as file:
            settings = json.load(file)
    else:
        settings = default_settings

    # Устанавливаем значения, используя значения по умолчанию, если значение отсутствует или пусто
    domain_entry.delete(0, tk.END)
    domain_value = settings.get("domain") if settings.get("domain", None) else default_settings["domain"]
    domain_entry.insert(0, domain_value)

    token_vk_entry.delete(0, tk.END)
    token_vk_value = settings.get("token_vk") if settings.get("token_vk", None) else default_settings["token_vk"]
    token_vk_entry.insert(0, token_vk_value)

    image_path_entry.delete(0, tk.END)
    image_path_value = settings.get("image_path") if settings.get("image_path", None) else default_settings["image_path"]
    image_path_entry.insert(0, image_path_value)

    source_path_entry.delete(0, tk.END)
    source_path_value = settings.get("source_path") if settings.get("source_path", None) else default_settings["source_path"]
    source_path_entry.insert(0, source_path_value)

    duplicate_path_entry.delete(0, tk.END)
    duplicate_path_value = settings.get("duplicate_path") if settings.get("duplicate_path", None) else default_settings["duplicate_path"]
    duplicate_path_entry.insert(0, duplicate_path_value)




#### Скачивание изображений

def download_image(url, file_name, callback, photo_id, ii):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_name, 'wb') as f:
                f.write(response.content)
            callback(f"Скачан файл {photo_id}\n", end='\r')
            view_label.config(text=f"\nСкачан файл {ii}", foreground="yellow")
    except Exception as e:
        callback(f"Ошибка при скачивании {file_name}: {e}\n", end='\r')
        view_label.config(text=f"Ошибка при скачивании файла:\n{file_name}", foreground="red")

def download_images(callback, domain_entry, token_vk_entry, image_path_entry):
    global stop_threads
    global code_start
    ii = 0
    domain = domain_entry.get()
    tokenVK = token_vk_entry.get()
    image_dir = image_path_entry.get()

    if not tokenVK:
        callback(f"Не указан Сервисный ключ доступа VK")
        view_label.config(text="\nНе указан Сервисный ключ доступа VK", foreground="red")
        code_start = False
        return

    base_url = f'https://api.vk.com/method/wall.get?domain={domain}&count=100&access_token={tokenVK}&v=5.131'
    total = requests.get(base_url).json()['response']['count']
    callback("----------------------------------")
    callback(f"Начато скачивание изображений\nВсего постов: {total}")
    callback("----------------------------------")
    view_label.config(text=f"Начато скачивание изображений\nВсего постов: {total}", foreground="green")
    faf = 0

    with requests.Session() as session:
        initial_response = session.get(base_url).json()
        total_count = initial_response['response']['count']

        num_batches = (total_count - 1) // 100 + 1

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        existing_files = set(os.listdir(image_dir))
        futures = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(num_batches):
                if stop_threads:
                    break

                offset = i * 100
                batch_url = f'{base_url}&offset={offset}'
                response_batch = session.get(batch_url).json()

                for item in response_batch['response']['items']:
                    if 'attachments' in item and item['attachments']:
                        for attachment in item['attachments']:
                            if attachment['type'] == 'photo':
                                if not stop_threads:
                                    largest_photo = max(attachment['photo']['sizes'], key=lambda size: size['width']*size['height'])
                                    photo_id = attachment['photo']['id']
                                    file_name = f"{domain}_{photo_id}.jpg"

                                    if file_name not in existing_files:
                                        file_path = os.path.join(image_dir, file_name)
                                        ii+=1
                                        futures.append(executor.submit(download_image, largest_photo['url'], file_path, callback, photo_id, ii))
                                    else:
                                        faf += 1
                                        callback(f"Пропущены файлы {faf} шт. Файлы уже есть в базе.", end='\r')
                                        view_label.config(text=f"\nПропущены файлы {faf} шт. Файлы уже есть в базе.", foreground="yellow")

            # Ожидание завершения всех задач
            for future in as_completed(futures):
                if stop_threads:
                    # Очистка оставшихся задач
                    for f in futures:
                        f.cancel()
                    break

        # Проверка после выхода из цикла
        if stop_threads:
            callback("\nПроцесс скачивания изображений остановлен.")
            view_label.config(text="\nПроцесс скачивания изображений остановлен", foreground="yellow")
        else:
            callback("\nСкачивание изображений завершено.\n")
            view_label.config(text="\nСкачивание изображений завершено", foreground="green")
        code_start = False

#### Скачивание источников

def download_sources(callback, domain_entry, token_vk_entry, source_path_entry):
    global stop_threads
    global code_start

    domain = domain_entry.get()
    tokenVK = token_vk_entry.get()
    source_dir = source_path_entry.get()

    if not tokenVK:
        print("Не указан Сервисный ключ доступа VK")
        view_label.config(text="\nНе указан Сервисный ключ доступа VK", foreground="red")
        code_start = False
        return

    base_url = f'https://api.vk.com/method/wall.get?domain={domain}&count=100&access_token={tokenVK}&v=5.131'
    total_count = requests.get(base_url).json()['response']['count']
    num_batches = (total_count - 1) // 100 + 1

    links = []

    callback("----------------------------------")
    callback(f"Скачивание источников\nВсего постов: {total_count}")
    callback("----------------------------------")
    view_label.config(text=f"\nСкачивание источников", foreground="green")

    def process_batch(offset, attempt=1):
        global stop_threads

        if stop_threads:  # Проверка флага
            return []

        try:
            url_batch = f'{base_url}&offset={offset}'
            response_batch = requests.get(url_batch).json()

            if 'response' in response_batch:
                batch_links = [item['copyright']['link']
                               for item in response_batch['response']['items']
                               if 'copyright' in item]
                return batch_links
            else:
                raise ValueError("API response error")

        except ValueError as e:
            if attempt <= 3:  # Retry up to 3 times
                time.sleep(2 ** attempt)  # Exponential backoff
                return process_batch(offset, attempt + 1)
            else:
                callback(f"Не удалось обработать партию по смещению {offset}: {e}")
                view_label.config(text="\nОшибка", foreground="red")
                return []

    with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced number of workers
        futures = [executor.submit(process_batch, i * 100) for i in range(num_batches)]

        for i, future in enumerate(futures):
            if stop_threads:  # Проверка флага
                break
            links.extend(future.result())
            callback(f"Найдено {len(links)} источников из {total_count}", end='\r')
            view_label.config(text=f"\nНайдено {len(links)} источников", foreground="yellow")

    if not stop_threads:
        with open(source_dir, 'w') as f:
            for link in links:
                f.write(link + '\n')

        callback(f"Источников скачано: {len(links)}, всего постов: {total_count}", end='\r')
        view_label.config(text=f"\nИсточников скачано: {len(links)}", foreground="green")
    else:
        callback("\nПроцесс скачивания прерван.")
        view_label.config(text="\nПроцесс скачивания прерван", foreground="yellow")
    code_start = False



dubble_file = ""

#### Поиск дубликатов

def poisk_img(callback, image_path_entry, duplicate_path_entry):
    global stop_threads
    global code_start
    global dubble_file

    directory = image_path_entry.get()
    dupl_dir = duplicate_path_entry.get()
    def dhash(image, hash_size=8):
        # Проверка, что image является объектом изображения
        if not isinstance(image, Image.Image):
            raise ValueError("Переданный объект не является изображением PIL.Image")

        resized = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())

        difference = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                difference.append(pixel_left > pixel_right)

        decimal_value = 0
        hex_string = []
        for index, value in enumerate(difference):
            if value:
                decimal_value += 2**(index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
                decimal_value = 0

        return ''.join(hex_string)


    def check_image_similarity(image_path, target_hash, threshold, update_progress, image_found_flag):
        global image_found
        global dubble_file
        if image_found_flag[0]:  # Проверка флага
            return False

        if stop_threads:

            return
        try:
            with Image.open(image_path) as img:
                img_hash = dhash(img)
                if hamming_distance(target_hash, img_hash) <= threshold:
                    callback(f"\n----------------------------------\nНайдено похожее изображение:\n{image_path}\n----------------------------------")
                    dubble_file = os.path.basename(image_path)
                    # dubble_file = image_path
                    os.startfile(image_path)
                    image_found_flag[0] = True  # Установка флага
                    return True
        except IOError:
            callback(f"Битый файл: '{image_path}'. Удаление файла.\n", end='\r')
            view_label.config(text=f"Удаление битого файла:\n'{image_path}'", foreground="red")
            os.remove(image_path)
        finally:
            update_progress()

        return False
    # В начале поиска устанавливаем флаг в False
    image_found_flag = [False]

    def hamming_distance(s1, s2):
        if len(s1) != len(s2):
            raise ValueError("Undefined for sequences of unequal length")
        return sum(el1 != el2 for el1, el2 in zip(s1, s2))

    root_image_path = None
    for filename in os.listdir(dupl_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')):
            root_image_path = filename
            break

    if root_image_path is None:
        image = ImageGrab.grabclipboard()
        if image is None:
            callback("Изображение не найдено, ни в буфере обмена, ни в папке.\n")
            view_label.config(text=f"\nВыберите изображение для поиска", foreground="yellow")
            code_start = False
            return
    else:
        image = Image.open(root_image_path)

    target_hash = dhash(image)

    # Чуствительность поиска
    threshold = 5
    try:
        image_files = [os.path.join(directory, f) for f in os.listdir(directory)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'))]
    except Exception as e:
        if "Системе не удается найти указанный путь:" in str(e):
            callback(f"Системе не удается найти указанный путь к папке {directory}.\nВозможно база еще не была скачана.\n")
            view_label.config(text="\nНе найдена база изображений", foreground="red")
            code_start = False
            return
        else:
            callback(f"Произошла ошибка: {e}\n")
            view_label.config(text="\nОшибка", foreground="red")
            code_start = False
            return
    total_images = len(image_files)
    current_image_number = 0


    def update_progress():
            nonlocal current_image_number
            current_image_number += 1
            if current_image_number % 20 == 0 or current_image_number == total_images:
                callback(f"Проверка изображений {current_image_number}/{total_images}...", end='\r')
                view_label.config(text=f"Проверка изображений\n{current_image_number}/{total_images}", foreground="yellow")


    callback("----------------------------------")
    callback(f"Начат поиск похожих изображений\nВсего: {total_images}")
    callback("----------------------------------")
    view_label.config(text=f"Поиск дубликатов.\nВсего: {total_images}", foreground="green")

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for f in image_files:
            if stop_threads:  # Проверка флага перед запуском нового задания
                break
            futures.append(executor.submit(check_image_similarity, f, target_hash, threshold, update_progress, image_found_flag))

        results = []
        for future in futures:
            if stop_threads:  # Проверка флага перед ожиданием завершения задания
                break
            results.append(future.result())

    if stop_threads:
        callback("\nПоиск остановлен.\n")
        view_label.config(text=f"\nПоиск остановлен", foreground="yellow")
    elif not any(results):
        callback("\nПохожих изображений не найдено.\n")
        view_label.config(text=f"\nПохожих изображений не найдено", foreground="green")
    else:
        callback("\nПоиск завершен.\n")
        view_label.config(text=f"Найдено похожее изображение:\n{dubble_file}", foreground="green")
    code_start = False





def update_console(message, end='\n'):
    # Включить редактирование для обновления текста
    console_text.config(state=tk.NORMAL)

    if end == '\r':
        # Перемещение курсора в начало текущей строки
        console_text.mark_set("insert", "end-1c linestart")
        # Удаление текущей строки
        console_text.delete("insert", "end-1c")

    # Вставка нового сообщения
    console_text.insert(tk.END, message)
    if end != '\r':
        console_text.insert(tk.END, end)

    # Прокрутка до конца текста
    console_text.see(tk.END)

    # Отключить редактирование после обновления текста
    console_text.config(state=tk.DISABLED)

code_start = False
def run_script(script_name):
    def target():
        global stop_threads
        global code_start
        stop_threads = False
        save_settings()
        load_settings()
        if code_start == False:
            # Очистка консоли перед выполнением скрипта
            console_text.config(state=tk.NORMAL)
            console_text.delete("1.0", tk.END)
            console_text.config(state=tk.DISABLED)

            if script_name == "down_img.py":
                code_start = True
                download_images(update_console, domain_entry, token_vk_entry, image_path_entry)
            elif script_name == "down_sour.py":
                code_start = True
                download_sources(update_console, domain_entry, token_vk_entry, source_path_entry)
            elif script_name == "poisk.py":
                code_start = True
                poisk_img(update_console, image_path_entry, duplicate_path_entry)
            # Добавьте здесь обработку для других скриптов

    threading.Thread(target=target).start()



root = tk.Tk()
root.title("DubbLess")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
# Установка размеров и центрирование окна
window_width = 600
window_height = 500
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x_coordinate = (screen_width - window_width) // 2
y_coordinate = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

# Запрет на изменение размеров окна
root.resizable(False, False)


style = ThemedStyle(root)
style.set_theme("black")
style.configure("Vertical.TScrollbar", gripcount=0,
                background="#333", troughcolor="#222",
                bordercolor="#333", arrowcolor="#fff",
                lightcolor="#333", darkcolor="#333",
                relief="flat")

style.element_create("Round.Vertical.Scrollbar.trough", "from", "default")
style.layout("Vertical.TScrollbar",
    [('Round.Vertical.Scrollbar.trough', {'children':
        [('Vertical.Scrollbar.uparrow', {'side': 'top', 'sticky': ''}),
         ('Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': ''}),
         ('Vertical.Scrollbar.thumb', {'unit': '1', 'children':
            [('Vertical.Scrollbar.grip', {'sticky': ''})],
            'sticky': 'nswe'})],
        'sticky': 'ns'})])

bg_color = "#333"
root.configure(bg=bg_color)

# Создание фрейма для кнопок
buttons_subframe = ttk.Frame(root)
buttons_subframe.pack(side="bottom", fill="x")

buttons_frame = ttk.Frame(root)
buttons_frame.pack(side="left", fill="y")

description_frame = ttk.Frame(root)
description_frame.pack(side="bottom", fill="both", expand=True)

def stop_process():
    global stop_threads
    stop_threads = True

def toggle_settings():
    if settings_frame.winfo_viewable():
        settings_frame.pack_forget()  # Скрыть панель настроек
        image_label.pack(side="left", fill="none", expand=False)  # Показать image_label
        console_text.pack_forget()
        save_settings()  # Сохранить настройки при закрытии панели
        load_settings()
    else:
        settings_frame.pack(after=buttons_subframe, fill="x")  # Показать панель настроек
        image_label.pack_forget()  # Скрыть image_label
        console_text.pack(side="left", fill="both", expand=True)

# Создание фрейма для текста и скроллбара
text_subframe = ttk.Frame(buttons_subframe)
text_subframe.pack(side="bottom", fill="x")

style = ttk.Style()
style.configure('Large1.TButton', anchor="center", font=("Helvetica", 14))

# Создание разделительной полосы
separator = ttk.Separator(buttons_subframe, orient='horizontal')
separator.pack(side="top", fill='x', expand=True)

# Создание Label с цветным текстом
view_label = tk.Label(buttons_subframe, text="\n", fg="green", bg="#424242", font=("Open Sans", 12), anchor="center")
view_label.pack(side="top", expand=True, fill="both")

# Создание кнопки Стоп
stop_button = ttk.Button(buttons_subframe, text="Стоп", command=stop_process, style="Large1.TButton", width=19)
stop_button.pack(side="left", expand=True, pady=5)

# Создание Text и Scrollbar для описания
description_text = tk.Text(text_subframe, wrap=tk.WORD, background="#333", foreground="#fff", font=("Helvetica", 10), height=4)
description_text.pack(side="bottom", fill="x", expand=False)

description_text.insert(tk.END, "DubbLess v1.2 by HalfDay")


def update_description(description):
    description_text.delete(1.0, tk.END)
    description_text.insert(tk.END, description)

open_icon_path = resource_path("icon-open.png")
open_icon = tk.PhotoImage(file=open_icon_path)
open_icon = open_icon.subsample(25, 25)

def open_images():
    try:
        os.startfile(image_path_entry.get())
    except Exception as e:
        if "Не удается найти указанный файл" in str(e):
            print(f"Системе не удается найти указанный путь к папке {image_path_entry.get()}\nВозможно база еще не была скачана.\n")
            return
        else:
            print(f"Произошла ошибка: {e}\n")
            return
def open_source():
    try:
        os.startfile(source_path_entry.get())
    except Exception as e:
        if "Не удается найти указанный файл" in str(e):
            print(f"Системе не удается найти указанный путь к файлу {source_path_entry.get()}\nВозможно источники еще не были скачаны.\n")
            return
        else:
            print(f"Произошла ошибка: {e}\n")
            return
def open_root():
    try:
        os.startfile(duplicate_path_entry.get())
    except Exception as e:
        if "Не удается найти указанный файл" in str(e):
            print(f"Системе не удается найти указанный путь {duplicate_path_entry.get()}")
            return
        else:
            print(f"Произошла ошибка: {e}\n")
            return

button_commands = [
    ("Скачать изображения", "down_img.py", "Обновляет базу скаченных изображений со всех постов сообщества вк в указанную папку.\nПо умолчанию это папка images.\nУже имеющиеся изображения не перезаписываются, а пропускаются."),
    ("Скачать источники", "down_sour.py", "Скачивает источники со всех постов сообщества вк в файл source.txt.\nПуть к файлу можно изменить.\nФайл каждый раз перезаписывается."),
    ("Поиск дубликата", "poisk.py", 'Ищет дубликат среди базы скаченных изображений.\nДубликат ищется по файлу (путь можно изменить) или буферу обмена (необходимо скопировать изображение).'),
]

open_functions = [open_images, open_source, open_root]

def find_first_image(directory):
    """Find the first image in the given directory."""
    for file in os.listdir(directory):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return os.path.join(directory, file)
    return None

def update_image():
    try:
        image_file = find_first_image('.')
        if image_file:
            image = Image.open(image_file)
        else:
            image = ImageGrab.grabclipboard()

        if image:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            image_label.config(image=photo)
            image_label.image = photo
        else:
            image_label.config(image='', text="No Image", bg="#333333")
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")

    root.after(2000, update_image)

for (text, script, description), open_func in zip(button_commands, open_functions):
    button_frame = ttk.Frame(buttons_frame)
    button_frame.pack(fill="x", padx=10, pady=5)

    btn = ttk.Button(button_frame, text=text, command=lambda script_name=script: run_script(script_name), style="Large.TButton", width=20)
    btn.pack(side="left")
    btn.bind("<Enter>", lambda e, desc=description: update_description(desc))

    icon_btn = ttk.Button(button_frame, image=open_icon, command=open_func)
    icon_btn.pack(side="left")

settings_icon_path = resource_path("icon-gear.png")
settings_icon = tk.PhotoImage(file=settings_icon_path)
settings_icon = settings_icon.subsample(17, 17)

settings_button_frame = ttk.Frame(buttons_frame)
settings_button_frame.pack(side="bottom", fill="x", padx=10, pady=5)

settings_btn = ttk.Button(settings_button_frame, image=settings_icon, command=toggle_settings)
settings_btn.pack(side="left", anchor='w', pady=5)

image_frame = ttk.Frame(root)
image_frame.pack(side="right", fill="both", expand=True)

max_size = (310, 350)
placeholder_image = Image.new('RGB', max_size, color=(51,51,51))  # Dark placeholder
placeholder_photo = ImageTk.PhotoImage(placeholder_image)
image_label = tk.Label(image_frame, image=placeholder_photo, bg="#333333")  # Dark background
image_label.photo = placeholder_photo  # Keep a reference
image_label.pack(side="left", fill="none", expand=False)

image_label.config(width=max_size[0], height=max_size[1])

root.after(2000, update_image)

# Настройка стиля виджетов
style.configure("Dark.TEntry", fieldbackground="#555", foreground="#fff", borderwidth=0)

# Панель настроек
settings_frame = ttk.Frame(root)

# Функции для выбора пути через проводник
def choose_image_path():
    path = filedialog.askdirectory(initialdir="images")
    image_path_entry.delete(0, tk.END)
    image_path_entry.insert(0, path)
    save_settings()
def choose_source_path():
    path = filedialog.askopenfilename(initialdir=".", filetypes=[("Text files", "*.txt")])
    source_path_entry.delete(0, tk.END)
    source_path_entry.insert(0, path)
    save_settings()
def choose_duplicate_path():
    path = filedialog.askdirectory(initialdir=".")
    duplicate_path_entry.delete(0, tk.END)
    duplicate_path_entry.insert(0, path)
    save_settings()
def open_vk_dev_site():
    url = "https://dev.vk.com/ru/mini-apps/management/settings"
    webbrowser.open(url)

# Настройка стиля для маленького текста Label
style.configure("Small.TLabel", foreground="#fff", font=('Helvetica', 10))

# Настройка столбцов для центрирования надписи "Настройки"
settings_frame.columnconfigure(0, weight=0)
settings_frame.columnconfigure(1, weight=0)
settings_frame.columnconfigure(2, weight=0)

# Надпись "Настройки" в центральном столбце
ttk.Label(settings_frame, text="Настройки", style="Small.TLabel").grid(row=0, column=1)



# Поля для ввода настроек в панели настроек
ttk.Label(settings_frame, text="Id сообщества:", style="Small.TLabel", anchor="e").grid(row=1, column=0, sticky='e')
domain_entry = ttk.Entry(settings_frame, style="Dark.TEntry")
domain_entry.grid(row=1, column=1)

ttk.Label(settings_frame, text="Сервисный ключ доступа VK:", style="Small.TLabel", anchor="e").grid(row=2, column=0, sticky='e')
token_vk_entry = ttk.Entry(settings_frame, style="Dark.TEntry")
token_vk_entry.grid(row=2, column=1)
ttk.Button(settings_frame, text="Получить", command=open_vk_dev_site).grid(row=2, column=2)

ttk.Label(settings_frame, text="Путь к базе изображений:", style="Small.TLabel", anchor="e").grid(row=3, column=0, sticky='e')
image_path_entry = ttk.Entry(settings_frame, style="Dark.TEntry")
image_path_entry.grid(row=3, column=1)
ttk.Button(settings_frame, text="Выбрать", command=choose_image_path).grid(row=3, column=2)

ttk.Label(settings_frame, text="Путь к источникам:", style="Small.TLabel", anchor="e").grid(row=4, column=0, sticky='e')
source_path_entry = ttk.Entry(settings_frame, style="Dark.TEntry")
source_path_entry.grid(row=4, column=1)
ttk.Button(settings_frame, text="Выбрать", command=choose_source_path).grid(row=4, column=2)

ttk.Label(settings_frame, text="Путь к папке с проверяемым артом:", style="Small.TLabel", anchor="e").grid(row=5, column=0, sticky='e')
duplicate_path_entry = ttk.Entry(settings_frame, style="Dark.TEntry")
duplicate_path_entry.grid(row=5, column=1)
ttk.Button(settings_frame, text="Выбрать", command=choose_duplicate_path).grid(row=5, column=2)

# Добавление отступа
ttk.Label(settings_frame, text="", style="Small.TLabel").grid(row=6, column=0, pady=0)

# Создание Text и Scrollbar для консоли
console_text = tk.Text(image_frame, wrap=tk.WORD, background="#111", foreground="#fff", font=("Consolas", 10), state=tk.DISABLED)
console_scrollbar = ttk.Scrollbar(image_frame, orient="vertical", command=console_text.yview, style="Vertical.TScrollbar")
console_text.configure(yscrollcommand=console_scrollbar.set)
sys.stdout = ConsoleRedirector(console_text)
sys.stderr = sys.stdout
load_settings()

style.configure("Large.TButton", font=("Helvetica", 14))
style.configure("TButton", relief="flat", borderwidth=0)
style.map("TButton", background=[("active", "#555")], highlightthickness=[(("active",), 0)])

icon_path = resource_path('icon.ico')
root.iconbitmap(icon_path)

root.mainloop()
