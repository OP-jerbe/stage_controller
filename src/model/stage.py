from threading import Lock
from typing import Optional

import serial


class Stage:
    def __init__(self, com_port: Optional[str] = None) -> None:
        self._lock = Lock()
        self._term_char = '\r'
        self.com_port = com_port
        self.serial_port: Optional[serial.Serial] = None

        if self.com_port:
            self.open_connection(self.com_port)

    def open_connection(
        self, port: str, baudrate: int = 9600, timeout: float = 1.0
    ) -> None:
        """
        Establishes a serial connection to the instrument at the specified COM port.

        Args:
            port (str): The COM port where the stage is connected (e.g., 'COM3' or '/dev/ttyUSB0').
                The port name is automatically converted to uppercase.
            baudrate (int): The serial communication baud rate in bits per second. Defaults to 9600.
            timeout (float): The read and write timeout in seconds. Defaults to 1.0.
        """
        try:
            self.serial_port = serial.Serial(
                port=port.upper(),
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )

        except Exception as e:
            print(f'Failed to make a serial connection to {port}.\n\n{str(e)}')
            self.serial_port = None

    def _send_command(self, command: str) -> None:
        """
        Sends a command string to the stage without expecting a response.

        Args:
            command (str): The command string to send to the instrument.
                The carriage return termination character is appended automatically.
        """
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with stage, but no instrument is connected.'
            )

        if not command.endswith(self._term_char):
            command += self._term_char

        with self._lock:
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception as e:
                raise ConnectionError(f'Serial Communication Error\n\n{str(e)}')

        print(f'Command: "{command.strip()}"')

    def _send_query(self, query: str) -> str:
        """
        Sends a query command to the stage, reads the response, and handles unsolicited output.

        Args:
            query (str): The query command string to send.
                The carriage return termination character is appended automatically.

        Returns:
            str: The decoded and stripped string response received from the instrument.
        """
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError(
                'Attempted to communicate with stage, but no instrument is connected.'
            )
        if not query.endswith(self._term_char):
            query += self._term_char

        with self._lock:
            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.write(query.encode('utf-8'))
                response = self._readline()
            except Exception as e:
                print(f'Unexpected Error sending query: {e}')
                raise

        return response

    def _readline(self) -> str:
        """
        Reads data from the serial port until the termination character is found.

        Returns:
            str: The decoded and stripped line of response data.
        """
        if not self.serial_port:
            raise RuntimeError('No serial port connection.')

        return (
            self.serial_port.read_until(self._term_char.encode('utf-8'))
            .decode('utf-8')
            .strip()
        )


class Motor1(Stage):
    def __init__(self, com_port: Optional[str] = None) -> None:
        super().__init__(com_port)


class Motor2(Stage):
    def __init__(self, com_port: Optional[str] = None) -> None:
        super().__init__(com_port)
