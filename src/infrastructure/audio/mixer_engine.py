import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

from src.infrastructure.audio.mixer_channel import ChannelStrip, Send
from src.infrastructure.audio.mixer_bus import Bus


logger = logging.getLogger(__name__)


class MixerEngine:
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 512
    ):
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size

        self._channels: Dict[str, ChannelStrip] = {}
        self._buses: Dict[str, Bus] = {}
        self._master = ChannelStrip(id="master", name="Master", volume=1.0)
        self._any_solo: bool = False
        self._routing_matrix: Dict[str, List[str]] = {}
        self._sidechain_buffers: Dict[str, np.ndarray] = {}

        self._dc_filter_state: Dict[str, float] = {"master": 0.0}
        self._dc_filter_coef: float = 0.999
        self._input_latency: int = 0
        self._output_latency: int = 0

        logger.info(f"MixerEngine: {sample_rate}Hz, buffer {buffer_size}")

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def master(self) -> ChannelStrip:
        return self._master

    # === Gestión de Canales ===

    def add_channel(self, channel_id: str, name: str) -> ChannelStrip:
        if channel_id in self._channels:
            raise ValueError(f"Canal {channel_id} ya existe")

        channel = ChannelStrip(id=channel_id, name=name)
        self._channels[channel_id] = channel
        self._routing_matrix[channel_id] = []
        logger.info(f"Canal añadido: {name}")
        return channel

    def remove_channel(self, channel_id: str) -> bool:
        if channel_id in self._channels:
            del self._channels[channel_id]
            self._routing_matrix.pop(channel_id, None)
            self._sidechain_buffers.pop(channel_id, None)
            logger.info(f"Canal removido: {channel_id}")
            return True
        return False

    def get_channel(self, channel_id: str) -> Optional[ChannelStrip]:
        return self._channels.get(channel_id)

    def get_all_channels(self) -> List[ChannelStrip]:
        return list(self._channels.values())

    def set_channel_volume(self, channel_id: str, volume: float) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False

        volume = max(0.0, min(1.0, volume))

        if channel.link_group:
            ratio = volume / (channel.volume + 0.001)
            for ch in self._channels.values():
                if ch.link_group == channel.link_group and ch.id != channel_id:
                    ch.volume = max(0.0, min(1.0, ch.volume * ratio))

        channel.volume = volume
        return True

    def set_channel_pan(self, channel_id: str, pan: float) -> bool:
        channel = self.get_channel(channel_id)
        if channel:
            channel.pan = max(-1.0, min(1.0, pan))
            return True
        return False

    def set_channel_mute(self, channel_id: str, mute: bool) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False

        channel.mute = mute

        if channel.mute_group:
            for ch in self._channels.values():
                if ch.mute_group == channel.mute_group and ch.id != channel_id:
                    ch.mute = mute

        self._update_solo_state()
        return True

    def set_channel_solo(self, channel_id: str, solo: bool) -> bool:
        channel = self.get_channel(channel_id)
        if channel:
            channel.solo = solo
            self._update_solo_state()
            return True
        return False

    def set_channel_solo_safe(self, channel_id: str, safe: bool) -> bool:
        channel = self.get_channel(channel_id)
        if channel:
            channel.solo_safe = safe
            return True
        return False

    def set_channel_mute_group(self, channel_id: str, group_id: Optional[str]) -> bool:
        channel = self.get_channel(channel_id)
        if channel:
            channel.mute_group = group_id
            return True
        return False

    def set_channel_link_group(self, channel_id: str, group_id: Optional[str]) -> bool:
        channel = self.get_channel(channel_id)
        if channel:
            channel.link_group = group_id
            return True
        return False

    def _update_solo_state(self) -> None:
        self._any_solo = any(c.solo for c in self._channels.values())

    def get_channel_audible(self, channel_id: str) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False

        if self._any_solo:
            if channel.solo:
                return True
            if channel.solo_safe:
                return not channel.mute
            return False

        return not channel.mute

    # === Gestión de Sends ===

    def add_send(
        self,
        channel_id: str,
        send_id: str,
        name: str,
        target_bus: str,
        amount: float = 0.0,
        pre_fader: bool = False,
    ) -> Optional[Send]:
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        send = Send(id=send_id, name=name, target_bus=target_bus, amount=amount, pre_fader=pre_fader)
        channel.sends.append(send)
        return send

    def remove_send(self, channel_id: str, send_id: str) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False
        channel.sends = [s for s in channel.sends if s.id != send_id]
        return True

    def set_send_amount(self, channel_id: str, send_id: str, amount: float) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False
        for send in channel.sends:
            if send.id == send_id:
                send.amount = max(0.0, min(1.0, amount))
                return True
        return False

    # === Routing Matrix ===

    def route_channel_to_bus(self, channel_id: str, bus_id: str) -> bool:
        if channel_id not in self._channels:
            return False
        if bus_id not in self._buses:
            return False

        if bus_id not in self._routing_matrix.get(channel_id, []):
            self._routing_matrix.setdefault(channel_id, []).append(bus_id)

        bus = self._buses[bus_id]
        if channel_id not in bus.channels:
            bus.channels.append(channel_id)

        logger.info(f"Canal {channel_id} enrutado a bus {bus_id}")
        return True

    def unroute_channel_from_bus(self, channel_id: str, bus_id: str) -> bool:
        if channel_id in self._routing_matrix:
            if bus_id in self._routing_matrix[channel_id]:
                self._routing_matrix[channel_id].remove(bus_id)
                if bus_id in self._buses:
                    bus = self._buses[bus_id]
                    if channel_id in bus.channels:
                        bus.channels.remove(channel_id)
                return True
        return False

    def get_channel_routes(self, channel_id: str) -> List[str]:
        return self._routing_matrix.get(channel_id, [])

    # === Sidechain ===

    def set_sidechain_source(self, channel_id: str, source_id: Optional[str]) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False

        old_source = channel.sidechain_source
        if old_source and old_source in self._sidechain_buffers:
            del self._sidechain_buffers[old_source]

        channel.sidechain_source = source_id

        if source_id and source_id in self._channels:
            self._sidechain_buffers[source_id] = np.zeros(self._buffer_size, dtype=np.float32)

        return True

    def get_sidechain_audio(self, source_id: str) -> Optional[np.ndarray]:
        return self._sidechain_buffers.get(source_id)

    def _update_sidechain(self, source_id: str, audio: np.ndarray) -> None:
        if source_id in self._sidechain_buffers:
            rms = np.sqrt(np.mean(audio ** 2))
            self._sidechain_buffers[source_id] = np.full(self._buffer_size, rms, dtype=np.float32)

    # === Gestión de Buses ===

    def add_bus(self, bus_id: str, name: str) -> Bus:
        if bus_id in self._buses:
            raise ValueError(f"Bus {bus_id} ya existe")

        bus = Bus(id=bus_id, name=name)
        self._buses[bus_id] = bus
        logger.info(f"Bus añadido: {name}")
        return bus

    def remove_bus(self, bus_id: str) -> bool:
        if bus_id in self._buses:
            for channel_routes in self._routing_matrix.values():
                if bus_id in channel_routes:
                    channel_routes.remove(bus_id)
            del self._buses[bus_id]
            return True
        return False

    def get_bus(self, bus_id: str) -> Optional[Bus]:
        return self._buses.get(bus_id)

    def get_all_buses(self) -> List[Bus]:
        return list(self._buses.values())

    # === Procesamiento ===

    def _apply_dc_filter(self, audio: np.ndarray, bus_id: str) -> np.ndarray:
        if bus_id not in self._dc_filter_state:
            self._dc_filter_state[bus_id] = 0.0

        state = self._dc_filter_state[bus_id]
        coef = self._dc_filter_coef

        if audio.ndim == 2:
            mono = audio.mean(axis=0)
        else:
            mono = audio

        for i in range(len(mono)):
            state = coef * state + mono[i]
            dc = mono[i] - state
            if audio.ndim == 2:
                audio[0, i] -= dc * 0.5
                audio[1, i] -= dc * 0.5
            else:
                audio[i] -= dc

        self._dc_filter_state[bus_id] = state
        return audio

    def process_stereo(self, inputs: Dict[str, np.ndarray], num_samples: int) -> np.ndarray:
        output = np.zeros((2, num_samples), dtype=np.float32)

        if not inputs:
            return output

        for channel_id, audio_data in inputs.items():
            channel = self.get_channel(channel_id)
            if not channel:
                continue

            if not self.get_channel_audible(channel_id):
                continue

            if audio_data.ndim == 1:
                audio_stereo = np.stack([audio_data, audio_data])
            else:
                audio_stereo = audio_data.copy()

            if channel.sidechain_source:
                self._update_sidechain(channel.sidechain_source, audio_data)

            for send in channel.sends:
                if send.pre_fader and send.amount > 0:
                    bus = self._buses.get(send.target_bus)
                    if bus:
                        bus_audio = audio_stereo * send.amount * bus.volume
                        output += bus_audio

            processed = audio_stereo
            for effect in channel.effects:
                if hasattr(effect, 'process'):
                    try:
                        result = effect.process(processed)
                        if isinstance(result, np.ndarray):
                            if result.ndim == 1:
                                result = np.stack([result, result])
                            processed = result
                    except Exception as e:
                        logger.warning(f"Error en efecto {effect}: {e}")

            audio_stereo = processed * channel.volume
            audio_stereo = self._apply_pan(audio_stereo, channel.pan)
            output += audio_stereo

            for send in channel.sends:
                if not send.pre_fader and send.amount > 0:
                    bus = self._buses.get(send.target_bus)
                    if bus:
                        bus_audio = audio_stereo * send.amount * bus.volume
                        output += bus_audio

            for bus_id in self._routing_matrix.get(channel_id, []):
                bus = self._buses.get(bus_id)
                if bus:
                    output += audio_stereo * bus.volume

        output *= self._master.volume
        output = self._apply_dc_filter(output, "master")
        self._update_meters(inputs)

        return output

    def process_quad(self, inputs: Dict[str, np.ndarray], num_samples: int) -> np.ndarray:
        if num_samples <= 0:
            return np.zeros((4, 1), dtype=np.float32)

        output = np.zeros((4, num_samples), dtype=np.float32)

        if not inputs:
            return output

        for channel_id, audio_data in inputs.items():
            channel = self.get_channel(channel_id)
            if not channel:
                continue

            if not self.get_channel_audible(channel_id):
                continue

            if channel.sidechain_source:
                self._update_sidechain(channel.sidechain_source, audio_data)

            if audio_data.ndim == 1:
                audio_quad = np.tile(audio_data, (4, 1))
            elif audio_data.shape[0] == 2:
                audio_quad = np.vstack([audio_data[0], audio_data[1], audio_data[0], audio_data[1]])
            else:
                audio_quad = audio_data

            for send in channel.sends:
                if send.pre_fader and send.amount > 0:
                    bus = self._buses.get(send.target_bus)
                    if bus:
                        bus_audio = audio_quad * send.amount * bus.volume
                        output += bus_audio

            processed = audio_quad
            for effect in channel.effects:
                if hasattr(effect, 'process'):
                    try:
                        result = effect.process(processed)
                        if isinstance(result, np.ndarray):
                            processed = result
                    except Exception as e:
                        logger.warning(f"Error en efecto {effect}: {e}")

            audio_quad = processed * channel.volume
            if channel.pan != 0:
                fbm = abs(channel.pan)
                audio_quad[2] = audio_quad[0] * fbm
                audio_quad[3] = audio_quad[1] * fbm

            output += audio_quad

            for send in channel.sends:
                if not send.pre_fader and send.amount > 0:
                    bus = self._buses.get(send.target_bus)
                    if bus:
                        bus_audio = audio_quad * send.amount * bus.volume
                        output += bus_audio

            for bus_id in self._routing_matrix.get(channel_id, []):
                bus = self._buses.get(bus_id)
                if bus:
                    output += audio_quad * bus.volume

        output *= self._master.volume

        mono_out = output.mean(axis=0)
        output = self._apply_dc_filter(np.vstack([mono_out, mono_out]), "master_quad")
        output = np.vstack([output[0], output[1], output[0], output[1]])

        self._update_meters(inputs)

        return output

    def _apply_pan(self, audio: np.ndarray, pan: float) -> np.ndarray:
        if audio.shape[0] != 2:
            return audio

        angle = (pan + 1.0) * math.pi / 4.0
        left = math.cos(angle)
        right = math.sin(angle)

        output = audio.copy()
        output[0] *= left
        output[1] *= right

        return output

    def _update_meters(self, inputs: Dict[str, np.ndarray]) -> None:
        for channel_id, audio_data in inputs.items():
            channel = self.get_channel(channel_id)
            if not channel:
                continue

            if audio_data.ndim == 1:
                peak = np.abs(audio_data).max()
                channel.peak_left = peak
                channel.peak_right = peak
            else:
                channel.peak_left = np.abs(audio_data[0]).max()
                channel.peak_right = np.abs(audio_data[1]).max()

    def get_meter_levels(self) -> Dict[str, Tuple[float, float]]:
        levels = {}
        for channel_id, channel in self._channels.items():
            levels[channel_id] = (channel.peak_left, channel.peak_right)
        levels["master"] = (self._master.peak_left, self._master.peak_right)
        return levels

    def reset_meters(self) -> None:
        for channel in self._channels.values():
            channel.peak_left = 0.0
            channel.peak_right = 0.0
        self._master.peak_left = 0.0
        self._master.peak_right = 0.0

    # === Utilidades ===

    def get_channel_count(self) -> int:
        return len(self._channels)

    def get_bus_count(self) -> int:
        return len(self._buses)

    def clear(self) -> None:
        self._channels.clear()
        self._buses.clear()
        self._routing_matrix.clear()
        self._sidechain_buffers.clear()
        self._dc_filter_state = {"master": 0.0}
        self._master = ChannelStrip(id="master", name="Master", volume=1.0)
        logger.info("Mixer limpiado")

    # === Serialización ===

    def to_dict(self) -> dict:
        return {
            "channels": {
                ch_id: {
                    "id": ch.id,
                    "name": ch.name,
                    "volume": ch.volume,
                    "pan": ch.pan,
                    "mute": ch.mute,
                    "solo": ch.solo,
                    "solo_safe": ch.solo_safe,
                    "mute_group": ch.mute_group,
                    "link_group": ch.link_group,
                    "sidechain_source": ch.sidechain_source,
                    "sends": [
                        {
                            "id": s.id, "name": s.name,
                            "target_bus": s.target_bus,
                            "amount": s.amount,
                            "pre_fader": s.pre_fader,
                        }
                        for s in ch.sends
                    ],
                }
                for ch_id, ch in self._channels.items()
            },
            "buses": {
                bus_id: {"id": bus.id, "name": bus.name, "volume": bus.volume, "channels": bus.channels}
                for bus_id, bus in self._buses.items()
            },
            "routing_matrix": {ch_id: routes for ch_id, routes in self._routing_matrix.items()},
            "master": {"volume": self._master.volume},
            "sample_rate": self._sample_rate,
            "buffer_size": self._buffer_size,
        }

    @classmethod
    def from_dict(cls, data: dict, sample_rate: int = 44100) -> "MixerEngine":
        mixer = cls(
            sample_rate=data.get("sample_rate", sample_rate),
            buffer_size=data.get("buffer_size", 512),
        )

        for ch_data in data.get("channels", {}).values():
            mixer.add_channel(ch_data["id"], ch_data["name"])
            ch = mixer.get_channel(ch_data["id"])
            if ch:
                ch.volume = ch_data.get("volume", 0.8)
                ch.pan = ch_data.get("pan", 0.0)
                ch.mute = ch_data.get("mute", False)
                ch.solo = ch_data.get("solo", False)
                ch.solo_safe = ch_data.get("solo_safe", False)
                ch.mute_group = ch_data.get("mute_group")
                ch.link_group = ch_data.get("link_group")
                ch.sidechain_source = ch_data.get("sidechain_source")

                for send_data in ch_data.get("sends", []):
                    mixer.add_send(
                        ch.id, send_data["id"], send_data["name"],
                        send_data["target_bus"],
                        send_data.get("amount", 0.0),
                        send_data.get("pre_fader", False),
                    )

        for bus_data in data.get("buses", {}).values():
            mixer.add_bus(bus_data["id"], bus_data["name"])
            bus = mixer.get_bus(bus_data["id"])
            if bus:
                bus.volume = bus_data.get("volume", 1.0)
                bus.channels = bus_data.get("channels", [])

        for ch_id, routes in data.get("routing_matrix", {}).items():
            for bus_id in routes:
                mixer.route_channel_to_bus(ch_id, bus_id)

        master_data = data.get("master", {})
        mixer._master.volume = master_data.get("volume", 1.0)

        mixer._update_solo_state()

        return mixer
