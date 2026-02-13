import serial

from src.helpers.helpers import load_ini


class Stage:
    def __init__(self) -> None:
        self.comport = self._get_comport()

    @staticmethod
    def _get_comport() -> str:
        config_data = load_ini()
        return config_data.get('COMPORT', 'port')

    def connect(self, port) -> None:
        serial.Serial(port)
