import os
import yt_dlp
import time
from flask import Flask, render_template, request, send_file, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Настройки
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Максимальное время хранения файлов в секундах (здесь — 1 час)
MAX_AGE = 60 * 60  # 3600 секунд = 1 час
MAX_SIZE_MB = 500  # Максимальный размер хранилища (в МБ)

# Удалить старые файлы
def cleanup_downloads():
    now = time.time()
    deleted_count = 0
    total_size_freed = 0

    try:
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getctime(filepath)
                if file_age > MAX_AGE:
                    file_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    total_size_freed += file_size
    except Exception as e:
        print(f"Ошибка при очистке: {e}")

    if deleted_count > 0:
        print(f"Очистка: удалено {deleted_count} файлов, освобождено {total_size_freed >> 20} МБ")

# Опционально: ограничение по общему размеру (если место заканчивается)
def limit_storage():
    total_size = sum(
        os.path.getsize(os.path.join(DOWNLOAD_FOLDER, f))
        for f in os.listdir(DOWNLOAD_FOLDER)
        if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))
    )
    if total_size > MAX_SIZE_MB * 1024 * 1024:
        # Сортируем по времени создания (старые — первыми)
        files = [
            (f, os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f)))
            for f in os.listdir(DOWNLOAD_FOLDER)
            if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))
        ]
        files.sort(key=lambda x: x[1])  # По возрасту

        while total_size > MAX_SIZE_MB * 0.9 * 1024 * 1024:  # до 90% лимита
            if not files:
                break
            oldest_file = files.pop(0)
            filepath = os.path.join(DOWNLOAD_FOLDER, oldest_file[0])
            if os.path.exists(filepath):
                total_size -= os.path.getsize(filepath)
                os.remove(filepath)
                print(f"Удалён для экономии места: {oldest_file[0]}")

# Функция скачивания
def download_video(url):
    cleanup_downloads()      # Чистим перед скачиванием
    limit_storage()          # Проверяем общий объём

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).50s-%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'retries': 5,
        'fragment_retries': 5,
        'socket_timeout': 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info.get('title', 'Без названия')
    except Exception as e:
        return None, str(e)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url.startswith(('http://', 'https://')):
            flash("Пожалуйста, введите корректную ссылку.")
            return redirect(url_for('index'))

        filepath, title = download_video(url)
        if filepath and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            flash(f"Не удалось скачать видео: {title}")
            return redirect(url_for('index'))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
