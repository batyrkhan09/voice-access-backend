import speech_recognition as sr
import tempfile
import os
import sqlite3
from pydub import AudioSegment

# Указываем путь к ffmpeg (можно просто "ffmpeg" на сервере)
AudioSegment.converter = "ffmpeg"

def verify_user(audio_file, username):
    recognizer = sr.Recognizer()

    # Сохраняем временно .webm файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        webm_path = temp_audio.name
        temp_audio.write(audio_file.read())

    # Проверка размера файла (не больше 5МБ)
    if os.path.getsize(webm_path) > 5 * 1024 * 1024:
        try:
            os.remove(webm_path)
        except:
            pass
        return {"success": False, "message": "Аудиофайл слишком большой"}

    # Конвертация в .wav
    wav_path = webm_path.replace(".webm", ".wav")
    try:
        audio = AudioSegment.from_file(webm_path, format="webm")
        audio.export(wav_path, format="wav")
    except Exception as e:
        print(f"[ERROR] Конвертация не удалась: {e}")
        try: os.remove(webm_path)
        except: pass
        return {"success": False, "message": "Ошибка при конвертации аудио"}

    # Распознавание речи
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU").lower()
            print(f"[INFO] Распознанный текст: {text}")
    except Exception as e:
        print(f"[ERROR] Ошибка распознавания: {e}")
        try:
            os.remove(webm_path)
            os.remove(wav_path)
        except:
            pass
        return {"success": False, "message": "Ошибка при распознавании речи"}

    # Поиск фразы в базе
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT passphrase FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        return {"success": False, "message": "Ошибка базы данных"}

    try:
        os.remove(webm_path)
        os.remove(wav_path)
    except:
        pass

    if row and row[0] in text:
        return {"success": True, "message": "Доступ разрешён ✅"}
    else:
        return {"success": False, "message": "Фраза не распознана ❌"}
