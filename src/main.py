import yt_dlp
import os
import json
import hashlib
import random
import threading

import flet as ft
import flet_video as ftv

from datetime import datetime
from typing import List, Dict, Optional
from pprint import pprint


#https://gallery.flet.dev/icons-browser/

#Server returned HTTP response code: 503 for URL: https://github.com/media-kit/libmpv-android-video-build/releases/download/v1.1.7/default-arm64-v8a.jar
#pub.dev/media_kit_libs_android_video-1.3.8/android/build.gradle
#Server returned HTTP response code: 503 for URL:
# Константы
APP_NAME = "Video Downloader"

temp_dir = os.getenv("FLET_APP_STORAGE_TEMP")
data_dir = os.getenv("FLET_APP_STORAGE_DATA")

SETTINGS_FILE = os.path.join(data_dir, "settings.json")
HISTORY_FILE = os.path.join(data_dir, "history.json")
QUEUE_FILE = os.path.join(data_dir, "queue.json")

FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'bin', 'ffmpeg')

#--ffmpeg-location


def stable_string_hash(input_string, algorithm='sha1'):
    """
    Generates a stable hash for a string using a specified cryptographic algorithm.

    Args:
        input_string (str): The string to be hashed.
        algorithm (str): The name of the hashing algorithm (e.g., 'md5', 'sha1', 'sha256', 'sha512').

    Returns:
        str: The hexadecimal representation of the stable hash.
    """
    # Ensure the input is encoded to bytes, as hashlib functions expect bytes
    encoded_string = input_string.encode('utf-8')

    # Get the hash object for the specified algorithm
    hasher = hashlib.new(algorithm)

    # Update the hasher with the encoded string
    hasher.update(encoded_string)

    # Return the hexadecimal digest of the hash
    return hasher.hexdigest()

def gen_uid(string: str):
    return str(stable_string_hash(string))

def rand_uid():
    return random.getrandbits(100)

class ForceDownloadClass:
    def start_download(self, e: ft.ControlEvent, fmt: dict):
        # Добавляем в очередь
        self.add_to_queue(self.current_url, fmt)
        # Переходим на страницу очереди
        self.page.go("/queue")
        
        # Запускаем скачивание с повторами в отдельном потоке
        self.page.run_thread(
            self.download_with_retries,
            self.current_url,
            fmt,
            max_retries=3,      # макс. число попыток
            delay_seconds=5     # задержка между попытками (сек)
        )

    def download_with_retries(
        self,
        url: str,
        fmt: dict,
        max_retries: int = 3,
        delay_seconds: int = 5
    ):
        """
        Выполняет download_video с повторными попытками при ошибках.
        """
        for attempt in range(1, max_retries + 1):
            try:
                self.download_video(url, fmt)
                # Если успешно — выходим из цикла
                return
            except Exception as exc:
                # Логируем ошибку
                print(f"Попытка {attempt} не удалась: {exc}")
                
                # Если это последняя попытка — поднимаем исключение
                if attempt == max_retries:
                    print("Все попытки исчерпаны. Загрузка не удалась.")
                    # Можно обновить UI: показать ошибку пользователю
                    self.update_ui_on_failure(url, exc)
                    return
                
                # Ждём перед следующей попыткой
                time.sleep(delay_seconds)

    def download_video(self, url: str, fmt: dict):
        """
        Основная логика скачивания (пример).
        Должна выбрасывать исключение при ошибке.
        """
        # Здесь ваш код скачивания
        # Если ошибка — raise Exception("...")
        pass

    def update_ui_on_failure(self, url: str, error: Exception):
        """
        Обновляет UI при окончательной неудаче.
        Например, меняет статус в очереди, показывает уведомление.
        """
        # Пример: обновить элемент в очереди
        for item in self.queue_items:
            if item.url == url:
                item.status = f"Ошибка: {str(error)}"
                break
        
        # Обновить интерфейс
        self.page.update()

