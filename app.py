from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import verify_user
from models import init_db
from voice_verification import save_user_voice_embedding, verify_user_voice
import sqlite3
import tempfile
import os
from time import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
init_db()

# === 🔐 Ограничение попыток входа ===
login_attempts = {}  # {username: [кол-во_попыток, время_последней_неудачи]}
MAX_ATTEMPTS = 5
BLOCK_TIME = 30  # сек

@app.route("/api/can-record", methods=["POST"])
def can_record():
    data = request.get_json()
    username = data.get("username")
    now = time()

    attempts, last_time = login_attempts.get(username, [0, 0])
    if attempts >= MAX_ATTEMPTS and (now - last_time) < BLOCK_TIME:
        remaining = int(BLOCK_TIME - (now - last_time))
        return jsonify({"canRecord": False, "remaining": remaining})

    return jsonify({"canRecord": True})


@app.route("/api/verify", methods=["POST"])
def verify():
    audio = request.files.get("audio")
    username = request.form.get("username")

    if not audio or not username:
        return jsonify({"success": False, "message": "Отсутствует имя или аудио"}), 400

    now = time()
    attempts, last_time = login_attempts.get(username, [0, 0])
    if attempts >= MAX_ATTEMPTS and (now - last_time) < BLOCK_TIME:
        remaining = int(BLOCK_TIME - (now - last_time))
        return jsonify({
            "success": False,
            "blocked": True,
            "retry_after": remaining,
            "message": f"🔒 Превышено количество попыток. Подождите {remaining} сек."
        }), 403

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
        audio_path = temp.name
        audio.save(audio_path)

    match, score_text = verify_user_voice(audio_path, username)
    if not match:
        os.remove(audio_path)
        if attempts + 1 >= MAX_ATTEMPTS:
            login_attempts[username] = [MAX_ATTEMPTS, now]
        else:
            login_attempts[username] = [attempts + 1, last_time]
        return jsonify({"success": False, "message": "Голос не совпадает ❌\n" + score_text})

    result = verify_user(open(audio_path, "rb"), username)
    os.remove(audio_path)

    if result["success"]:
        login_attempts[username] = [0, 0]  # сброс попыток

    return jsonify(result)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.form
    username = data.get("username")
    phrase = data.get("phrase")
    audio_file = request.files.get("audio")

    if not username or not phrase or not audio_file:
        return jsonify({"success": False, "message": "Имя, фраза и аудио обязательны"}), 400

    try:
        with sqlite3.connect('database.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, passphrase) VALUES (?, ?)', (username, phrase))
            conn.commit()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
            audio_path = temp.name
            audio_file.save(audio_path)

        save_user_voice_embedding(audio_path, username)
        os.remove(audio_path)

        return jsonify({"success": True, "message": "Пользователь зарегистрирован!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Такой пользователь уже существует"}), 409
    except sqlite3.OperationalError as e:
        return jsonify({"success": False, "message": f"Ошибка базы данных: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
