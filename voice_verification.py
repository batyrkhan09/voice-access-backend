import os
import torch
from pydub import AudioSegment
from speechbrain.pretrained import SpeakerRecognition

from speechbrain.dataio.dataio import read_audio
import subprocess

# 🔧 Отключаем предупреждение про симлинки (опционально)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Указываем путь к ffmpeg (для pydub)
AudioSegment.converter = r"C:\\Users\\tokta\\Desktop\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"

# ✅ Загрузка локальной модели speaker verification
verifier = SpeakerRecognition.from_hparams(
    source="pretrained_models/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec-ecapa-voxceleb",
    run_opts={"use_symlinks": False}
)

# 📁 Папка для хранения эмбеддингов
EMBEDDING_DIR = "voice_embeddings"
os.makedirs(EMBEDDING_DIR, exist_ok=True)

# === 📥 При регистрации: сохраняем отпечаток голоса ===
def save_user_voice_embedding(audio_path, username):
    wav_path = convert_to_wav(audio_path)
    signal = read_audio(wav_path)
    embedding = verifier.encode_batch(signal.unsqueeze(0))  # Добавляем измерение батча
    torch.save(embedding, os.path.join(EMBEDDING_DIR, f"{username}.pt"))
    os.remove(wav_path)

# === 🔐 При входе: сравниваем голос с эталоном ===
def verify_user_voice(audio_path, username):
    embedding_path = os.path.join(EMBEDDING_DIR, f"{username}.pt")
    if not os.path.exists(embedding_path):
        return False, "Нет голосового отпечатка для этого пользователя"

    wav_path = convert_to_wav(audio_path)
    signal = read_audio(wav_path)
    test_embedding = verifier.encode_batch(signal.unsqueeze(0))
    ref_embedding = torch.load(embedding_path)

    similarity = torch.nn.functional.cosine_similarity(
    test_embedding.squeeze(1), ref_embedding.squeeze(1)
    )[0].item()

    os.remove(wav_path)

    print(f"[DEBUG] Similarity: {similarity:.4f}")
    return similarity > 0.5, f"Similarity: {similarity:.4f}"


# === 🎧 Конвертация webm → wav 16kHz mono ===
def convert_to_wav(webm_path):
    wav_path = webm_path.replace(".webm", ".wav")
    try:
        print(f"[DEBUG] Начинаем конвертацию: {webm_path}")
        result = subprocess.run(
            [
                r"C:\Users\tokta\Desktop\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe",
                "-y",                     # overwrite output
                "-i", webm_path,
                "-ar", "16000",           # sample rate
                "-ac", "1",               # mono
                wav_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            print(f"[ERROR] ffmpeg stderr:\n{result.stderr.decode()}")
            raise Exception("FFmpeg конвертация не удалась")

        print(f"[DEBUG] Успешно сконвертировано: {wav_path}")
        return wav_path

    except Exception as e:
        print(f"[ERROR] Конвертация не удалась: {e}")
        raise

