import flet as ft
from yt_dlp import YoutubeDL
import threading
import os

def main(page: ft.Page):
    page.title = "Видео загрузчик FetchFile"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    url_field = ft.TextField(label="Введите URL видео", width=(page.width-200), value="https://rutube.ru/video/11609795aeabe7398b154f0fdf0fadd3/")
    progress_bar = ft.ProgressBar(width=(page.width-200), visible=False)
    status = ft.Text("")
    download_button = ft.ElevatedButton("Скачать", disabled=False)

    # Переменная для хранения выбранного пути
    FLET_APP_STORAGE_DATA = os.getenv("FLET_APP_STORAGE_DATA")

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
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded_bytes = d.get('downloaded_bytes', 0)
                progress = downloaded_bytes / total_bytes if total_bytes else 0
                progress_bar.value = progress
                status.value = f"Скачано: {downloaded_bytes / 1024:.2f} KB / {total_bytes / 1024:.2f} KB"
                page.update()
            elif d['status'] == 'finished':
                progress_bar.value = 1.0
                status.value = "Скачивание завершено!"
                download_button.disabled = False
                page.update()

        def run_download():
            ydl_opts = {
                'outtmpl': os.path.join(FLET_APP_STORAGE_DATA, '%(title)s.%(ext)s'),
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

    async def open_folder_picker():
        nonlocal FLET_APP_STORAGE_DATA
        folder = await page.pick_directory()
        if folder:
            FLET_APP_STORAGE_DATA = folder
            status.value = f"Выбрана папка: {FLET_APP_STORAGE_DATA}"
        else:
            status.value = "Выбор папки отменён"
        page.update()

    page.on_ready = lambda e: open_folder_picker()

    form_row = ft.Column(
        [
            ft.Row(
                [
                    url_field,
                    download_button
                ],
                alignment=ft.MainAxisAlignment.CENTER,  # По горизонтали по центру
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    progress_bar,
                    status,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,      # Центрирование колонки по вертикали на странице
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # Центрирование по горизонтали
        expand=True  # Занять весь доступный экран для центрирования
    )

    page.add(form_row)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", upload_dir=os.getenv("FLET_APP_STORAGE_DATA"))
