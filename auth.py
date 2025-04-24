import speech_recognition as sr
import tempfile
import os
import sqlite3
from pydub import AudioSegment

# Указываем путь к ffmpeg вручную (важно!)
AudioSegment.converter = r"C:\\Users\\tokta\\Desktop\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"

def verify_user(audio_file, username):
    recognizer = sr.Recognizer()

    # Сохраняем загруженный webm-файл вручную через .read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        webm_path = temp_audio.name
        temp_audio.write(audio_file.read())

    # Конвертация webm → wav
    wav_path = webm_path.replace(".webm", ".wav")
    try:
        print(f"[DEBUG] Конвертация: {webm_path} → {wav_path}")
        audio = AudioSegment.from_file(webm_path, format="webm")
        audio.export(wav_path, format="wav")
    except Exception as e:
        print(f"[ERROR] Конвертация не удалась: {e}")
        return {"success": False, "message": "Ошибка при конвертации webm → wav"}

    # Распознавание речи
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU").lower()
            print(f"[INFO] Распознанный текст: {text}")
    except Exception as e:
        print(f"[ERROR] Ошибка распознавания: {e}")
        return {"success": False, "message": "Ошибка при распознавании голоса"}

    # Проверка в базе данных
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT passphrase FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Ошибка базы данных: {e}")
        return {"success": False, "message": "Ошибка базы данных"}

    # Удаление временных файлов
    os.remove(webm_path)
    os.remove(wav_path)

    # Сравнение фразы
    if row and row[0] in text:
        return {"success": True, "message": "Доступ разрешён ✅"}
    else:
        return {"success": False, "message": "Доступ запрещён ❌"}