class VideoDownloader:
    def __init__(self):
        self.page: ft.Page = None
        self.settings = self.load_settings()
        self.history = self.load_history()
        self.queue = self.load_queue()
        self.formats = []
        self.current_url = ""
        #self.progress = ft.ProgressBar(visible=True, value=0, bar_height=2)
        #ft.Ref[ft.Column]()

        #self.progress.current.controls.append(
        #    ft.ProgressBar(width=(page.width-120), visible=False),
        #)

    def bottom_nav(self):
        return ft.BottomAppBar(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.HOME,
                        tooltip="Главная",
                        on_click=lambda _: self.page.go("/"),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.LIST,
                        tooltip="История",
                        on_click=lambda _: self.page.go("/history"),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.QUEUE,
                        tooltip="Очередь",
                        on_click=lambda _: self.page.go("/queue"),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS,
                        tooltip="Настройки",
                        on_click=lambda _: self.page.go("/settings"),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
        )

    def load_settings(self) -> Dict:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"download_path": temp_dir}

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)

    def load_history(self) -> List[Dict]:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def load_queue(self) -> List[Dict]:
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                    q = json.load(f)
                    for e in q:
                        if 'status' in e and e['status']=='pending':
                            e['status'] = 'cancelled'
                        if 'progress' in e:
                            #visible = bool(e['progress'] and e['progress'] != 1)
                            e['progress'] = ft.ProgressBar(visible=False, bar_height=2, value=e['progress'])
                        else:
                            e.setdefault('progress', ft.ProgressBar(visible=False, bar_height=2))
                    return q
            except:
                return []
        return []

    def save_queue(self):
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            queue = []
            for e in self.queue:
                s = e.copy()
                if 'progress' in s:
                    s['progress'] = s['progress'].value
                    #del s['progress']
                queue.append(s)
            json.dump(queue, f, indent=2)

    def add_to_history(self, url: str, fmt: dict):
        #title: str, format_id: str, filepath: str

        self.history.append({
            "url": url,
            "title": fmt['title'],
            "format_id": fmt['format_id'],
            "filepath": fmt['filepath'],
            "thumbnail": fmt.get('thumbnail'),
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()

    def add_to_queue(self, url: str, fmt: dict):
        # url: str, title: str, format_id: str
        # title, format_id
        title = fmt['title']
        format_id = fmt['format_id']
        thumbnail = fmt['thumbnail']

        uid = gen_uid(url+format_id)
        self.queue.insert(0, {
            "url": url,
            "uid": uid,
            "title": title,
            "format_id": format_id,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
            "thumbnail": thumbnail,
            "progress": ft.ProgressBar(visible=True, bar_height=2),
        })
        self.save_queue()

    def get_formats(self, url: str) -> List[Dict]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = []
                #print(" ")
                #pprint(info)
                #print(" ")
                thumbnail = info.get('thumbnail')
                for f in info['formats']:
                    #pprint(f)
                    if (f.get('format_note') or f.get('format')) and f.get('ext'):
                        #uid = gen_uid(url+f['format_id'])
                        formats.append({
                            'format_id': f['format_id'],
                            'uid': gen_uid(url+f['format_id']),
                            'title': info.get('title'),
                            'ext': f['ext'],
                            'format_note': (f.get('format_note') or f.get('format')),
                            'filesize': f.get('filesize'),
                            'fps': f.get('fps'),
                            'progress': ft.ProgressBar(visible=True, value=0, bar_height=2),
                            'thumbnail': thumbnail,
                        })
                return sorted(formats, key=lambda x: (x['filesize'] or 0), reverse=True)
        except Exception as e:
            #print(f"!Error fetching formats: {e}")
            return []

    def download_video(self, url: str, fmt: dict) -> bool:
        # format_id: str
        format_id = fmt['format_id']
        uid=gen_uid(url+format_id)
        if not self.settings["download_path"]:
            self.show_snackbar("Укажите папку для сохранения в настройках!")
            return False

        for item in self.queue:
            if item["uid"] == uid:
                item['progress'].visible = True
                item['progress'].value=None
        self.page.update()

        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(self.settings["download_path"], '%(title)s_%(format_id)s.%(ext)s'),
            'progress_hooks': [self.progress_hook(uid)],
            'ffmpeg_location': FFMPEG_PATH,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown Title')
                filepath = ydl.prepare_filename(info)
                fmt['title'] = title
                fmt['filepath'] = filepath
                self.add_to_history(url, fmt)
                self.update_queue_status(url, format_id, "completed")
                self.show_snackbar(f"Скачан успешно: {title}")
                return True
        except Exception as e:
            self.update_queue_status(url, format_id, f"Ошибка скачивания: {str(e)}")
            self.show_snackbar(f"Ошибка скачивания: {e}", ft.Colors.RED)
            #raise Exception(f"Ошибка скачивания: {str(e)}")
            return False

    def progress_hook(self, uid):
        def _(d):
            #pprint(d)
            #https://rutube.ru/video/6f27ea5aebdea7445203679d8f1d508d/
            if d['status'] == 'downloading':

                percent = d.get('_percent_str', '0%')
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded = d.get('downloaded_bytes', 0)
                progress = downloaded / total if total else 0
                #self.progress.value = progress
                for i in (filter(lambda e: e['format_id']==d['info_dict']['format_id'] and uid==e['uid'], self.queue)):
                    i['progress'].value = progress

                self.page.session.set("download_progress", percent)
                self.page.update()
            elif d['status'] == 'finished':
                for i in (filter(lambda e:e.get('progress') and e['format_id']==d['info_dict']['format_id'] and uid==e['uid'], self.queue)):
                    i['progress'].visible = False
                    i['progress'].value = 1
                self.page.update()
        return _



    def update_queue_status(self, url: str, format_id: str, status: str):
        for item in self.queue:
            if item["url"] == url and item["format_id"] == format_id:
                item["status"] = status
                item["updated"] = datetime.now().isoformat()
        #pprint(self.queue)
        self.save_queue()
        self.refresh_queue_page()

    def show_snackbar(self, message: str, color=None):
        #self.page.snackbar = ft.SnackBar(
        #    content=ft.Text(message),
        #    action="Закрыть",
        #    action_color=ft.Colors.BLUE,
        #)
        #self.page.snackbar.open = True
        #self.page.update()

        self.page.open(ft.SnackBar(
            content=ft.Text(message, color),
            action="Закрыть",
            action_color=ft.Colors.BLUE,
        ))
        self.page.update()

    # --- Страницы приложения ---

    def home_page(self):
        return ft.View(
            "/",
            [
                ft.AppBar(title=ft.Text("Скачать видео"), bgcolor=ft.Colors.SURFACE),
                ft.Column(
                    [
                        ft.TextField(
                            label="Ссылка на видео",
                            on_change=self.on_url_change,
                            expand=True,
                            autofocus=True,
                        ),
                        ft.ElevatedButton(
                            "Получить форматы",
                            #on_click=lambda e: self.page.run_thread(self.fetch_formats, e),
                            on_click=lambda e: threading.Thread(target=self.fetch_formats, args=[e], daemon=True).start(),
                            #disabled=True,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def formats_page(self):
        controls = [
            ft.AppBar(title=ft.Text("Выберите формат"), bgcolor=ft.Colors.SURFACE),
            ft.Text(f"Ссылка: {self.current_url}", size=14, italic=True),
        ]

        if not self.formats:
            controls.append(ft.Text("Форматы не найдены. Попробуйте другую ссылку.", color=ft.Colors.RED))
            controls.append(
                ft.ElevatedButton(
                    "Назад",
                    on_click=lambda e: self.page.go("/"),
                )
            )
        else:
            list_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=20,
            )

            for fmt in self.formats:
                filesize = f"{fmt['filesize'] / (1024 * 1024):.1f} MB" if fmt['filesize'] else "N/A"
                fps = f"{fmt['fps']} fps" if fmt['fps'] else "N/A"

                list_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{fmt['format_note']} ({fmt['ext']})"),
                        subtitle=ft.Text(f"Размер: {filesize}, FPS: {fps}"),
                        trailing=ft.Text(fmt['format_id'], size=12, color=ft.Colors.GREY_600),
                        on_click=lambda e, fmt=fmt: self.start_download(e, fmt),
                    )
                )

            controls.append(list_view)

        return ft.View(
            "/formats",
            controls,
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def history_page(self):
        controls = [
            ft.AppBar(title=ft.Text("История загрузок"), bgcolor=ft.Colors.SURFACE),
        ]

        if not self.history:
            controls.append(ft.Text("История пуста.", size=16, color=ft.Colors.GREY_500))
        else:
            list_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=20,
            )

            for idx, item in enumerate(reversed(self.history)):  # показываем новые сверху

                card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row([
                            ft.Container(
                                content=ft.Stack(  # Используем Stack для наложения элементов
                                    controls=[
                                        ft.Image(
                                            src=item.get('thumbnail') or 'No_Image_Available.jpeg',
                                            width=100,
                                            height=100,
                                            fit=ft.ImageFit.COVER,
                                        ),
                                        # Добавляем иконку по центру поверх изображения
                                        ft.Container(
                                            content=ft.Icon(
                                                name=ft.Icons.PLAY_CIRCLE_FILL,
                                                color=ft.Colors.WHITE, # Белый цвет иконки для контраста
                                                size=50, # Увеличиваем размер иконки
                                            ),
                                            width=100,
                                            height=100,
                                            alignment=ft.alignment.center, # Выравниваем контейнер (и иконку внутри) по центру Stack
                                            opacity=0.7,
                                        ),
                                    ],
                                ),
                                on_click=lambda e, filevideo=item['filepath']: self.play_video(e, filevideo),
                                ink=True,
                                border_radius=ft.border_radius.all(10)
                            ),
                            ft.Column([
                                ft.Text(item["title"], weight=ft.FontWeight.BOLD),
                                ft.Text(f"Формат: {item['format_id']}", size=12),
                                ft.Text(
                                    f"Файл: {os.path.basename(item['filepath'])}",
                                    size=12,
                                    color=ft.Colors.BLUE_400,
                                    no_wrap=True,
                                    #on_click=lambda e, filevideo=item['filepath']: self.play_video(e, filevideo)
                                ),
                                ft.Text(
                                    f"!Дата: {datetime.fromisoformat(item['timestamp']).strftime('%d.%m.%Y %H:%M')}",
                                    size=10,
                                    color=ft.Colors.GREY_600
                                ),
                            ], expand=True),

                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                tooltip="Удалить запись",
                                on_click=lambda e, i=idx: self.delete_history_item(i),
                            ),
                        ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            #vertical_alignment=ft.CrossAxisAlignment.START,  # Выравниваем по верху
                        )
                    )
                )
                list_view.controls.append(card)


            controls.append(list_view)

        controls.append(
            ft.ElevatedButton(
                "Очистить историю",
                on_click=self.clear_history,
                style=ft.ButtonStyle(color=ft.Colors.RED),
            )
        )

        return ft.View(
            "/history",
            controls,
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def queue_page(self):
        controls = [
            ft.AppBar(title=ft.Text("Очередь загрузок"), bgcolor=ft.Colors.SURFACE),
        ]

        if not self.queue:
            controls.append(ft.Text("Очередь пуста.", size=16, color=ft.Colors.GREY_500))
        else:
            list_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=20,
            )

            for item in self.queue:
                status_color = ft.Colors.GREEN if item["status"] == "completed" else \
                            ft.Colors.RED if "error" in item["status"] else \
                            ft.Colors.RED if "cancelled" in item["status"] else \
                            ft.Colors.ORANGE

                if not item['status'] in ('pending', 'completed'):
                    IconButton = ft.IconButton(
                                icon=ft.Icons.REPLAY,
                                icon_color=ft.Colors.BLUE_400,
                                tooltip="Повторить загрузку",
                                on_click=lambda e, fmt=item: self.retry_download(e, fmt),
                            )
                else:
                    IconButton = ft.Text()
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD_DONE,
                        icon_color=ft.Colors.GREEN,
                        tooltip="Завершено",
                    )

                list_view.controls.append(
                    ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row([
                            ft.Column([
                                ft.Text(os.path.basename(item.get("title", "Неизвестно")), weight=ft.FontWeight.BOLD),
                                ft.Text(f"Формат: {item['format_id']}", size=12),
                                ft.Text(f"Статус: {item['status']}", size=12, color=status_color),
                                ft.Text(
                                    f"Добавлено: {datetime.fromisoformat(item['timestamp']).strftime('%d.%m.%Y %H:%M')}",
                                    size=10,
                                    color=ft.Colors.GREY_600
                                ),
                                item['progress'],
                            ], expand=True),

                            IconButton,
                        ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            #vertical_alignment=ft.CrossAxisAlignment.START,  # Выравниваем по верху
                        )
                    )
                )


                )

            controls.append(list_view)

        controls.append(
            ft.ElevatedButton(
                "Очистить очередь",
                on_click=self.clear_queue,
                style=ft.ButtonStyle(color=ft.Colors.RED),
            )
        )

        return ft.View(
            "/queue",
            controls,
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def settings_page(self):
        path_field = ft.TextField(
            label="Папка для сохранения",
            value=self.settings["download_path"],
            read_only=True,
            expand=True,
        )

        def on_result_pick_dialog(e: ft.FilePickerResultEvent):
            if e.path:
                self.settings["download_path"] = e.path
                path_field.value = self.settings["download_path"]
                self.save_settings()
            else:
                self.show_snackbar("Выбор отменен")

            self.page.update()

        pick_dialog = ft.FilePicker(on_result=on_result_pick_dialog)
        self.page.overlay.append(pick_dialog)

        def open_folder_picker(e):
            #pick_dialog.pick_files(
            #            allow_multiple=True
            #        )
            pick_dialog.get_directory_path(dialog_title="Выберите папку для сохранения", initial_directory=self.settings["download_path"])



        controls = [
            ft.AppBar(title=ft.Text("Настройки"), bgcolor=ft.Colors.SURFACE),
            path_field,
            ft.Row([
                ft.ElevatedButton(
                    "Выбрать папку",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=open_folder_picker,
                ),
                ft.ElevatedButton(
                    "Сбросить",
                    on_click=self.reset_settings,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Text("Версия: 1.0.0", size=12, color=ft.Colors.GREY_600),
        ]

        return ft.View(
            "/settings",
            controls,
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


    def play_video(self, e: ft.ControlEvent, filevideo: str):
        def close(e):
            self.page.close(self.page.dialog)
            self.page.dialog.open = False
            self.page.update()

        if os.path.exists(filevideo):
            video_player = ftv.Video(
                title=os.path.basename(filevideo),
                playlist=ftv.VideoMedia(resource=filevideo),
                autoplay=True,
                expand=True,
            )
        else:
            video_player = ft.Text(f"Файл не обнаружен: {filevideo}")

        self.page.dialog = ft.AlertDialog(
            #title=ft.Text("play_video: "+os.path.basename(filevideo)),
            content=ft.Container(
                content=video_player,
                expand=True,
                alignment=ft.alignment.center,
                width=self.page.width * 0.8,
                height=self.page.height * 0.7,
                #width=400,
                #height=300,
            ),
            #actions=[
            #    ft.ElevatedButton("Close", on_click=close),
            #],
            #modal=True,
        )


        self.page.open(self.page.dialog)
        self.page.dialog.open = True
        self.page.update()
        #video_player.playlist_add(ftv.VideoMedia(filevideo))

    def delete_history_item(self, index: int):
        # Получаем реальный индекс в исходном списке (т.к. показываем reversed)
        real_index = len(self.history) - 1 - index

        def confirm_delete(e):
            self.history.pop(real_index)
            self.save_history()
            self.refresh_history_page()
            #self.page.snackbar = ft.SnackBar(
            #    content=ft.Text("Запись удалена из истории."),
            #    duration=2000,
            #)
            self.show_snackbar("Запись удалена из истории.")
            #self.page.snackbar.open = True
            #self.page.update()

        def cancel_delete(e):
            self.page.close(self.page.dialog)
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Удалить запись?"),
            content=ft.Text("Вы уверены, что хотите удалить эту запись из истории?"),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_delete),
                ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            modal=True,
        )
        self.page.open(self.page.dialog)
        self.page.dialog.open = True
        self.page.update()

    # --- Обработчики событий ---

    def on_url_change(self, e):
        self.current_url = e.control.value.strip()
        
        # Находим представление с маршрутом "/" (главная страница)
        #print(dir(e))
        #e.control.disabled = not self.current_url

        for view in self.page.views:
            if view.route == "/":
                # Получаем кнопку по позиции в иерархии
                # controls[1] — это Column, controls[1] внутри неё — вторая кнопка
                button = view.controls[1].controls[1]
                if isinstance(button, ft.ElevatedButton):
                    button.disabled = not self.current_url
                break
        
        self.page.update()


    def fetch_formats(self, e):
        if not self.current_url:
            self.show_snackbar("Введите ссылку!")
            return
        e.control.content = ft.ProgressRing(width=20, height=20, stroke_width=2, disabled=True)
        #e.control.disabled=True
        self.page.update()

        self.formats = self.get_formats(self.current_url)
        
        #e.control.disabled=False
        e.control.content = None
        self.page.update()

        if self.formats:
            self.page.go("/formats")
        else:
            self.page.go("/formats")
            self.show_snackbar("Не удалось получить форматы. Проверьте ссылку.")

    def retry_download(self, e: ft.ControlEvent, fmt: dict):
        #self.page.run_thread(self.download_video, fmt['url'], fmt)
        threading.Thread(target=self.download_video, args=(fmt['url'], fmt), daemon=True).start()

    def start_download(self, e: ft.ControlEvent, fmt: dict):
        # Добавляем в очередь
        self.add_to_queue(self.current_url, fmt)
        # Переходим на страницу очереди
        self.page.go("/queue")
        # Запускаем скачивание в отдельном потоке, чтобы не блокировать UI
        #self.page.run_thread(self.download_video, self.current_url, fmt)
        threading.Thread(target=self.download_video, args=(self.current_url, fmt), daemon=True).start()

    def clear_history(self, e):
        self.history.clear()
        self.save_history()
        self.refresh_history_page()

    def clear_queue(self, e):
        self.queue.clear()
        self.save_queue()
        self.refresh_queue_page()

    def reset_settings(self, e):
        self.settings["download_path"] = ""
        self.save_settings()
        # Ищем TextField в текущем представлении /settings
        for view in self.page.views:
            if view.route == "/settings":
                for control in view.controls:
                    if isinstance(control, ft.TextField):
                        control.value = ""
                        break
        self.page.update()


    # --- Методы обновления страниц ---

    def refresh_history_page(self):
        self.page.views.clear()
        self.page.views.append(self.formats_page())
        self.page.views.append(self.history_page())
        self.page.views.append(self.queue_page())
        self.page.views.append(self.settings_page())
        self.page.views.append(self.home_page())
        self.page.update()

    def refresh_queue_page(self):
        self.page.views.clear()
        self.page.views.append(self.formats_page())
        self.page.views.append(self.history_page())
        self.page.views.append(self.queue_page())
        self.page.views.append(self.settings_page())
        self.page.views.append(self.home_page())
        self.page.update()


    # --- Основной метод запуска ---

    def run(self, page: ft.Page):
        self.page = page
        self.page.title = APP_NAME
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Настройка навигации
        def route_change(route):
            self.page.views.clear()

            if page.route == "/formats":
                self.page.views.append(self.formats_page())
            elif page.route == "/history":
                self.page.views.append(self.history_page())
            elif page.route == "/queue":
                self.page.views.append(self.queue_page())
            elif page.route == "/settings":
                self.page.views.append(self.settings_page())
            else:
                self.page.views.append(self.home_page())

            self.page.update()

        def view_pop(view):
            top_view = self.page.views.pop()
            if len(self.page.views) > 0:
                top_view = self.page.views[-1]
            self.page.go(top_view.route)

            #self.page.views.pop()
            #top_view = self.page.views[-1]
            #self.page.go(top_view.route)

        self.page.on_route_change = route_change
        self.page.on_view_pop = view_pop
        self.page.go(self.page.route)

        self.page.update()



# Точка входа
def main(page: ft.Page):
    app = VideoDownloader()
    app.run(page)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", view=ft.AppView.WEB_BROWSER)  # Для веб-версии
    # ft.app(target=main)  # Для десктопной версии



#напиши полноценное приложение для скачивания видео по ссылке используя flet.View и yt-dlp. В нем нолжно быть несколько страниц: Страница ввода ссылки, после ввода получаем список доступных форматов для выбора из возможных; страница истории; страница очереди; страница настроек. В настройках выбор папки для сохранения flet.FilePicker и если директория не указана, просить указать. Добавь меню BottomAppBar для выбора каждого пункта.  Синтаксис для версии flet 0.28.3
