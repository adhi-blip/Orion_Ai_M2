import pyaudio
import wave
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import spectrogram
import simpleaudio as sa  # For playback

# Audio Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

def record_audio():
    """Records audio and saves it to a file."""
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("* Recording...")

    frames = [stream.read(CHUNK) for _ in range(int(RATE / CHUNK * RECORD_SECONDS))]

    print("* Done recording")

    # Stop stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save to file
    with wave.open(WAVE_OUTPUT_FILENAME, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

def play_audio():
    """Plays the recorded audio file."""
    print("* Playing audio...")
    wave_obj = sa.WaveObject.from_wave_file(WAVE_OUTPUT_FILENAME)
    play_obj = wave_obj.play()
    play_obj.wait_done()  # Wait until playback is finished
    print("* Playback finished.")

def plot_waveform():
    """Plots the waveform of the saved audio file."""
    sample_rate, audio_data = wavfile.read(WAVE_OUTPUT_FILENAME)

    time = np.linspace(0, len(audio_data) / sample_rate, num=len(audio_data))

    plt.figure(figsize=(10, 4))
    plt.plot(time, audio_data, color="blue")
    plt.title("Audio Waveform")
    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.show()

def plot_spectrogram():
    """Plots the spectrogram of the saved audio file."""
    sample_rate, audio_data = wavfile.read(WAVE_OUTPUT_FILENAME)

    frequencies, time, Sxx = spectrogram(audio_data, sample_rate)

    plt.figure(figsize=(10, 4))
    plt.pcolormesh(time, frequencies, 10 * np.log10(Sxx), shading="auto")
    plt.title("Audio Spectrogram")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")
    plt.colorbar(label="Intensity [dB]")
    plt.show()