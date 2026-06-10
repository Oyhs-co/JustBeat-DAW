import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None  # type: ignore[assignment]
    logger.warning("sounddevice no disponible, audio playback desactivado")


@dataclass
class AudioDeviceInfo:
    name: str
    index: int
    channels_in: int
    channels_out: int
    sample_rates: List[int] = field(default_factory=list)
    is_asio: bool = False
    latency_in: float = 0.0
    latency_out: float = 0.0


class DeviceManager:
    def __init__(self) -> None:
        self._device_name: Optional[str] = None
        self._device_index: Optional[int] = None
        self._asio_device: Optional[str] = None
        self._available_devices: List[AudioDeviceInfo] = []
        self._input_latency: float = 0.0
        self._output_latency: float = 0.0
        self._latency_compensation_samples: int = 0

        self._on_device_changed: Optional[callable] = None

        if HAS_SOUNDDEVICE:
            self.scan_devices()

    def set_on_device_changed(self, callback: callable) -> None:
        self._on_device_changed = callback

    def scan_devices(self) -> None:
        if not HAS_SOUNDDEVICE:
            return

        sd_local = sd

        try:
            devices = sd_local.query_devices()
            self._available_devices = []

            for i, dev in enumerate(devices):
                dev_info = AudioDeviceInfo(
                    name=dev["name"],
                    index=i,
                    channels_in=dev["max_input_channels"],
                    channels_out=dev["max_output_channels"],
                    sample_rates=sorted(set([
                        int(dev.get("default_samplerate", 44100))
                    ])),
                    is_asio="ASIO" in dev["name"].upper(),
                    latency_in=dev.get("default_low_input_latency", 0.0),
                    latency_out=dev.get("default_low_output_latency", 0.0),
                )
                self._available_devices.append(dev_info)

            logger.info(
                f"Dispositivos de audio: {len(self._available_devices)} encontrados"
            )

            self._auto_select_device()

        except Exception as e:
            logger.warning(f"Error escaneando dispositivos: {e}")

    def _auto_select_device(self) -> None:
        if not HAS_SOUNDDEVICE or not self._available_devices:
            return

        asio_devices = [
            d for d in self._available_devices
            if d.is_asio and d.channels_out >= 2
        ]

        if asio_devices:
            best = asio_devices[0]
            self._device_name = best.name
            self._device_index = best.index
            self._input_latency = best.latency_in
            self._output_latency = best.latency_out
            logger.info(f"Dispositivo ASIO seleccionado: {best.name}")
            return

        output_devices = [
            d for d in self._available_devices if d.channels_out >= 2
        ]

        if output_devices:
            best = max(output_devices, key=lambda d: d.channels_out)
            self._device_name = best.name
            self._device_index = best.index
            self._input_latency = best.latency_in
            self._output_latency = best.latency_out
            logger.info(
                f"Dispositivo seleccionado: {best.name} ({best.channels_out} canales)"
            )
            return

        try:
            default = sd.query_devices(kind="output")
            if default:
                self._device_name = default["name"]
                self._device_index = default["index"]
                logger.info(f"Dispositivo por defecto: {self._device_name}")
        except Exception:
            pass

    def get_available_devices(self) -> List[AudioDeviceInfo]:
        return list(self._available_devices)

    def set_device(self, device_name: str, is_asio: bool = False) -> bool:
        logger.info(f"Set audio device requested: {device_name}, is_asio={is_asio}")
        for dev in self._available_devices:
            if dev.name == device_name:
                self._device_name = dev.name
                self._device_index = dev.index

                if dev.is_asio:
                    self._asio_device = dev.name

                self._input_latency = dev.latency_in
                self._output_latency = dev.latency_out

                if self._on_device_changed:
                    self._on_device_changed()

                logger.info(f"Dispositivo cambiado a: {device_name}")
                return True

        logger.warning(f"Dispositivo no encontrado: {device_name}")
        return False

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name

    @property
    def device_index(self) -> Optional[int]:
        return self._device_index

    @property
    def output_latency(self) -> float:
        return self._output_latency * 1000.0

    @property
    def input_latency(self) -> float:
        return self._input_latency * 1000.0

    @property
    def total_latency(self) -> float:
        return (self._input_latency + self._output_latency) * 1000.0
