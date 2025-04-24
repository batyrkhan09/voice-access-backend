import os
import torch
from pydub import AudioSegment
from speechbrain.pretrained import SpeakerRecognition
from speechbrain.dataio.dataio import read_audio
import subprocess

# 🔧 Убираем предупреждение
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# ✅ Установка ffmpeg
ffmpeg_path = r"C:\\Users\\tokta\\Desktop\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"
AudioSegment.converter = ffmpeg_path if os.path.exists(ffmpeg_path) else "ffmpeg"

# 📁 Папка для эмбеддингов
EMBEDDING_DIR = "voice_embeddings"
os.makedirs(EMBEDDING_DIR, exist_ok=True)

# === ✅ Ленивая загрузка модели один раз ===
_verifier = None

def get_verifier():
    global _verifier
    if _verifier is None:
        print("[INFO] Загружаем модель speaker verification...")
        _verifier = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
            run_opts={"use_symlinks": False}
        )
    return _verifier

# === 📥 Регистрация ===
def save_user_voice_embedding(audio_path, username):
    wav_path = convert_to_wav(audio_path)
    signal = read_audio(wav_path)
    verifier = get_verifier()
    embedding = verifier.encode_batch(signal.unsqueeze(0))
    torch.save(embedding, os.path.join(EMBEDDING_DIR, f"{username}.pt"))
    os.remove(wav_path)

# === 🔐 Проверка ===
def verify_user_voice(audio_path, username):
    embedding_path = os.path.join(EMBEDDING_DIR, f"{username}.pt")
    if not os.path.exists(embedding_path):
        return False, "Нет голосового отпечатка для этого пользователя"

    wav_path = convert_to_wav(audio_path)
    signal = read_audio(wav_path)
    verifier = get_verifier()
    test_embedding = verifier.encode_batch(signal.unsqueeze(0))
    ref_embedding = torch.load(embedding_path)

    similarity = torch.nn.functional.cosine_similarity(
        test_embedding.squeeze(1), ref_embedding.squeeze(1)
    )[0].item()

    os.remove(wav_path)

    print(f"[DEBUG] Similarity: {similarity:.4f}")
    return similarity > 0.5, f"Similarity: {similarity:.4f}"

# === 🎧 Конвертация webm → wav ===
def convert_to_wav(webm_path):
    wav_path = webm_path.replace(".webm", ".wav")
    ffmpeg = AudioSegment.converter

    try:
        print(f"[DEBUG] Конвертация: {webm_path}")
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i", webm_path,
                "-ar", "16000",
                "-ac", "1",
                wav_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            print(f"[ERROR] ffmpeg stderr:\n{result.stderr.decode()}")
            raise Exception("FFmpeg конвертация не удалась")

        return wav_path

    except Exception as e:
        print(f"[ERROR] Конвертация не удалась: {e}")
        raise
