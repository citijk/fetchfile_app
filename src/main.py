import flet as ft
from yt_dlp import YoutubeDL
import threading
import os
import json
from uuid import getnode as get_mac




def main(page: ft.Page):


    page.title = "Видео загрузчик FetchFile"
    page.padding = 20
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[
            ft.Locale("de", "DE"),
            ft.Locale("es", "VE"),
            ft.Locale("en", "US"),
            ft.Locale("ru", "RU"),
        ],
        #current_locale=ft.Locale("es", "VE")
    )

    #page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    #page.vertical_alignment = ft.MainAxisAlignment.CENTER
    #page.vertical_alignment = ft.MainAxisAlignment.START

    #page.floating_action_button = ft.FloatingActionButton(
    #    icon=ft.Icons.ADD, shape=ft.CircleBorder()
    #)
    #page.floating_action_button_location = ft.FloatingActionButtonLocation.CENTER_DOCKED


    def handle_locale_change(e):
        index = int(e.data)
        if index == 0:
            page.locale_configuration.current_locale = ft.Locale("de", "DE")
        elif index == 1:
            page.locale_configuration.current_locale = ft.Locale("es", "VE")
        elif index == 2:
            page.locale_configuration.current_locale = ft.Locale("en", "US")
        elif index == 3:
            page.locale_configuration.current_locale = ft.Locale("ru", "RU")
        page.update()

    def bs_dismissed(e):
        page.add(ft.Text("Bottom sheet dismissed"))

    bs = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Text("Select lang"),
                    ft.CupertinoSlidingSegmentedButton(
                            selected_index=0,
                            thumb_color=ft.Colors.BLUE_400,
                            on_change=handle_locale_change,
                            controls=[ft.Text("German"), ft.Text("Spanish"), ft.Text("English"), ft.Text("Russian")],
                    ),
                    ft.ElevatedButton("Dismiss", on_click=lambda _: page.close(bs)),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=50,
        ),
        open=False,
        on_dismiss=bs_dismissed,
    )
    page.overlay.append(bs)


    def check_item_clicked(e):
        e.control.checked = not e.control.checked
        page.update()


    appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.DOWNLOAD),
        leading_width=40,
        title=ft.Text("FetchFile"),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED),
            ft.IconButton(ft.Icons.FILTER_3),
            ft.ElevatedButton("en", on_click=lambda e: page.open(bs)),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text="Item 1"),
                    ft.PopupMenuItem(),  # divider
                    ft.PopupMenuItem(
                        text="Checked item", checked=False, on_click=check_item_clicked
                    ),
                ]
            ),
        ],
    )


    bottom_appbar = ft.BottomAppBar(
        content=ft.Row(
            [
                #ft.IconButton(ft.Icons.MENU),
                ft.Text("fetchfile.me (c)"),
                #ft.IconButton(ft.Icons.SEARCH),
            ],
            #alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.BLUE_GREY_900,
    )


    class BaseView(ft.View):
        def __init__(self, *a, **kw):
            super().__init__(*a,
                appbar = appbar,
                bottom_appbar = bottom_appbar,
                fullscreen_dialog = True,
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment = ft.CrossAxisAlignment.CENTER,
                **kw,)


    url_field = ft.TextField(label="Введите URL видео", width=(page.width-120), value="https://rutube.ru/video/c5f09f19624cf5c0fca126ca7e635a69/")
    info_text = ft.Text("", width=(page.width-120))

    image = ft.Image(
                src=False,
                width=200,  # Set desired width
                fit=ft.ImageFit.COVER # Adjust how the image fits within the specified size
            )

    progress_bar = ft.ProgressBar(width=(page.width-120), visible=False)
    status = ft.Text(get_mac())
    download_button = ft.ElevatedButton("Скачать", disabled=True)
    fetch_info_button = ft.ElevatedButton("Показать информацию")
    select_folder_button = ft.ElevatedButton("Выбрать папку для сохранения")

    file_picker = ft.FilePicker(on_result=None)

    CONFIG_PATH = "config.json"
    def load_config():
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        return {}
    def save_config(config):
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)
    config = load_config()
    save_folder = config.get("save_folder", os.path.expanduser("~"))

    status.value = f"будет сохраненно в: {save_folder}"

    def on_result(e: ft.FilePickerResultEvent):
        nonlocal save_folder
        if e.path:
            save_folder = e.path
            config["save_folder"] = save_folder
            save_config(config)
            status.value = f"Выбрана папка: {save_folder}"
        else:
            status.value = "Выбор папки отменён"
        page.update()

    file_picker.on_result = on_result
    page.overlay.append(file_picker)

    def open_folder_picker(e):
        file_picker.get_directory_path(dialog_title="Выберите папку для сохранения", initial_directory=save_folder)

    #select_folder_button.on_click = open_folder_picker

    def fetch_info(e):
        url = url_field.value.strip()
        if not url:
            info_text.value = "Введите URL для получения информации"
            download_button.disabled = True
            page.update()
            return

        info_text.value = "Получение информации..."
        download_button.disabled = True
        progress_bar.visible = False
        #status.value = ""
        page.update()

        def run_info():
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'N/A')
                    duration = info.get('duration', 0)
                    duration_min = duration // 60
                    duration_sec = duration % 60
                    uploader = info.get('uploader', 'N/A')
                    filesize = info.get('filesize_approx') or info.get('filesize') or 0
                    filesize_mb = filesize / (1024 * 1024) if filesize else 'N/A'
                    ext = info.get('ext', 'N/A')
                    thumbnail = info.get('thumbnail', '')


                    if thumbnail:
                        image.src = thumbnail
                        image.update()

                    info_text.value = (
                        f"Название: {title}\n"
                        f"Длительность: {duration_min}м {duration_sec}с\n"
                        f"Загрузчик: {uploader}\n"
                        f"Размер файла: {filesize_mb if isinstance(filesize_mb, str) else f'{filesize_mb:.2f} MB'}\n"
                        f"Формат: {ext}"
                    )
                    download_button.disabled = False
            except Exception as ex:
                info_text.value = f"Ошибка получения информации: {ex}"
                download_button.disabled = True
            page.update()

        threading.Thread(target=run_info, daemon=True).start()

    def download_video(e):
        url = url_field.value.strip()
        if not url:
            status.value = "Введите URL для загрузки"
            page.update()
            return

        download_button.disabled = True
        progress_bar.value = 0
        progress_bar.visible = True
        status.value = "Начинается скачивание..."
        page.update()

        def on_progress(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded = d.get('downloaded_bytes', 0)
                progress = downloaded / total if total else 0
                progress_bar.value = progress
                status.value = f"Скачано: {downloaded / 1024:.2f} KB / {total / 1024:.2f} KB"
                page.update()
            elif d['status'] == 'finished':
                progress_bar.value = 1.0
                status.value = "Скачивание завершено!"
                download_button.disabled = False
                page.update()

        def run_download():
            ydl_opts = {
                'outtmpl': os.path.join(save_folder, '%(title)s.%(ext)s'),
                'progress_hooks': [on_progress],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as ex:
                status.value = f"Ошибка: {ex}"
                progress_bar.visible = False
                download_button.disabled = False
                page.update()

        threading.Thread(target=run_download, daemon=True).start()

    fetch_info_button.on_click = fetch_info
    #download_button.on_click = download_video








    def route_change(route: ft.RouteChangeEvent):
        page.views.clear()
        def next_prev(e):
            fetch_info(e)
            page.go("/preview")

        page.views.append(
            BaseView(
                "/",
                [
                    ft.Row([
                        url_field,
                        ft.ElevatedButton("Next", on_click=next_prev)
                    ]),
                ],
            )
        )
        if page.route == "/preview":
            def next_prev(e):
                download_video(e)
                page.go("/download")
            download_button.on_click=next_prev
            page.views.append(
                BaseView(
                    "/preview",
                    [
                        image,
                        info_text,
                        #ft.AppBar(title=ft.Text("About")),
                        #ft.Text("This is the About Page!"),
                        download_button,
                        status,
                        ft.ElevatedButton("Выбрать папку для сохранения", on_click = open_folder_picker),
                    ],
                )
            )
        elif page.route == "/download":
            def cancel(e):
                page.go("/preview")

            page.views.append(
                BaseView(
                    "/download",
                    [
                        progress_bar,
                        ft.ElevatedButton("cancel", on_click=cancel),
                    ],
                )
            )
        page.update()


    def view_pop(e):
        top_view = page.views.pop()
        if len(page.views) > 0:
            top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    page.go(page.route)

#    form_row = ft.Column(
#        [
#            ft.Row(
#                [
#                    url_field,
#                    download_button
#                ],
#                alignment=ft.MainAxisAlignment.CENTER,  # По горизонтали по центру
#                vertical_alignment=ft.CrossAxisAlignment.CENTER,
#            ),
#            ft.Row(
#                [
#                    progress_bar,
#                ],
#                alignment=ft.MainAxisAlignment.CENTER,
#                vertical_alignment=ft.CrossAxisAlignment.CENTER,
#            ),
#            ft.Row(
#                [
#                    image,
#                    info_text,
#                ],
#                alignment=ft.MainAxisAlignment.CENTER,
#                vertical_alignment=ft.CrossAxisAlignment.CENTER,
#            ),
#            fetch_info_button,
#            status,
#            select_folder_button,
#        ],
#        alignment=ft.MainAxisAlignment.CENTER,      # Центрирование колонки по вертикали на странице
#        horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # Центрирование по горизонтали
#        expand=True  # Занять весь доступный экран для центрирования
#    )
#
#    page.add(
#        form_row
#    )

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", view=ft.AppView.WEB_BROWSER)
