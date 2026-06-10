"""Test script for audio playback."""
import sys
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test audio stream directly
print("Testing audio stream...")

import sounddevice as sd
import numpy as np

def audio_callback(outdata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    # Generate simple tone
    t = np.linspace(0, frames/44100, frames)
    freq = 440  # A4
    output = 0.3 * np.sin(2 * np.pi * freq * t)
    outdata[:] = np.column_stack([output, output])

try:
    # Get default output device
    devices = sd.query_devices()
    print(f"Devices: {devices[:200]}...")
    
    # Try to create and start stream with explicit device
    stream = sd.OutputStream(
        samplerate=44100,
        blocksize=256,
        channels=2,
        callback=audio_callback,
        device=4  # Explicit device
    )
    print("Stream created, starting...")
    stream.start()
    print("Stream started, playing for 1 second...")
    time.sleep(1)
    print("Stopping...")
    stream.stop()
    stream.close()
    print("Done!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
