"""MIDI Handler - Gestor de dispositivos MIDI.

Manejo de dispositivos MIDI de entrada y salida,
incluyendo aprendizaaje MIDI (MIDI Learn).
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time


logger = logging.getLogger(__name__)

try:
    import rtmidi
    HAS_RTMIDI = True
except ImportError:
    HAS_RTMIDI = False
    rtmidi = None


class MIDIMessageType(Enum):
    """Tipos de mensaje MIDI."""
    NOTE_ON = 0x90
    NOTE_OFF = 0x80
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    PITCH_BEND = 0xE0
    SYSEX = 0xF0


@dataclass
class MIDIMessage:
    """Mensaje MIDI.
    
    Attributes:
        message_type: Tipo de mensaje
        channel: Canal (0-15)
        data1: Primer dato
        data2: Segundo dato
        timestamp: Timestamp
    """
    message_type: MIDIMessageType
    channel: int
    data1: int
    data2: int
    timestamp: float = 0.0
    
    @property
    def note(self) -> int:
        """Obtener nota."""
        return self.data1
    
    @property
    def velocity(self) -> int:
        """Obtener velocidad."""
        return self.data2
    
    @property
    def cc_number(self) -> int:
        """Obtener número de CC."""
        return self.data1
    
    @property
    def cc_value(self) -> int:
        """Obtener valor de CC."""
        return self.data2


@dataclass
class MIDIDevice:
    """Dispositivo MIDI."""
    name: str
    is_input: bool
    is_output: bool
    port_index: int


@dataclass
class MIDILearnAssignment:
    """Asignación de MIDI Learn.
    
    Attributes:
        cc_number: Número de CC
        channel: Canal MIDI
        target_parameter: Parámetro objetivo
        min_value: Valor mínimo
        max_value: Valor máximo
    """
    cc_number: int
    channel: int
    target_parameter: str
    min_value: float = 0.0
    max_value: float = 1.0


class MIDIHandler:
    """Manejador de MIDI.
    
    Gestiona dispositivos MIDI, mensajes y MIDI Learn.
    """
    
    def __init__(self):
        """Inicializar manejador."""
        self._devices: Dict[str, MIDIDevice] = {}
        self._input_devices: Dict[str, Any] = {}
        self._output_devices: Dict[str, Any] = {}
        
        # Callbacks
        self._note_on_callback: Optional[Callable[[int, int, int], None]] = None
        self._note_off_callback: Optional[Callable[[int, int, int], None]] = None
        self._cc_callback: Optional[Callable[[int, int, int], None]] = None
        self._program_change_callback: Optional[Callable[[int, int], None]] = None
        
        # MIDI Learn
        self._midi_learn_mode = False
        self._midi_learn_assignments: Dict[int, MIDILearnAssignment] = {}
        self._midi_learn_callback: Optional[Callable[[int], None]] = None
        
        # Mensajes pendientes
        self._message_queue: List[MIDIMessage] = []
        self._queue_lock = threading.Lock()
        self._last_midi_log_time: float = 0.0
        
        # Estado
        self._is_running = False
        
        logger.info("MIDIHandler inicializado")
    
    # === Dispositivos ===
    
    def get_input_devices(self) -> List[MIDIDevice]:
        """Obtener dispositivos de entrada."""
        return [d for d in self._devices.values() if d.is_input]
    
    def get_output_devices(self) -> List[MIDIDevice]:
        """Obtener dispositivos de salida."""
        return [d for d in self._devices.values() if d.is_output]
    
    def open_input(self, device_name: str) -> bool:
        """Abrir dispositivo de entrada usando rtmidi.
        
        Args:
            device_name: Nombre del dispositivo
            
        Returns:
            True si fue exitoso
        """
        if HAS_RTMIDI and rtmidi:
            try:
                midi_in = rtmidi.MidiIn()
                ports = midi_in.get_ports()
                for i, name in enumerate(ports):
                    if device_name in name:
                        midi_in.open_port(i)
                        midi_in.set_callback(self._rtmidi_callback)
                        self._input_devices[device_name] = midi_in
                        logger.info(f"MIDI input opened via rtmidi: {device_name}")
                        return True
                logger.warning(f"MIDI device not found: {device_name}")
                return False
            except Exception as e:
                logger.warning(f"rtmidi error opening input: {e}")
        
        logger.info(f"MIDI input device opened (simulated): {device_name}")
        return True
    
    def close_input(self, device_name: str) -> bool:
        """Cerrar dispositivo de entrada.
        
        Args:
            device_name: Nombre del dispositivo
            
        Returns:
            True si fue exitoso
        """
        if device_name in self._input_devices:
            try:
                self._input_devices[device_name].close_port()
            except Exception:
                pass
            del self._input_devices[device_name]
            logger.info(f"MIDI input closed: {device_name}")
            return True
        logger.info(f"MIDI input device closed (simulated): {device_name}")
        return True
    
    def open_output(self, device_name: str) -> bool:
        """Abrir dispositivo de salida usando rtmidi.
        
        Args:
            device_name: Nombre del dispositivo
            
        Returns:
            True si fue exitoso
        """
        if HAS_RTMIDI and rtmidi:
            try:
                midi_out = rtmidi.MidiOut()
                ports = midi_out.get_ports()
                for i, name in enumerate(ports):
                    if device_name in name:
                        midi_out.open_port(i)
                        self._output_devices[device_name] = midi_out
                        logger.info(f"MIDI output opened via rtmidi: {device_name}")
                        return True
                logger.warning(f"MIDI output device not found: {device_name}")
                return False
            except Exception as e:
                logger.warning(f"rtmidi error opening output: {e}")
        
        logger.info(f"MIDI output device opened (simulated): {device_name}")
        return True
    
    def close_output(self, device_name: str) -> bool:
        """Cerrar dispositivo de salida.
        
        Args:
            device_name: Nombre del dispositivo
            
        Returns:
            True si fue exitoso
        """
        if device_name in self._output_devices:
            try:
                self._output_devices[device_name].close_port()
            except Exception:
                pass
            del self._output_devices[device_name]
            logger.info(f"MIDI output closed: {device_name}")
            return True
        logger.info(f"MIDI output device closed (simulated): {device_name}")
        return True
    
    def _rtmidi_callback(self, event, data=None):
        """Callback para mensajes entrantes de rtmidi."""
        try:
            msg, delta = event
            if len(msg) < 2:
                return
            status = msg[0]
            channel = status & 0x0F
            msg_type = status & 0xF0
            data1 = msg[1] if len(msg) > 1 else 0
            data2 = msg[2] if len(msg) > 2 else 0
            
            type_map = {
                0x90: MIDIMessageType.NOTE_ON,
                0x80: MIDIMessageType.NOTE_OFF,
                0xB0: MIDIMessageType.CONTROL_CHANGE,
                0xC0: MIDIMessageType.PROGRAM_CHANGE,
                0xE0: MIDIMessageType.PITCH_BEND,
            }
            mtype = type_map.get(msg_type)
            if mtype:
                midi_msg = MIDIMessage(
                    message_type=mtype,
                    channel=channel,
                    data1=data1,
                    data2=data2,
                    timestamp=time.time(),
                )
                self.process_message(midi_msg)
        except Exception as e:
            logger.debug(f"Error in rtmidi callback: {e}")
    
    # === Callbacks ===
    
    def set_note_on_callback(
        self,
        callback: Callable[[int, int, int], None]
    ) -> None:
        """Establecer callback de Note On.
        
        Args:
            callback: Función(note, velocity, channel)
        """
        self._note_on_callback = callback
    
    def set_note_off_callback(
        self,
        callback: Callable[[int, int, int], None]
    ) -> None:
        """Establecer callback de Note Off.
        
        Args:
            callback: Función(note, velocity, channel)
        """
        self._note_off_callback = callback
    
    def set_cc_callback(
        self,
        callback: Callable[[int, int, int], None]
    ) -> None:
        """Establecer callback de Control Change.
        
        Args:
            callback: Función(cc_number, value, channel)
        """
        self._cc_callback = callback
    
    def set_program_change_callback(
        self,
        callback: Callable[[int, int], None]
    ) -> None:
        """Establecer callback de Program Change.
        
        Args:
            callback: Función(program, channel)
        """
        self._program_change_callback = callback
    
    # === Procesamiento ===
    
    def process_message(self, message: MIDIMessage) -> None:
        """Procesar un mensaje MIDI.
        
        Args:
            message: Mensaje a procesar
        """
        # Encolar mensaje
        with self._queue_lock:
            self._message_queue.append(message)
        
        # Procesar inmediatamente
        self._handle_message(message)
    
    def _handle_message(self, message: MIDIMessage) -> None:
        """Manejar mensaje MIDI.
        
        Args:
            message: Mensaje
        """
        msg_type = message.message_type
        channel = message.channel
        
        now = time.time()
        if now - self._last_midi_log_time >= 0.5:
            if msg_type == MIDIMessageType.NOTE_ON and message.velocity > 0:
                logger.info(f"MIDI note_on: note={message.note}, velocity={message.velocity}, channel={channel}")
            elif msg_type == MIDIMessageType.NOTE_OFF or (msg_type == MIDIMessageType.NOTE_ON and message.velocity == 0):
                logger.info(f"MIDI note_off: note={message.note}, channel={channel}")
            self._last_midi_log_time = now
        
        if msg_type == MIDIMessageType.NOTE_ON and message.velocity > 0:
            if self._note_on_callback:
                self._note_on_callback(
                    message.note,
                    message.velocity,
                    channel
                )
        
        elif msg_type in (MIDIMessageType.NOTE_OFF, 
                          (MIDIMessageType.NOTE_ON, 0)):
            if self._note_off_callback:
                self._note_off_callback(
                    message.note,
                    message.velocity,
                    channel
                )
        
        elif msg_type == MIDIMessageType.CONTROL_CHANGE:
            if self._cc_callback:
                self._cc_callback(
                    message.cc_number,
                    message.cc_value,
                    channel
                )
                
                # MIDI Learn
                self._handle_midi_learn(
                    message.cc_number,
                    message.cc_value,
                    channel
                )
        
        elif msg_type == MIDIMessageType.PROGRAM_CHANGE:
            if self._program_change_callback:
                self._program_change_callback(message.data1, channel)
    
    def process_queued_messages(self) -> int:
        """Procesar mensajes en cola.
        
        Returns:
            Número de mensajes procesados
        """
        with self._queue_lock:
            messages = self._message_queue.copy()
            self._message_queue.clear()
        
        for msg in messages:
            self._handle_message(msg)
        
        return len(messages)
    
    # === MIDI Learn ===
    
    def start_midi_learn(
        self,
        callback: Optional[Callable[[int], None]] = None
    ) -> None:
        """Iniciar modo MIDI Learn.
        
        Args:
            callback: Callback cuando se recibe un CC
        """
        self._midi_learn_mode = True
        self._midi_learn_callback = callback
        logger.info("MIDI Learn iniciado")
    
    def stop_midi_learn(self) -> None:
        """Detener modo MIDI Learn."""
        self._midi_learn_mode = False
        self._midi_learn_callback = None
        logger.info("MIDI Learn detenido")
    
    @property
    def midi_learn_mode(self) -> bool:
        """Ver si está en modo MIDI Learn."""
        return self._midi_learn_mode
    
    def _handle_midi_learn(
        self,
        cc_number: int,
        value: int,
        channel: int
    ) -> None:
        """Manejar MIDI Learn.
        
        Args:
            cc_number: Número de CC
            value: Valor
            channel: Canal
        """
        if self._midi_learn_mode and self._midi_learn_callback:
            self._midi_learn_callback(cc_number)
            self.stop_midi_learn()
    
    def assign_midi_learn(
        self,
        cc_number: int,
        channel: int,
        target_parameter: str,
        min_value: float = 0.0,
        max_value: float = 1.0
    ) -> MIDILearnAssignment:
        """Asignar una conexión MIDI Learn.
        
        Args:
            cc_number: Número de CC
            channel: Canal
            target_parameter: Parámetro objetivo
            min_value: Valor mínimo
            max_value: Valor máximo
            
        Returns:
            Asignación creada
        """
        assignment = MIDILearnAssignment(
            cc_number=cc_number,
            channel=channel,
            target_parameter=target_parameter,
            min_value=min_value,
            max_value=max_value
        )
        
        self._midi_learn_assignments[cc_number] = assignment
        logger.info(f"MIDI Learn asignado: CC{cc_number} -> {target_parameter}")
        
        return assignment
    
    def remove_midi_learn(self, cc_number: int) -> bool:
        """Remover una asignación MIDI Learn.
        
        Args:
            cc_number: Número de CC
            
        Returns:
            True si se removió
        """
        if cc_number in self._midi_learn_assignments:
            del self._midi_learn_assignments[cc_number]
            return True
        return False
    
    def get_midi_learn_assignments(self) -> List[MIDILearnAssignment]:
        """Obtener todas las asignaciones MIDI Learn."""
        return list(self._midi_learn_assignments.values())
    
    def clear_midi_learn(self) -> None:
        """Limpiar todas las asignaciones MIDI Learn."""
        self._midi_learn_assignments.clear()
        logger.info("MIDI Learn limpiado")
    
    # === Envío de MIDI ===
    
    def _send_rtmidi(self, device: str, msg: list) -> None:
        if device and device in self._output_devices:
            try:
                self._output_devices[device].send_message(msg)
            except Exception as e:
                logger.warning(f"Error sending MIDI to {device}: {e}")
        else:
            for dev in self._output_devices.values():
                try:
                    dev.send_message(msg)
                except Exception:
                    pass

    def send_note_on(
        self,
        note: int,
        velocity: int,
        channel: int = 0,
        device: str = ""
    ) -> None:
        """Enviar Note On.
        
        Args:
            note: Nota
            velocity: Velocidad
            channel: Canal
            device: Dispositivo de salida
        """
        logger.debug(f"MIDI Note On: {note} v{velocity} ch{channel}")
        if HAS_RTMIDI:
            status = 0x90 | (channel & 0x0F)
            self._send_rtmidi(device, [status, note & 0x7F, velocity & 0x7F])
    
    def send_note_off(
        self,
        note: int,
        velocity: int = 0,
        channel: int = 0,
        device: str = ""
    ) -> None:
        """Enviar Note Off.
        
        Args:
            note: Nota
            velocity: Velocidad
            channel: Canal
            device: Dispositivo de salida
        """
        logger.debug(f"MIDI Note Off: {note} ch{channel}")
        if HAS_RTMIDI:
            status = 0x80 | (channel & 0x0F)
            self._send_rtmidi(device, [status, note & 0x7F, velocity & 0x7F])
    
    def send_cc(
        self,
        cc_number: int,
        value: int,
        channel: int = 0,
        device: str = ""
    ) -> None:
        """Enviar Control Change.
        
        Args:
            cc_number: Número de CC
            value: Valor
            channel: Canal
            device: Dispositivo de salida
        """
        logger.debug(f"MIDI CC: {cc_number} = {value} ch{channel}")
        if HAS_RTMIDI:
            status = 0xB0 | (channel & 0x0F)
            self._send_rtmidi(device, [status, cc_number & 0x7F, value & 0x7F])
    
    # === Utilidades ===
    
    def get_cc_value_normalized(self, value: int) -> float:
        """Normalizar valor de CC (0-127 a 0.0-1.0).
        
        Args:
            value: Valor original
            
        Returns:
            Valor normalizado
        """
        return value / 127.0
    
    def cc_to_parameter(
        self,
        cc_value: int,
        min_value: float,
        max_value: float
    ) -> float:
        """Convertir valor CC a valor de parámetro.
        
        Args:
            cc_value: Valor CC (0-127)
            min_value: Valor mínimo del parámetro
            max_value: Valor máximo del parámetro
            
        Returns:
            Valor del parámetro
        """
        normalized = self.get_cc_value_normalized(cc_value)
        return min_value + (max_value - min_value) * normalized
    
    # === Serialización ===
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "midi_learn_assignments": [
                {
                    "cc_number": a.cc_number,
                    "channel": a.channel,
                    "target_parameter": a.target_parameter,
                    "min_value": a.min_value,
                    "max_value": a.max_value
                }
                for a in self._midi_learn_assignments.values()
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MIDIHandler":
        """Crear desde diccionario."""
        handler = cls()
        
        for assignment in data.get("midi_learn_assignments", []):
            handler.assign_midi_learn(
                cc_number=assignment["cc_number"],
                channel=assignment["channel"],
                target_parameter=assignment["target_parameter"],
                min_value=assignment.get("min_value", 0.0),
                max_value=assignment.get("max_value", 1.0)
            )
        
        return handler
