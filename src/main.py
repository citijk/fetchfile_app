import flet as ft
import yt_dlp
import os
import json
from datetime import datetime
from typing import List, Dict, Optional


# Константы
APP_NAME = "Video Downloader"
SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"
QUEUE_FILE = "queue.json"


class VideoDownloader:
    def __init__(self):
        self.page: ft.Page = None
        self.settings = self.load_settings()
        self.history = self.load_history()
        self.queue = self.load_queue()
        self.formats = []
        self.current_url = ""

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
        return {"download_path": "/Users/z/Downloads"}

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
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_queue(self):
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.queue, f, indent=2)

    def add_to_history(self, url: str, title: str, format_id: str, filepath: str):
        self.history.append({
            "url": url,
            "title": title,
            "format_id": format_id,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history()

    def add_to_queue(self, url: str, format_id: str):
        self.queue.append({
            "url": url,
            "format_id": format_id,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        })
        self.save_queue()

    def get_formats(self, url: str) -> List[Dict]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        try:
            print(url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = []
                for f in info['formats']:
                    if (f.get('format_note') or f.get('format')) and f.get('ext'):
                        formats.append({
                            'format_id': f['format_id'],
                            'ext': f['ext'],
                            'format_note': (f.get('format_note') or f.get('format')),
                            'filesize': f.get('filesize'),
                            'fps': f.get('fps'),
                        })
                return sorted(formats, key=lambda x: (x['filesize'] or 0), reverse=True)
        except Exception as e:
            print(f"!Error fetching formats: {e}")
            return []

    def download_video(self, url: str, format_id: str) -> bool:
        if not self.settings["download_path"]:
            self.show_snackbar("Укажите папку для сохранения в настройках!")
            return False

        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(self.settings["download_path"], '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown Title')
                filepath = ydl.prepare_filename(info)
                self.add_to_history(url, title, format_id, filepath)
                self.update_queue_status(url, format_id, "completed")
                self.show_snackbar(f"Скачать успешно: {title}")
                return True
        except Exception as e:
            self.update_queue_status(url, format_id, f"!error: {str(e)}")
            self.show_snackbar(f"Ошибка скачивания: {e}")
            return False

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            self.page.session.set("download_progress", percent)
            self.page.update()

    def update_queue_status(self, url: str, format_id: str, status: str):
        for item in self.queue:
            if item["url"] == url and item["format_id"] == format_id:
                item["status"] = status
                item["updated"] = datetime.now().isoformat()
        self.save_queue()
        self.refresh_queue_page()

    def show_snackbar(self, message: str):
        self.page.snackbar = ft.SnackBar(
            content=ft.Text(message),
            action="Закрыть",
            action_color=ft.Colors.BLUE,
        )
        self.page.snackbar.open = True
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
                        ),
                        ft.ElevatedButton(
                            "Получить форматы",
                            on_click=self.fetch_formats,
                            disabled=True,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            self.bottom_nav(),
            vertical_alignment=ft.MainAxisAlignment.CENTER,
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
                        on_click=lambda e, fmt_id=fmt['format_id']: self.start_download(fmt_id),
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

            for item in reversed(self.history):  # показываем новые сверху
                list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(item["title"], weight=ft.FontWeight.BOLD),
                                ft.Text(f"Формат: {item['format_id']}", size=12),
                                ft.Text(f"Файл: {os.path.basename(item['filepath'])}", size=12, color=ft.Colors.BLUE_400),
                                ft.Text(
                                    f"Дата: {datetime.fromisoformat(item['timestamp']).strftime('%d.%m.%Y %H:%M')}",
                                    size=10,
                                    color=ft.Colors.GREY_600
                                ),
                            ])
                        )
                    )
                )

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
                            ft.Colors.RED if "error" in item["status"] else ft.Colors.ORANGE

                list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(os.path.basename(item.get("title", "Неизвестно")), weight=ft.FontWeight.BOLD),
                                ft.Text(f"Формат: {item['format_id']}", size=12),
                                ft.Text(f"Статус: {item['status']}", size=12, color=status_color),
                                ft.Text(
                                    f"Добавлено: {datetime.fromisoformat(item['timestamp']).strftime('%d.%m.%Y %H:%M')}",
                                    size=10,
                                    color=ft.Colors.GREY_600
                                ),
                            ])
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
        def on_pick_result(e: ft.FilePickerResultEvent):
            if e.files and e.files[0].path:
                self.settings["download_path"] = e.files[0].path
                self.save_settings()
                # Обновляем значение в текстовом поле
                path_field.value = self.settings["download_path"]
                self.page.update()

        pick_dialog = ft.FilePicker(on_result=on_pick_result)
        self.page.overlay.append(pick_dialog)

        def open_folder_picker(e):
            #pick_dialog.pick_files(
            #            allow_multiple=True
            #        )
            pick_dialog.get_directory_path(dialog_title="Выберите папку для сохранения", initial_directory=self.settings["download_path"])

        path_field = ft.TextField(
            label="Папка для сохранения",
            value=self.settings["download_path"],
            read_only=True,
            expand=True,
        )

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


    # --- Обработчики событий ---

    def on_url_change(self, e):
        self.current_url = e.control.value.strip()
        
        # Находим представление с маршрутом "/" (главная страница)
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

        self.formats = self.get_formats(self.current_url)
        if self.formats:
            self.page.go("/formats")
        else:
            self.show_snackbar("Не удалось получить форматы. Проверьте ссылку.")

    def start_download(self, format_id: str):
        # Добавляем в очередь
        self.add_to_queue(self.current_url, format_id)
        
        # Переходим на страницу очереди
        self.page.go("/queue")
        
        # Запускаем скачивание в отдельном потоке, чтобы не блокировать UI
        def download_task():
            self.download_video(self.current_url, format_id)
        
        import threading
        thread = threading.Thread(target=download_task)
        thread.start()

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



#напиши полноценное приложение для скачивания видео по ссылке используя flet.View и yt-dlp. В нем нолжно быть несколько страниц: Страница ввода ссылки, после ввода получаем список доступных форматов для выбора из возможных; страница истории; страница очереди; страница настроек. В настройках выбор папки для сохранения flet.FilePicker и если директория не указана, просить указать. Синтаксис для версии flet 0.28.3
