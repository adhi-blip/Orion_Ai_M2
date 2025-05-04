import asyncio
from system_commands import execute_command
from LLM_llama_spch import chat_with_ollama
from chroma_memory import build_prompt,contextual_storage
import pyttsx3
import sys
import vosk
import numpy as np
import resample
import pyaudio
import json
import time
import os

# Ensure proper event loop handling for Windows
if sys.platform.startswith("win") and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize Text-to-Speech Engine
engine = pyttsx3.init()
engine.setProperty("rate", 180)
engine.setProperty("volume", 1.0)

# Initialize Vosk Speech Recognition Model
VOSK_MODEL_PATH = r"C:\Users\WORKSTATION X\OneDrive\Documents\Jarvis Project\Jarvis\vosk-model-en-us-0.42-gigaspeech"
recognizer_model = vosk.Model(VOSK_MODEL_PATH)
recognizer = vosk.KaldiRecognizer(recognizer_model, 16000)

# Audio settings for high-quality mic
INPUT_RATE = 192000
TARGET_RATE = 16000
CHANNELS = 2
BUFFER_SIZE = 4096
DEVICE_INDEX = 1  # Update if needed

def preprocess_audio(data):
    """Convert stereo audio at 192kHz to mono 16kHz for Vosk."""
    audio_data = np.frombuffer(data, dtype=np.int16)
    mono_data = audio_data.reshape(-1, CHANNELS).mean(axis=1).astype(np.int16)
    resampled_data = resample(mono_data, int(len(mono_data) * TARGET_RATE / INPUT_RATE)).astype(np.int16)
    return resampled_data.tobytes()


async def listen():
    """Continuously listens for 'Hey Jarvis' and processes commands."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=INPUT_RATE,
                    input=True, input_device_index=DEVICE_INDEX,
                    frames_per_buffer=BUFFER_SIZE)
    stream.start_stream()

    print("Listening for wake word... (Say 'Hey Jarvis')")

    try:
        while True:
            data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
            processed_data = preprocess_audio(data)

            if recognizer.AcceptWaveform(processed_data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()

                if text:
                    print(f"Recognized: {text}")
                    if text.startswith("hey jarvis"):
                        command = text.replace("hey jarvis", "").strip()
                        if command:
                            print(f"Executing command immediately: {command}")
                            await execute_command(command)
                        else:
                            await speak("Yes?")
                            success = await listen_for_commands(stream)
                            print(success)
                            speak(success)
                            if not success:
                                break

    except Exception as e:
        print(f"Error in listening: {type(e).__name__} - {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


async def listen_for_commands(stream):
    """Listens for commands after wake word detection."""
    last_input_time = time.time()

    while True:
        data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
        processed_data = preprocess_audio(data)

        if recognizer.AcceptWaveform(processed_data):
            result = json.loads(recognizer.Result())
            command = result.get("text", "").lower()

            if command:
                print(f"Command Recognized: {command}")
                last_input_time = time.time()

                if command in ["stop", "exit", "quit"]:
                    await speak("Goodbye!")
                    return

                await execute_command(command)

        if time.time() - last_input_time > 15:
            print("No command detected for 15 seconds. Returning to idle...")
            return


async def speak(text):
    """Speaks the provided text asynchronously."""
    print(f"Speaking: {text}")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, engine.say, text)
    await loop.run_in_executor(None, engine.runAndWait)
    await asyncio.sleep(0.5)


async def execute_command(command):
    """Handles AI-generated responses and system commands."""
    try:
        from chroma_memory import build_prompt, contextual_storage  # Ensure this is at the top

        # Build context-aware prompt
        prompt = build_prompt(command)

        # Call LLM with full prompt
        response = await chat_with_ollama(prompt)

        print(f"LLM Response: {response}")

        if isinstance(response, dict):
            response_type = response.get("type")
            content = response.get("content")

            if response_type == "command":
                if content.lower() in ["exit", "quit", "stop"]:
                    await speak("Exiting. Goodbye!")
                    return False

                allowed_commands = ["notepad", "calc"]
                if content.lower() in allowed_commands:
                    os.system(content)
                else:
                    await speak(f"Command '{content}' is not allowed.")

            elif response_type == "response":
                await speak(content)
                contextual_storage(command,content)
        else:
            print(f"Unexpected response format: {response}")

    except Exception as e:
        print(f"Error in LLM response: {e}")
        await speak("Sorry, I couldn't understand that.")
    return True


async def main():
    await listen()


if __name__ == "__main__":
    asyncio.run(main())
