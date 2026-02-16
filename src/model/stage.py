from threading import Lock
from typing import Any, Literal, Optional

import serial


class Stage:
    def __init__(self, com_port: Optional[str] = None) -> None:
        self._lock = Lock()
        self._term_char = '\r'
        self.com_port = com_port
        self.serial_port: Optional[serial.Serial] = None
        self.max_motor_pos = 2.147e9
        self.min_motor_pos = -2.147e9

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

    @staticmethod
    def _check_motor_input(value: Any) -> None:
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for motor arg but got {type(value).__name__}.'
            )
        if value not in (1, 2):
            raise ValueError(
                f'Invalid motor selection: {value}. Motor selection must be 1 or 2.'
            )

    ###################################################################################
    ################################# Set Commands ####################################
    ###################################################################################

    def setAccel(self, motor: Literal[1, 2], value: int) -> None:
        """Set the acceleration in steps/sec-sq"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid accleration setting: {value}. Acceleration setting must be between 0 and 65535.'
            )

        command = f':{motor}a{value}'
        self._send_command(command)

    def setHome(self, motor: Literal[1, 2], position: int) -> None:
        """Home to position"""

        self._check_motor_input(motor)
        if not isinstance(position, int):
            raise ValueError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.min_motor_pos <= position <= self.max_motor_pos:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.min_motor_pos} and {self.max_motor_pos}.'
            )
        command = f':{motor}c{position}'
        self._send_command(command)

    def goToSetPoint(self, motor: Literal[1, 2], set_point: int) -> None:
        """Go to a predetermined set point position"""

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise ValueError(
                f'Expected int for value arg but got {type(set_point).__name__}.'
            )
        if set_point not in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
            raise ValueError('Invalid set point selection. Valid set points are 0-9.')

        command = f':{motor}d{set_point}'
        self._send_command(command)

    def setHalt(self, motor: Literal[1, 2], value: Literal[1, 2]) -> None:
        """Set the halt type. value=1=Hard Stop. value=2=Soft Stop"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in (1, 2):
            raise ValueError(
                f'Invalid value selection: {motor}. Value selection must be 1 or 2.'
            )

        command = f':{motor}h{value}'
        self._send_command(command)

    def initMotor(self, motor: Literal[1, 2]) -> None:
        """Initialize a motor"""

        self._check_motor_input(motor)

        command = f':{motor}i1'
        self._send_command(command)

    def jog(self, motor: Literal[1, 2], steps: int) -> None:
        """Jog the motor a number of steps (can be negative)"""

        self._check_motor_input(motor)
        if not isinstance(steps, int):
            raise ValueError(
                f'Expected int for steps arg but got {type(steps).__name__}.'
            )

        command = f':{motor}j{steps}'
        self._send_command(command)

    def setOutput2(self, motor: Literal[1, 2], value: Literal[1, 2]) -> None:
        """Set the output2 state. value=1=On. value=2=Off"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in (1, 2):
            raise ValueError(
                f'Invalid value selection: {motor}. Value selection must be 1 or 2.'
            )

        command = f':{motor}n{value}'
        self._send_command(command)

    def setOutput1(self, motor: Literal[1, 2], value: Literal[1, 2]) -> None:
        """Set the output1 state. value=1=On. value=2=Off"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in (1, 2):
            raise ValueError(
                f'Invalid value selection: {motor}. Value selection must be 1 or 2.'
            )

        command = f':{motor}o{value}'
        self._send_command(command)

    def goToPos(self, motor: Literal[1, 2], position: int) -> None:
        """Go to a postion"""

        self._check_motor_input(motor)
        if not isinstance(position, int):
            raise ValueError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.min_motor_pos <= position <= self.max_motor_pos:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.min_motor_pos} and {self.max_motor_pos}.'
            )

        command = f':{motor}p{position}'
        self._send_command(command)

    def setSpeed(self, motor: Literal[1, 2], value: int) -> None:
        """Set the speed in steps/sec"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}s{value}'
        self._send_command(command)

    def setVelocity(self, motor: Literal[1, 2], value: int) -> None:
        """Set the max velocity in steps/sec"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}v{value}'
        self._send_command(command)

    def goToAbsPos(self, motor: Literal[1, 2], position: float) -> None:
        """Go to absolute position 0-360.0 in degrees"""

        self._check_motor_input(motor)
        if not isinstance(position, (int, float)):
            raise ValueError(
                f'Expected int or float but got {type(position).__name__}.'
            )
        if not 0 <= position <= 360.0:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between 0 and 360.0 degrees.'
            )

        command = f':{motor}x{position}'
        self._send_command(command)

    def setSetPoint(self, motor: Literal[1, 2], set_point: int, position: int) -> None:
        """Set a set point position. Valid set points are 0-9"""

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise ValueError(
                f'Expected int for set_point arg but got {type(set_point).__name__}.'
            )
        if set_point not in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
            raise ValueError('Invalid set point selection. Valid set points are 0-9.')
        if not isinstance(position, int):
            raise ValueError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.min_motor_pos <= position <= self.max_motor_pos:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.min_motor_pos} and {self.max_motor_pos}.'
            )

        command = f':{motor}{set_point}{position}'
        self._send_command(command)

    def setNVAccel(self, motor: Literal[1, 2], value: int) -> None:
        """Set the non-volitile acceleration in steps/sec-sq"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid accleration setting: {value}. Acceleration setting must be between 0 and 65535.'
            )

        command = f':{motor}A{value}'
        self._send_command(command)

    def setBaud(self, motor: Literal[1, 2], baud: Literal[1, 2, 3, 4, 5]) -> None:
        """
        Set the baud rate for serial communication.

        Args:
            Motor (int): the motor to command (x-axis=1, y-axis=2)
            baud (int): baud rate where: 1=9600, 2=19200, 3=38400, 4=57600, 5=115200
        """

        self._check_motor_input(motor)
        if not isinstance(baud, int):
            raise ValueError(
                f'Expected int for baud arg but got {type(baud).__name__}.'
            )
        if baud not in [1, 2, 3, 4, 5]:
            raise ValueError(
                f'Invalid baud setting: {baud}. Baud setting must be 1-5 where 1=9600, 2=19200, 3=38400, 4=57600, 5=115200'
            )

        command = f':{motor}B{baud}'
        self._send_command(command)

    def setDirection(self, motor: Literal[1, 2], direction: str) -> None:
        """
        Set the direction of the motor to "CW" or "CCW"

        Args:
            motor (int): the motor to command (x-axis=1, y-axis=2)
            direction (str): `CW` or `CCW` - the direction the motor will spin when commanded with a positive value.
        """

        self._check_motor_input(motor)
        match direction:
            case 'CW':
                value = 0
            case 'CCW':
                value = 1
            case _:
                raise ValueError(
                    f'Invalid direction {direction}. Valid directions are "CW" or "CCW".'
                )

        command = f':{motor}C{value}'
        self._send_command(command)

    def setAddress(self, motor: Literal[1, 2], value: int | str) -> None:
        """Set the address of a motor"""

        self._check_motor_input(motor)
        if not isinstance(value, (int, str)):
            raise ValueError(
                f'Expected int or str for value arg but got {type(value).__name__}.'
            )
        if value not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'D', 'E', 'F'):
            raise ValueError(
                f'Invalid address value: {value}. Valid address values are 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E'
            )

        command = f':{motor}D{value}'
        self._send_command(command)

    def setEncoderCPR(self, motor: Literal[1, 2], value: int) -> None:
        """Set the encoder cycles-per-revolution (or pulses-per-sec x4)"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}E{value}'
        self._send_command(command)

    def setHoldingCurr(self, motor: Literal[1, 2], value: int) -> None:
        """Set the holding current"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 31:
            raise ValueError(
                f'Invalid holding current value: {value}. Valid holding current is 0-31.'
            )

        command = f':{motor}H{value}'
        self._send_command(command)

    def setInitLoadError(self, motor: Literal[1, 2], value: int) -> None:
        """Set the allowable error before hard stop is detected"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise ValueError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}I{value}'
        self._send_command(command)
