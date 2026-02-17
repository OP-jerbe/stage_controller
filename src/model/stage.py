from threading import Lock
from typing import Any, Literal, Optional

import serial


class Stage:
    MOTOR_POSITION_RANGE = (-2.147e9, 2.147e9)
    CONTROLLER_MAX_CURRENT_RATING = 2.0  # AMPS
    VALID_SET_POINTS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
    VALID_ADDRESSES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'D', 'E', 'F'}
    VALID_BAUD_RATES = {9600, 19200, 38400, 57600, 115200}
    VALID_QUADRATURE_COUNTS = {
        192,
        276,
        400,
        500,
        768,
        800,
        1000,
        1024,
        1536,
        1600,
        2000,
        2048,
        3200,
        4000,
        4096,
        8192,
    }

    def __init__(
        self,
        com_port: Optional[str] = None,
        motor_max_current: float = 0.62,
        low_current_range: bool = True,
    ) -> None:
        self._lock = Lock()
        self._term_char = '\r'
        self.com_port = com_port
        self.serial_port: Optional[serial.Serial] = None
        self.motor_max_current = motor_max_current  # AMPS
        self.low_current_range = low_current_range

        if low_current_range:
            self.CONTROLLER_MAX_CURRENT_RATING = 1.0

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
            raise TypeError(
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
            raise TypeError(
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
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.MOTOR_POSITION_RANGE[0] <= position <= self.MOTOR_POSITION_RANGE[1]:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.MOTOR_POSITION_RANGE[0]} and {self.MOTOR_POSITION_RANGE[1]}.'
            )
        command = f':{motor}c{position}'
        self._send_command(command)

    def goToSetPoint(self, motor: Literal[1, 2], set_point: int) -> None:
        """Go to a predetermined set point position"""

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise TypeError(
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
            raise TypeError(
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
            raise TypeError(
                f'Expected int for steps arg but got {type(steps).__name__}.'
            )

        command = f':{motor}j{steps}'
        self._send_command(command)

    def setOutput2(self, motor: Literal[1, 2], value: Literal[1, 2]) -> None:
        """Set the output2 state. value=1=On. value=2=Off"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
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
            raise TypeError(
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
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.MOTOR_POSITION_RANGE[0] <= position <= self.MOTOR_POSITION_RANGE[1]:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.MOTOR_POSITION_RANGE[0]} and {self.MOTOR_POSITION_RANGE[1]}.'
            )

        command = f':{motor}p{position}'
        self._send_command(command)

    def setSpeed(self, motor: Literal[1, 2], value: int) -> None:
        """Set the speed in steps/sec"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid speed setting: {value}. Speed setting must be between 0 and 65535.'
            )

        command = f':{motor}s{value}'
        self._send_command(command)

    def setVelocity(self, motor: Literal[1, 2], value: int) -> None:
        """Set the max velocity in steps/sec"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid velocity setting: {value}. Velocity setting must be between 0 and 65535.'
            )

        command = f':{motor}v{value}'
        self._send_command(command)

    def goToAbsPos(self, motor: Literal[1, 2], position: float) -> None:
        """Go to absolute position 0-360.0 in degrees"""

        self._check_motor_input(motor)
        if not isinstance(position, (int, float)):
            raise TypeError(f'Expected int or float but got {type(position).__name__}.')
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
            raise TypeError(
                f'Expected int for set_point arg but got {type(set_point).__name__}.'
            )
        if set_point not in self.VALID_SET_POINTS:
            raise ValueError(
                f'Invalid set point selection. Valid set points are {sorted(list(self.VALID_SET_POINTS))}.'
            )
        if not isinstance(position, int):
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not self.MOTOR_POSITION_RANGE[0] <= position <= self.MOTOR_POSITION_RANGE[1]:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {self.MOTOR_POSITION_RANGE[0]} and {self.MOTOR_POSITION_RANGE[1]}.'
            )

        command = f':{motor}{set_point}{position}'
        self._send_command(command)

    def setNVAccel(self, motor: Literal[1, 2], value: int) -> None:
        """Set the non-volitile acceleration in steps/sec-sq"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid accleration setting: {value}. Acceleration setting must be between 0 and 65535.'
            )

        command = f':{motor}A{value}'
        self._send_command(command)

    def setBaud(self, motor: Literal[1, 2], baud: int) -> None:
        """
        Set the baud rate for serial communication.

        Args:
            Motor (int): the motor to command (x-axis=1, y-axis=2)
            baud (int): baud rate (9600, 19200, 38400, 57600, 115200)
        """

        self._check_motor_input(motor)
        if not isinstance(baud, int):
            raise TypeError(f'Expected int for baud arg but got {type(baud).__name__}.')
        match baud:
            case 9600:
                value = 1
            case 19200:
                value = 2
            case 38400:
                value = 3
            case 57600:
                value = 4
            case 115200:
                value = 5
            case _:
                raise ValueError(
                    f'Invalid baud setting: {baud}. Valid baud settings: {sorted(list(self.VALID_BAUD_RATES))}'
                )

        command = f':{motor}B{value}'
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
            raise TypeError(
                f'Expected int or str for value arg but got {type(value).__name__}.'
            )
        if value not in self.VALID_ADDRESSES:
            raise ValueError(
                f'Invalid address value: {value}. Valid address values are {list(self.VALID_ADDRESSES)}'
            )

        command = f':{motor}D{value}'
        self._send_command(command)

    def setEncoderCPR(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the encoder quadrature counts (PPR x 4).
        Default factory setting is 8192 (2048 PPR * 4).
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in self.VALID_QUADRATURE_COUNTS:
            raise ValueError(
                f"Invalid CPR '{value}'. Must be a quadrature total (PPR * 4) "
                f'supported by the datasheet. Supported: {sorted(list(self.VALID_QUADRATURE_COUNTS))}'
            )

        command = f':{motor}E{value}'
        self._send_command(command)

    def setZero(self, motor: Literal[1, 2]) -> None:
        """Sets the motor's zero position"""
        self._check_motor_input(motor)
        command = f':{motor}F'
        self._send_command(command)

    def setHoldingCurr(self, motor: Literal[1, 2], amps: float) -> None:
        """
        Set the holding current in Amperes.
        The hardware uses a 0-31 scale where 31 = 1.0A for low current scale (default)
        or 31 = 2.0A for high current scale.
        """

        self._check_motor_input(motor)
        if not isinstance(amps, (int, float)):
            raise TypeError(
                f'Expected int or float for amps but got {type(amps).__name__}.'
            )
        if amps < 0:
            raise ValueError(f'Current cannot be negative (got {amps}A).')
        if amps > self.motor_max_current:
            raise ValueError(
                f'Current {amps}A exceeds safe limit for this motor ({self.motor_max_current}A). '
                f'Higher current may cause overheating or winding damage.'
            )

        hw_max_value = 31
        amps_per_step = self.CONTROLLER_MAX_CURRENT_RATING / hw_max_value  # 1 / 31
        motor_max_value = int(self.motor_max_current / amps_per_step)  # 19

        value = round(amps / amps_per_step)

        # Final hardware clamp just in case of rounding edge-cases
        value = max(0, min(value, motor_max_value, hw_max_value))

        command = f':{motor}H{value}'
        self._send_command(command)

    def setInitLoadError(self, motor: Literal[1, 2], value: int) -> None:
        """Set the allowable error before hard stop is detected when homing the motor."""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 1 <= value <= 65535:
            raise ValueError(
                f'Invalid value for Initializing Load Error: {value}. Valid values are 1-65535.'
            )

        command = f':{motor}I{value}'
        self._send_command(command)

    def setOut1Config(self, motor: Literal[1, 2], value: Literal[0, 1, 2, 3]) -> None:
        """
        Set Output 1 Configuration mode.

        Args:
            motor (int): The motor to command
            value (int): 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped
        """

        self._check_motor_input(motor)
        if value not in {0, 1, 2, 3}:
            raise ValueError(
                'Invalid configuration mode. Valid modes are 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped'
            )

        command = f':{motor}J{value}'
        self._send_command(command)

    def setOut2Config(self, motor: Literal[1, 2], value: Literal[0, 1, 2, 3]) -> None:
        """
        Set Output 2 Configuration mode.

        Args:
            motor (int): The motor to command
            value (int): 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped
        """

        self._check_motor_input(motor)
        if value not in {0, 1, 2, 3}:
            raise ValueError(
                'Invalid configuration mode. Valid modes are 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped'
            )

        command = f':{motor}K{value}'
        self._send_command(command)

    def setLoadError(self, motor: Literal[1, 2], value: int) -> None:
        """Set the allowable following error before faulting"""

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}L{value}'
        self._send_command(command)

    def setMstepsPerStep(self, motor: Literal[1, 2], microsteps: int) -> None:
        """Set the number of microsteps per step"""

        self._check_motor_input(motor)
        if not isinstance(microsteps, int):
            raise TypeError(
                f'Expected int for microsteps arg but got {type(microsteps).__name__}'
            )
        if not 2 <= microsteps < 256:
            raise ValueError(
                f'Invalid value for microsteps arg: {microsteps}. Valid microsteps value is 2-256'
            )

        command = f':{motor}M{microsteps}'
        self._send_command(command)

    def setCurrentRange(self, motor: Literal[1, 2], value: Literal[0, 1]) -> None:
        """
        Set the current range to high (2.0 A) or low (1.0 A)

        Args:
            motor (int): the motor to command
            value (int): 0=high=2.0A, 1=low=1.0A
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in {0, 1}:
            raise ValueError(
                f'Invalid range value: {value}. Valid range values are 0 (high range = 2.0A) or 1 (low range = 1.0A)'
            )

        command = f':{motor}O{value}'
        self._send_command(command)
