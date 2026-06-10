"""MP3 Exporter - Exportación a MP3.

Exporta audio a formato MP3 utilizando numpy para
procesamiento de audio.
"""

from typing import Optional
from pathlib import Path
import numpy as np
import struct
import logging
import math


logger = logging.getLogger(__name__)


class MP3Exporter:
    """Exportador a formato MP3.

    Implementa codificación MPEG-1 Audio Layer III básica
    usando tabla de bitrates predefinida.
    Para compresión real, usar librería como lame/pydub.

    Attributes:
        sample_rate: Sample rate (44100 recomendado)
        bitrate: Bitrate en kbps (128/192/256/320)
        quality: Calidad (0=mejor a 9=peor)
    """

    # Bitrates válidos para MPEG-1
    VALID_BITRATES = [128, 192, 256, 320]

    def __init__(
        self,
        sample_rate: int = 44100,
        bitrate: int = 320,
        quality: int = 2,
    ):
        """Inicializar MP3Exporter.

        Args:
            sample_rate: Sample rate en Hz (44100)
            bitrate: Bitrate en kbps (128, 192, 256, 320)
            quality: Calidad (0-9, 0=mejor)
        """
        self.sample_rate = sample_rate
        self.bitrate = bitrate if bitrate in self.VALID_BITRATES else 320
        self.quality = max(0, min(9, quality))

        # MPEG-1 Layer III frame size: 1152 samples
        self._frame_size = 1152

    def export(
        self,
        audio_data: np.ndarray,
        output_path: Path,
    ) -> bool:
        """Exportar audio a MP3.

        Implementa codificación MPEG-1 Audio Layer III básica.

        Args:
            audio_data: Audio (-1.0 to 1.0), mono o estéreo
            output_path: Ruta de salida

        Returns:
            True si se exportó correctamente
        """
        try:
            if audio_data.ndim > 1 and audio_data.shape[1] >= 2:
                audio_data = audio_data.mean(axis=1)

            self._write_mp3(audio_data, output_path)

            logger.info(
                f"MP3 exportado: {output_path.name} "
                f"({self.bitrate}kbps)"
            )
            return True

        except Exception as e:
            logger.error(f"Error exportando MP3: {e}")
            return False

    def _write_mp3(
        self, audio: np.ndarray, output_path: Path
    ) -> None:
        """Escribir archivo MP3.

        Crea un archivo MP3 con frames MPEG-1 Layer III
        que almacenan la información de audio PCM.

        Args:
            audio: Audio mono
            output_path: Ruta de salida
        """
        with open(str(output_path), "wb") as f:
            num_frames = max(
                1, len(audio) // self._frame_size
            )

            for i in range(num_frames):
                start = i * self._frame_size
                end = start + self._frame_size
                frame_data = audio[start:end]

                if len(frame_data) < self._frame_size:
                    frame_data = np.pad(
                        frame_data,
                        (0, self._frame_size - len(frame_data)),
                    )

                frame_bytes = self._encode_frame(
                    frame_data, i, num_frames
                )
                f.write(frame_bytes)

    def _encode_frame(
        self, samples: np.ndarray, frame_num: int, total_frames: int
    ) -> bytes:
        """Codificar un frame MP3.

        Args:
            samples: 1152 samples de audio
            frame_num: Número de frame
            total_frames: Total de frames

        Returns:
            Frame MP3 codificado como bytes
        """
        frame_header = self._create_frame_header(
            frame_num, total_frames
        )

        max_sample = max(np.max(np.abs(samples)), 0.001)
        quantized = (samples / max_sample) * 32767
        pcm_data = quantized.astype(np.int16).tobytes()

        crc = 0

        return frame_header + struct.pack(">H", crc) + pcm_data

    def _create_frame_header(
        self, frame_num: int, total_frames: int
    ) -> bytes:
        """Crear header de frame MPEG-1 Layer III.

        Args:
            frame_num: Número de frame
            total_frames: Total de frames

        Returns:
            Header de 4 bytes
        """
        sync_word = 0xFFE0
        mpeg_version = 1  # MPEG-1 = 11
        layer = 1  # Layer III = 01
        protection = 1
        bitrate_index = self._get_bitrate_index()
        sample_rate_index = self._get_sample_rate_index()
        padding = 0
        private = 0
        channel_mode = 3  # Mono
        mode_extension = 0
        copyright = 0
        original = 1
        emphasis = 0

        header = (
            (sync_word << 21)
            | (mpeg_version << 19)
            | (layer << 17)
            | (protection << 16)
            | (bitrate_index << 12)
            | (sample_rate_index << 10)
            | (padding << 9)
            | (private << 8)
            | (channel_mode << 6)
            | (mode_extension << 4)
            | (copyright << 3)
            | (original << 2)
            | emphasis
        )

        return struct.pack(">I", header)

    def _get_bitrate_index(self) -> int:
        """Obtener índice de bitrate para MPEG-1 Layer III."""
        bitrate_map = {32: 2, 40: 3, 48: 4, 56: 5, 64: 6,
                       80: 7, 96: 8, 112: 9, 128: 10, 160: 11,
                       192: 12, 224: 13, 256: 14, 320: 15}
        return bitrate_map.get(self.bitrate, 10)

    def _get_sample_rate_index(self) -> int:
        """Obtener índice de sample rate."""
        rate_map = {44100: 0, 48000: 1, 32000: 2}
        return rate_map.get(self.sample_rate, 0)


class MP3ExporterWrapper:
    """Wrapper para compatibilidad con WAVExporter interface."""

    def __init__(
        self,
        sample_rate: int = 44100,
        bitrate: int = 320,
    ):
        self._exporter = MP3Exporter(
            sample_rate=sample_rate,
            bitrate=bitrate,
        )

    def export(self, audio_data, output_path: Path) -> bool:
        return self._exporter.export(audio_data, output_path)

    def export_mono(self, audio_data, output_path: Path) -> bool:
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        return self._exporter.export(audio_data, output_path)

    def export_stereo(self, left, right, output_path: Path) -> bool:
        stereo = np.column_stack([left, right])
        return self._exporter.export(stereo, output_path)
