import flet as ft
from yt_dlp import YoutubeDL
import threading
import os

def main(page: ft.Page):
    page.title = "Видео загрузчик FetchFile"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    url_field = ft.TextField(label="Введите URL видео", width=(page.width-120), value="https://rutube.ru/video/11609795aeabe7398b154f0fdf0fadd3/")
    progress_bar = ft.ProgressBar(width=(page.width-120), visible=False)
    status = ft.Text("")
    download_button = ft.ElevatedButton("Скачать", disabled=False)
    select_folder_button = ft.ElevatedButton("Выбрать папку для сохранения")

    # Переменная для выбранной папки (по умолчанию домашняя директория)
    save_folder = os.path.expanduser("~")

    # Создаём FilePicker для выбора папки
    file_picker = ft.FilePicker(on_result=None)

    # Устанавливаем обработчик события выбора папки через метод get_directory_path
    def on_result(e: ft.FilePickerResultEvent):
        nonlocal save_folder
        if e.path:
            save_folder = e.path
            status.value = f"Выбрана папка: {save_folder}"
        else:
            status.value = "Выбор папки отменён"
        page.update()

    file_picker.on_result = on_result
    page.overlay.append(file_picker)

    def open_folder_picker(e):
        # Используем метод get_directory_path для вызова диалога выбора папки
        file_picker.get_directory_path(dialog_title="Выберите папку для сохранения", initial_directory=save_folder)

    select_folder_button.on_click = open_folder_picker

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

    download_button.on_click = download_video

    page.add(
        ft.Column(
            [
                ft.Row([url_field, download_button], alignment=ft.MainAxisAlignment.CENTER),
                 ft.Row([select_folder_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([progress_bar], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([status], alignment=ft.MainAxisAlignment.CENTER),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
