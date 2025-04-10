import asyncio
import os
import sys
import json
import pyaudio
import vosk
import time
import numpy as np
import sounddevice as sd
from concurrent.futures import ThreadPoolExecutor
from TTS.api import TTS
from LLM_llama_spch import ollama_response  # Import AI response function

# Ensure proper event loop handling for Windows
if sys.platform.startswith("win") and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Global constants
SAMPLE_RATE = 16000
CHUNK_SIZE = 4096  # Increased for better efficiency
WAKE_WORD = "hey jarvis"
IDLE_TIMEOUT = 15  # seconds before returning to idle mode
ALLOWED_COMMANDS = ["notepad", "calc"]  # Example: only allow Notepad and Calculator

# Initialize Coqui TTS
coqui_tts = TTS("tts_models/en/ljspeech/tacotron2-DCA").to("cpu")  # Use "cuda" for GPU

# Cache for Vosk recognizer to prevent recreating it
_recognizer = None
_audio_stream = None
_pyaudio_instance = None

def get_recognizer():
    """Lazy-loading singleton for the speech recognizer."""
    global _recognizer
    if _recognizer is None:
        VOSK_MODEL_PATH = r"C:\Users\WORKSTATION X\OneDrive\Documents\Jarvis Project\Jarvis\vosk-model-en-us-0.22\vosk-model-en-us-0.22"
        model = vosk.Model(VOSK_MODEL_PATH)
        _recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    return _recognizer

def get_audio_stream():
    """Lazy-loading singleton for the audio stream."""
    global _audio_stream, _pyaudio_instance
    if _audio_stream is None:
        _pyaudio_instance = pyaudio.PyAudio()
        _audio_stream = _pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            frames_per_buffer=CHUNK_SIZE,
            input=True
        )
        _audio_stream.start_stream()
    return _audio_stream

def cleanup_audio():
    """Clean up audio resources."""
    global _audio_stream, _pyaudio_instance
    if _audio_stream:
        _audio_stream.stop_stream()
        _audio_stream.close()
        _audio_stream = None
    if _pyaudio_instance:
        _pyaudio_instance.terminate()
        _pyaudio_instance = None

async def recognize_speech(stream):
    """Process audio and return recognized text."""
    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
    if get_recognizer().AcceptWaveform(data):
        result = json.loads(get_recognizer().Result())
        return result.get("text", "").lower()
    return ""

async def speak(text):
    """Uses Coqui TTS to generate and play speech in real-time."""
    if not text:
        return

    print(f"Speaking: {text}")

    # Generate speech waveform
    wav = coqui_tts.tts(text)

    # Convert to numpy array for playback
    wav = np.array(wav, dtype=np.float32)

    # Play generated speech in real-time
    sd.play(wav, samplerate=22050)
    sd.wait()  # Wait until audio playback finishes

async def listen():
    """Continuously listens for 'Hey Jarvis' and processes commands."""
    print("Listening for wake word... (Say 'Hey Jarvis')")

    try:
        stream = get_audio_stream()

        while True:
            text = await recognize_speech(stream)

            if text:
                print(f"Recognized: {text}")

                # Check for wake word
                if WAKE_WORD in text:
                    # Extract command after wake word
                    command = text.replace(WAKE_WORD, "").strip()

                    if command:
                        print(f"Executing command immediately: {command}")
                        await execute_command(command)
                    else:
                        await speak("Yes?")
                        print("Wake word detected! Now listening for commands...")
                        await listen_for_commands(stream)
                        print("Listening for wake word... (Say 'Hey Jarvis')")

            await asyncio.sleep(0.01)  # Prevent CPU overuse

    except Exception as e:
        print(f"Error in listening: {e}")
    finally:
        cleanup_audio()

async def listen_for_commands(stream):
    """Listens for commands after wake word detection."""
    last_input_time = time.time()

    while True:
        text = await recognize_speech(stream)

        if text:
            print(f"Command Recognized: {text}")
            last_input_time = time.time()  # Reset timer

            if text in ["stop", "exit", "quit"]:
                await speak("Goodbye!")
                return

            await execute_command(text)

        if time.time() - last_input_time > IDLE_TIMEOUT:
            print(f"No command detected for {IDLE_TIMEOUT} seconds. Returning to idle...")
            return

        await asyncio.sleep(0.01)

async def execute_command(command):
    """Handles AI-generated responses and system commands."""
    try:
        response_task = asyncio.create_task(ollama_response(command))

        try:
            response = await asyncio.wait_for(response_task, timeout=5.0)  # Timeout after 5s
        except asyncio.TimeoutError:
            print("LLM response timed out")
            await speak("I'm having trouble processing that request right now.")
            return True

        print(f"LLM Response: {response}")

        if isinstance(response, dict):
            response_type = response.get("type")
            content = response.get("content")

            if response_type == "command":
                if content.lower() in ["exit", "quit", "stop"]:
                    await speak("Exiting. Goodbye!")
                    return False  # Stop loop

                if content.lower() in ALLOWED_COMMANDS:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, os.system, content)
                else:
                    await speak(f"Command '{content}' is not allowed.")

            elif response_type == "response":
                await speak(content)
        else:
            print(f"Unexpected response format: {response}")

    except Exception as e:
        print(f"Error in LLM response: {e}")
        await speak("Sorry, I couldn't understand that.")

    return True  # Keep running

async def main():
    """Continuously listens and executes commands."""
    try:
        await listen()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup_audio()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")

