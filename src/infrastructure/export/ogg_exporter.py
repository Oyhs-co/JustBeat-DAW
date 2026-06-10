"""OGG Exporter - Exportación a OGG Vorbis.

Exporta audio a formato OGG Vorbis usando numpy para
procesamiento y struct para escritura del formato OGG.

Nota:
    OGG Vorbis es un formato con compresión con pérdida.
    Para compresión/encoding real se necesita libvorbis.
    Esta implementación empaqueta PCM como OGG básico.
"""

from typing import Optional
from pathlib import Path
import numpy as np
import struct
import logging


logger = logging.getLogger(__name__)


class OGGExporter:
    """Exportador a formato OGG Vorbis.

    Attributes:
        sample_rate: Sample rate (44100 recomendado)
        quality: Calidad Vorbis (-0.1 a 1.0, donde 1.0 es mejor)
        bit_depth: Profundidad de bits (16 o 24)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        quality: float = 0.5,
        bit_depth: int = 16,
    ):
        self.sample_rate = sample_rate
        self.quality = max(-0.1, min(1.0, quality))
        self.bit_depth = bit_depth

    def export(
        self,
        audio_data: np.ndarray,
        file_path: Path,
        progress_callback=None
    ) -> bool:
        """Exportar audio a OGG Vorbis.

        Args:
            audio_data: Array numpy con audio (shape: samples o samples x canales).
            file_path: Ruta de salida.
            progress_callback: Callback opcional para progreso.

        Returns:
            True si la exportación fue exitosa.
        """
        try:
            if audio_data.size == 0:
                logger.error("No hay datos de audio para exportar")
                return False

            audio_data = np.clip(audio_data, -1.0, 1.0)

            if audio_data.ndim == 1:
                channels = 1
                samples_2d = audio_data.reshape(-1, 1)
            elif audio_data.ndim == 2:
                channels = audio_data.shape[1]
                samples_2d = audio_data
            else:
                logger.error(f"Dimensión de audio no soportada: {audio_data.ndim}")
                return False

            num_samples = samples_2d.shape[0]

            if progress_callback:
                progress_callback(0.1)

            pcm_data = self._to_pcm(samples_2d)

            if progress_callback:
                progress_callback(0.3)

            serial = 0
            ogg_data = self._create_ogg(pcm_data, channels, self.sample_rate, serial)

            if progress_callback:
                progress_callback(0.8)

            file_path.write_bytes(ogg_data)

            duration = num_samples / self.sample_rate
            logger.info(
                f"OGG exportado: {file_path} "
                f"({duration:.1f}s, {channels}ch, "
                f"{self.sample_rate}Hz, calidad={self.quality})"
            )

            if progress_callback:
                progress_callback(1.0)

            return True

        except Exception as e:
            logger.error(f"Error exportando OGG: {e}")
            return False

    def _to_pcm(self, samples: np.ndarray) -> bytes:
        if self.bit_depth == 16:
            pcm = (samples * 32767).astype(np.int16)
        elif self.bit_depth == 24:
            pcm_32 = (samples * 8388607).astype(np.int32)
            pcm_bytes = bytearray()
            for s in pcm_32.reshape(-1):
                pcm_bytes.extend(struct.pack("<i", int(s))[:3])
            return bytes(pcm_bytes)
        else:
            pcm = (samples * 2147483647).astype(np.int32)
        return pcm.tobytes()

    def _create_ogg(self, pcm_data: bytes, channels: int, sample_rate: int, serial: int) -> bytes:
        result = bytearray()

        # OGG page header
        result.extend(b"OggS")
        result.extend(struct.pack("<B", 0))
        result.extend(struct.pack("<B", 0x02))
        result.extend(struct.pack("<q", 0))
        result.extend(struct.pack("<I", serial))
        result.extend(struct.pack("<I", 0))
        result.extend(struct.pack("<I", 0))
        result.extend(struct.pack("<B", 0))

        # Vorbis identification header
        vorbis_id = bytearray()
        vorbis_id.extend(b"\x01vorbis")
        vorbis_id.extend(struct.pack("<I", 0))
        vorbis_id.extend(struct.pack("<I", sample_rate))
        vorbis_id.extend(struct.pack("<I", 0))
        vorbis_id.extend(struct.pack("<B", channels))
        vorbis_id.extend(struct.pack("<B", 1))
        vorbis_id.extend(struct.pack("<i", int(self.quality * 256)))

        # Comment header (simple)
        comment = bytearray()
        comment.extend(b"\x03vorbis")
        comment.extend(struct.pack("<I", 0))
        comment.extend(b"JustBeat-DAW")

        # Audio data pages
        page_size = 4096
        offset = 0
        page_no = 1
        granule = 0

        while offset < len(pcm_data):
            chunk = pcm_data[offset:offset + page_size]
            is_last = (offset + len(chunk) >= len(pcm_data))

            page = bytearray()
            page.extend(b"OggS")
            page.extend(struct.pack("<B", 0))
            page.extend(struct.pack("<B", 0x04 if is_last else 0x00))
            page.extend(struct.pack("<q", granule))
            page.extend(struct.pack("<I", serial))
            page.extend(struct.pack("<I", page_no))
            page.extend(struct.pack("<I", 0))
            page.extend(struct.pack("<B", 1))

            page.extend(struct.pack("<I", len(chunk)))
            page.extend(struct.pack("<B", 1))
            page.extend(chunk)

            result.extend(page)
            offset += len(chunk)
            page_no += 1
            granule += len(chunk) // (channels * (self.bit_depth // 8))

        return bytes(result)
