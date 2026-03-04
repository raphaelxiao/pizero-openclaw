import os
import config
from dotenv import load_dotenv

load_dotenv()

# Override config for testing GLM
config.AUDIO_PROVIDER = "glm"
config.GLM_API_KEY = os.environ.get("GLM_API_KEY")

if not config.GLM_API_KEY:
    print("Please set GLM_API_KEY in your .env file")
    exit(1)

import transcribe_glm
import tts_glm
import time

def test_glm_stt():
    print("Testing GLM STT...")
    # Create a dummy wav file if one doesn't exist
    import wave
    import struct
    dummy_wav = "test_dummy.wav"
    with wave.open(dummy_wav, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        for _ in range(16000): # 1 second of silence
            f.writeframesraw(struct.pack('<h', 0))
    
    try:
        transcript = transcribe_glm.transcribe(dummy_wav)
        print("Transcript:", transcript)
    except Exception as e:
        print("STT Error:", e)
    finally:
        if os.path.exists(dummy_wav):
            os.remove(dummy_wav)

def test_glm_tts():
    print("\nTesting GLM TTS...")
    player = tts_glm.TTSPlayer()
    try:
        player.submit("你好，这是一个智谱文本转语音系统测试的样例。")
        player.flush()
        print("TTS playback completed or flushed.")
    except Exception as e:
        print("TTS Error:", e)
    finally:
        player.cancel()
        time.sleep(1)

if __name__ == "__main__":
    test_glm_stt()
    test_glm_tts()
