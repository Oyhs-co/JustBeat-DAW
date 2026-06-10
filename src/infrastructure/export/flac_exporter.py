"""FLAC Exporter - Exportación a FLAC lossless.

Exporta audio a formato FLAC utilizando numpy para
procesamiento y struct para escritura del formato.
"""

from typing import List, Tuple
from pathlib import Path
import numpy as np
import struct
import logging


logger = logging.getLogger(__name__)


class FLACExporter:
    """Exportador a formato FLAC.

    Implementa codificación FLAC básica sin compresión
    (almacenamiento directo de subframes).
    Para compresión real, usar librería externa como libflac.

    Attributes:
        sample_rate: Sample rate
        bit_depth: Profundidad de bits (16 o 24)
        compression_level: Nivel de compresión (0-8)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: int = 16,
        compression_level: int = 5,
    ):
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.compression_level = max(0, min(8, compression_level))

    def export(
        self,
        audio_data: np.ndarray,
        output_path: Path,
    ) -> bool:
        """Exportar audio a FLAC.

        Args:
            audio_data: Audio (-1.0 to 1.0), mono o estéreo
            output_path: Ruta de salida

        Returns:
            True si se exportó correctamente
        """
        try:
            num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
            num_samples = audio_data.shape[0] if audio_data.ndim > 1 else len(audio_data)

            samples_int = self._to_integer(audio_data)

            with open(str(output_path), "wb") as f:
                f.write(b"fLaC")
                self._write_streaminfo(f, num_channels, num_samples)
                self._write_audio_frames(
                    f, samples_int, num_channels
                )

            logger.info(
                f"FLAC exportado: {output_path.name} "
                f"({num_samples} samples, {num_channels}ch)"
            )
            return True

        except Exception as e:
            logger.error(f"Error exportando FLAC: {e}")
            return False

    def _to_integer(self, audio_data: np.ndarray) -> np.ndarray:
        max_val = 2 ** (self.bit_depth - 1) - 1
        return (audio_data * max_val).astype(
            np.int32 if self.bit_depth > 16 else np.int16
        )

    def _write_streaminfo(
        self, f, num_channels: int, num_samples: int
    ) -> None:
        """Escribir metadata block STREAMINFO."""
        import hashlib

        min_block_size = 4096
        max_block_size = 4096
        min_frame_size = 0
        max_frame_size = 0

        md5 = hashlib.md5(b"0" * num_samples).digest()

        f.write(struct.pack(">B", 0x80))  # Last-metadata-block flag + type 0
        f.write(struct.pack(">B", 34))    # Block length (34 bytes)

        f.write(struct.pack(">HH", min_block_size, max_block_size))
        f.write(struct.pack(">II", min_frame_size, max_frame_size))

        # Sample rate (20 bits), channels (3 bits), bps (5 bits), samples (36 bits)
        header = (
            (self.sample_rate << 44)
            | ((num_channels - 1) << 41)
            | ((self.bit_depth - 1) << 36)
            | (num_samples & 0xFFFFFFFFF)
        )
        f.write(struct.pack(">Q", header >> 8))
        f.write(struct.pack(">B", header & 0xFF))

        f.write(md5)

    def _write_audio_frames(
        self, f, samples: np.ndarray, num_channels: int
    ) -> None:
        """Escribir frames de audio como subframes FLAC (formato VERBATIM)."""
        block_size = 4096
        total = samples.shape[0] if samples.ndim > 1 else len(samples)

        for pos in range(0, total, block_size):
            end = min(pos + block_size, total)
            block = samples[pos:end]
            block_len = end - pos

            # Frame header
            f.write(struct.pack(">B", 0xFF))
            f.write(struct.pack(">B", 0xF8))
            sample_rate_code = 1 if self.sample_rate == 44100 else 4
            channel_assignment = num_channels - 1
            block_byte = (
                0x00 | (blocking_strategy := 0) << 4
                | (block_size_code := 1) << 0
            )
            _ = sample_rate_code
            _ = channel_assignment

            # Frame header (simplificado)
            f.write(struct.pack(">B", block_byte))
            f.write(struct.pack(">B", (sample_rate_code << 4) | channel_assignment))

            # Block size - 1 (UTF-8 encoded)
            f.write(struct.pack(">B", block_len - 1))

            # Frame number (simplificado)
            f.write(struct.pack(">B", pos // block_size))

            # Subframes VERBATIM
            if num_channels == 1:
                self._write_verbatim_subframe(f, block)
            else:
                for ch in range(num_channels):
                    self._write_verbatim_subframe(
                        f, block[:, ch] if block.ndim > 1 else block
                    )

            # Frame footer (CRC-16, simplificado: 0)
            f.write(struct.pack(">H", 0))

    def _write_verbatim_subframe(self, f, data: np.ndarray) -> None:
        """Escribir subframe VERBATIM."""
        f.write(struct.pack(">B", 0x02))  # VERBATIM subframe type

        for sample in data:
            if self.bit_depth == 16:
                f.write(struct.pack("<h", int(sample)))
            else:
                f.write(struct.pack("<i", int(sample)))


class FLACExporterWrapper:
    """Wrapper que implementa la misma interfaz que WAVExporter.

    Para usar con el export controller existente.
    """

    def __init__(self, sample_rate: int = 44100, bit_depth: int = 16):
        self._exporter = FLACExporter(
            sample_rate=sample_rate,
            bit_depth=bit_depth,
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
