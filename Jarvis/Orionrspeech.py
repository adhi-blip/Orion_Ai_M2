import asyncio
import os
import sys
import json
import pyaudio
import vosk
import pyttsx3
import numpy as np
import resample
import time
from LLM_llama_spch import chat_with_ollama # Import AI response function

# Ensure proper event loop handling for Windows
if sys.platform.startswith("win") and sys.version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize Text-to-Speech Engine
engine = pyttsx3.init()
engine.setProperty("rate", 180)  # Adjust speech speed
engine.setProperty("volume", 1.0)  # Max volume

# Initialize Vosk Speech Recognition Model
VOSK_MODEL_PATH = r"C:\Users\WORKSTATION X\OneDrive\Documents\Jarvis Project\Jarvis\vosk-model-en-us-0.42-gigaspeech"
recognizer_model = vosk.Model(VOSK_MODEL_PATH)
recognizer = vosk.KaldiRecognizer(recognizer_model, 16000)


async def listen():
    """Continuously listens for 'Hey Jarvis' and processes commands."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                    input=True, input_device_index=1,
                    frames_per_buffer=2048)

    stream.start_stream()

    print("Listening for wake word... (Say 'Hey Jarvis')")

    try:
        while True:
            data = stream.read(2048, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()

                if text:
                    print(f"Recognized: {text}")

                    # 🔹 Step 1: Wake Word Detection & Command Extraction
                    if text.startswith("hey jarvis"):
                        command = text.replace("hey jarvis", "").strip()  # Remove wake word
                        if command:
                            print(f"Executing command immediately: {command}")
                            await execute_command(command)  # Process without waiting
                        else:
                            await speak("Yes?")
                            print("Wake word detected! Now listening for commands...")
                            await listen_for_commands(stream)  # Continue listening

    except Exception as e:
        print(f"Error in listening: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()



async def listen_for_commands(stream):
    """
    Listens for commands after wake word detection.
    If no command is spoken within 15 seconds, it goes back to idle mode.
    """
    last_input_time = time.time()

    while True:
        data = stream.read(1024, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            command = result.get("text", "").lower()

            if command:
                print(f"Command Recognized: {command}")
                last_input_time = time.time()  # Reset timer

                # Exit if "stop", "quit", or "exit" is detected
                if command in ["stop", "exit", "quit"]:
                    await speak("Goodbye!")
                    return  # Stops listening for commands and returns to idle

                # Process command with AI
                await execute_command(command)

        # If 15 seconds pass with no input, return to idle
        if time.time() - last_input_time > 15:
            print("No command detected for 15 seconds. Returning to idle...")
            return


async def speak(text):
    """Uses TTS engine to speak the provided text asynchronously."""
    print(f"Speaking: {text}")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, engine.say, text)
    await loop.run_in_executor(None, engine.runAndWait)
    await asyncio.sleep(0.5)  # Short delay to prevent overlapping speech


async def execute_command(command):
    """Handles AI-generated responses and system commands."""
    try:
        response = await chat_with_ollama(command)  # ✅ Correctly awaiting async function
        print(f"LLM Response: {response}")  # DEBUG: Show full response

        if isinstance(response, dict):
            response_type = response.get("type")
            content = response.get("content")

            if response_type == "command":
                if content.lower() in ["exit", "quit", "stop"]:
                    await speak("Exiting. Goodbye!")
                    return False  # Stop loop

                # Restrict commands for security
                allowed_commands = ["notepad", "calc"]  # Example: only allow Notepad and Calculator
                if content.lower() in allowed_commands:
                    os.system(content)  # Execute allowed command
                else:
                    await speak(f"Command '{content}' is not allowed.")

            elif response_type == "response":
                await speak(content)  # Speak AI-generated response
        else:
            print(f"Unexpected response format: {response}")

    except Exception as e:
        print(f"Error in LLM response: {e}")
        await speak("Sorry, I couldn't understand that.")

    return True  # Keep running


async def main():
    """Continuously listens and executes commands."""
    await listen()  # Keep listening indefinitely


if __name__ == "__main__":
    asyncio.run(main())  # Run the main function
