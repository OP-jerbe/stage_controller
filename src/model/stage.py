from threading import Lock
from typing import Any, Literal, Optional

import serial


class Stage:
    MAX_MOTOR_POSITION = 2.147e9
    CONTROLLER_CURRENT_RANGE = 2.0  # AMPS
    CONTROLLER_MAX_CURRENT_VALUE = 31
    SET_POINTS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
    ADDRESSES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'D', 'E', 'F'}
    BAUD_RATES = {9600, 19200, 38400, 57600, 115200}
    QUADRATURE_COUNTS = {
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
        self.ser: Optional[serial.Serial] = None
        self.motor_max_current = motor_max_current  # AMPS
        self.controller_current_range = self.CONTROLLER_CURRENT_RANGE

        if low_current_range:
            self.controller_current_range = 1.0

        self.amps_per_step = (
            self.controller_current_range / self.CONTROLLER_MAX_CURRENT_VALUE
        )

        if self.com_port:
            self.open_connection(self.com_port)

    def open_connection(
        self, port: str, baudrate: int = 38400, timeout: float = 1.0
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
            self.ser = serial.Serial(
                port=port.upper(),
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )

        except Exception as e:
            print(f'Failed to make a serial connection to {port}.\n\n{str(e)}')
            self.ser = None

    def close_connection(self) -> None:
        """Closes an open serial port"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None

    def _send_command(self, command: str) -> None:
        """
        Sends a command string to the stage without expecting a response.

        Args:
            command (str): The command string to send to the instrument.
                The carriage return termination character is appended automatically.
        """
        if not self.ser or not self.ser.is_open:
            raise RuntimeError(
                'Attempted to communicate with stage, but no instrument is connected.'
            )

        if not command.endswith(self._term_char):
            command += self._term_char

        with self._lock:
            try:
                self.ser.write(command.encode('ascii'))
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
        if not self.ser or not self.ser.is_open:
            raise RuntimeError(
                'Attempted to communicate with stage, but no instrument is connected.'
            )
        if not query.endswith(self._term_char):
            query += self._term_char

        with self._lock:
            try:
                self.ser.reset_input_buffer()
                self.ser.write(query.encode('ascii'))
                response = self._readline()
                print(f'{response = }')
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
        if not self.ser:
            raise RuntimeError('No serial port connection.')

        return (
            self.ser.read_until(self._term_char.encode('ascii')).decode('ascii').strip()
        )

    @staticmethod
    def _check_motor_input(value: Any) -> None:
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for motor arg but got {type(value).__name__}.'
            )
        if value not in {0, 1, 2}:
            raise ValueError(
                f'Invalid motor selection: {value}. Valid motor selections are [0, 1, 2].'
            )

    ###################################################################################
    ################################# Set Commands ####################################
    ###################################################################################

    # --- Non-Volatile Settings ---

    def setNVAccel(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the non-volatile acceleration in steps/sec-sq

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the acceleration in steps/sec-sq stored in non-volatile memory
        """

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

    def setNVSpeed(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the non-volatile memory max speed in steps/sec

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the speed in steps/sec in non-volatile memory
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if not 0 <= value <= 65535:
            raise ValueError(
                f'Invalid speed setting: {value}. Speed setting must be between 0 and 65535.'
            )

        command = f':{motor}S{value}'
        self._send_command(command)

    # --- Set Points ---

    def editSetPoint(
        self,
        motor: Literal[1, 2],
        set_point: int,
        position: int,
        velocity: int,
        acceleration: int,
    ) -> None:
        """
        Create a set point profile. Valid set points are 0-9.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            set_point (int): the set point profile (0-9)
            position (int): the position the motor should travel to when the set point is executed
            velocity (int): the velocity the motor should use when set the point is executed
            acceleration (int): the acceleration the motor should use when the set point is executed
        """

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise TypeError(
                f'Expected int for set_point arg but got {type(set_point).__name__}.'
            )
        if set_point not in self.SET_POINTS:
            raise ValueError(
                f'Invalid set point selection. Valid set points are {sorted(list(self.SET_POINTS))}.'
            )
        if not isinstance(position, int):
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not -self.MAX_MOTOR_POSITION <= position <= self.MAX_MOTOR_POSITION:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {-self.MAX_MOTOR_POSITION} and {self.MAX_MOTOR_POSITION}.'
            )
        if not isinstance(velocity, int):
            raise TypeError(
                f'Expected int for velocity but got {type(velocity).__name__}.'
            )
        if not 0 <= velocity <= 65535:
            raise ValueError(
                f'Invalid velocity setting: {velocity}. Valid velocity range is 0-65535'
            )
        if not isinstance(acceleration, int):
            raise TypeError(
                f'Expected int for acceleration but got {type(acceleration).__name__}.'
            )
        if not 0 <= acceleration <= 65535:
            raise ValueError(
                f'Invalid acceleration setting: {acceleration}. Valid acceleration range is 0-65535'
            )

        command = f':{motor}{set_point}{position},{velocity},{acceleration}'
        self._send_command(command)

    def gotoSetPoint(self, motor: Literal[0, 1, 2], set_point: int) -> None:
        """
        Go to a predetermined set point position

        Args:
            motor (int): the motor to command (0=both, 1=x-axis, 2=y-axis)
        """

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise TypeError(
                f'Expected int for value arg but got {type(set_point).__name__}.'
            )
        if set_point not in self.SET_POINTS:
            raise ValueError(
                f'Invalid set point selection. Valid set points are {sorted(list(self.SET_POINTS))}.'
            )

        command = f':{motor}d{set_point}'
        self._send_command(command)

    # --- Movement Settings ---

    def halt(self, motor: Literal[0, 1, 2] = 0, value: Literal[1, 2] = 1) -> None:
        """
        Tell the motor to stop moving.

        Args:
            motor (int): the motor to command where:
                0=both (default)
                1=x-axis
                2=y-axis
            value (int): stop type where:
                1=Hard Stop (default)
                2=Soft Stop
        """

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

    def setMSteps(self, motor: Literal[1, 2], microsteps: int) -> None:
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

    def setDirection(self, motor: Literal[1, 2], direction: str) -> None:
        """
        Set the direction of the motor to "CW" or "CCW"

        Args:
            motor (int): the motor to command (x-axis=1, y-axis=2)
            direction (str): `"CW"` or `"CCW"` - the direction the motor will spin when homed.
        """

        self._check_motor_input(motor)
        match direction.upper():
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

    def setAccel(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the acceleration in steps/sec-sq

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the acceleration setting in steps/sec-sq
        """

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

    def setSpeed(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the speed in steps/sec

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the speed setting (0-65535)
        """

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
        """
        Set the max velocity in steps/sec

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the velocity setting in steps/sec (0-65535)
        """

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

    def setLoadError(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the allowable following error before faulting

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the load error setting in steps
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )

        command = f':{motor}L{value}'
        self._send_command(command)

    # --- Positioning ---

    def jog(self, motor: Literal[1, 2], steps: int) -> None:
        """
        Jog the motor a number of steps (can be negative)

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            steps (int): the number of steps to jog
        """

        self._check_motor_input(motor)
        if not isinstance(steps, int):
            raise TypeError(
                f'Expected int for steps arg but got {type(steps).__name__}.'
            )

        command = f':{motor}j{steps}'
        self._send_command(command)

    def gotoPos(self, motor: Literal[1, 2], position: int) -> None:
        """
        Go to a postion

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            position (int): the step to travel to
        """

        self._check_motor_input(motor)
        if not isinstance(position, int):
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not -self.MAX_MOTOR_POSITION <= position <= self.MAX_MOTOR_POSITION:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {-self.MAX_MOTOR_POSITION} and {self.MAX_MOTOR_POSITION}.'
            )

        command = f':{motor}p{position}'
        self._send_command(command)

    def gotoAbsPos(self, motor: Literal[1, 2], position: float) -> None:
        """
        Go to absolute position 0-360.0 in degrees

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            position (float): the position the motor should go to in degrees (0-360.0)
        """

        self._check_motor_input(motor)
        if not isinstance(position, (int, float)):
            raise TypeError(f'Expected int or float but got {type(position).__name__}.')
        if not 0 <= position <= 360.0:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between 0 and 360.0 degrees.'
            )

        command = f':{motor}x{position}'
        self._send_command(command)

    def setZero(self, motor: Literal[1, 2]) -> None:
        """
        Sets the motor's zero position

        Args:
            motor: the motor to command (1=x-axis, 2=y-axis)
        """
        self._check_motor_input(motor)
        command = f':{motor}F'
        self._send_command(command)

    # --- Phase Current Settings ---

    def setCurrRange(self, motor: Literal[1, 2], value: Literal[0, 1]) -> None:
        """
        Set the current range to high (2.0 A) or low (1.0 A)

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the current range where 0=high=2.0A, 1=low=1.0A
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
        if value == 0:
            self.controller_current_range = 2.0
        else:
            self.controller_current_range = 1.0

    def setHoldingCurr(self, motor: Literal[1, 2], amps: float) -> None:
        """
        Set the holding current in Amperes.
        The hardware uses a 0-31 scale where 31 = 1.0A for low current scale (default)
        or 31 = 2.0A for high current scale.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            amps (float): the holding current in amps when the motor is not in motion
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

        motor_max_value = int(self.motor_max_current / self.amps_per_step)  # 19

        value = round(amps / self.amps_per_step)

        # Final hardware clamp just in case of rounding edge-cases
        value = max(0, min(value, motor_max_value, self.CONTROLLER_MAX_CURRENT_VALUE))

        command = f':{motor}H{value}'
        self._send_command(command)

    def setRunCurr(self, motor: Literal[1, 2], amps: float) -> None:
        """
        Set the run current in Amperes.
        The hardware uses a 0-31 scale where 31 = 1.0A for low current scale (default)
        or 31 = 2.0A for high current scale.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            amps (float): the max current setting in amperes for when the motor is running
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

        motor_max_value = int(self.motor_max_current / self.amps_per_step)  # 19

        value = round(amps / self.amps_per_step)

        # Final hardware clamp just in case of rounding edge-cases
        value = max(0, min(value, motor_max_value, self.CONTROLLER_MAX_CURRENT_VALUE))

        command = f':{motor}R{value}'
        self._send_command(command)

    # --- Initialization ---

    def initMotor(self, motor: Literal[0, 1, 2]) -> None:
        """
        Initialize a motor

        Args:
            motor (int): the motor to command (0=both, 1=x-axis, 2=y-axis)
        """

        self._check_motor_input(motor)

        command = f':{motor}i1'
        self._send_command(command)

    def setOutput(
        self, motor: Literal[1, 2], output: Literal[1, 2], state: Literal[0, 1]
    ) -> None:
        """
        Force an output state On or Off.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            output (int): the output to set (1 or 2)
            state (int): the state of the output (0=Low or 1=High)
        """

        self._check_motor_input(motor)
        if not isinstance(output, int):
            raise TypeError(
                f'Expected int for output arg but got {type(output).__name__}.'
            )
        if output not in {1, 2}:
            raise ValueError(
                f'Invalid output selection: {output}. Value selection must be 1 or 2.'
            )
        if not isinstance(state, int):
            raise TypeError(
                f'Expected int for state arg but got {type(state).__name__}.'
            )
        if state not in {0, 1}:
            raise ValueError(f'Invalid state: {state}. Valid states are 0=Off or 1=On')

        output_map = {1: 'o', 2: 'n'}
        command = f':{motor}{output_map[output]}{state}'
        self._send_command(command)

    def setEncoderCPR(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the encoder quadrature counts (PPR x 4).
        Default factory setting is 8192 (2048 PPR * 4).

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the encoder counts-per-revolution
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in self.QUADRATURE_COUNTS:
            raise ValueError(
                f"Invalid CPR '{value}'. Must be a quadrature total (PPR * 4) "
                f'supported by the datasheet. Supported: {sorted(list(self.QUADRATURE_COUNTS))}'
            )

        command = f':{motor}E{value}'
        self._send_command(command)

    def setOutputConfig(
        self, motor: Literal[1, 2], input: Literal[1, 2], value: Literal[0, 1, 2, 3]
    ) -> None:
        """
        Set an Output Configuration mode.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            input (int): the input to configure (1 or 2)
            value (int): the parameter where 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped
        """

        self._check_motor_input(motor)
        if input not in {1, 2}:
            raise ValueError(
                f'Invalid input selection: {input}. Valid input is 1 or 2.'
            )
        if value not in {0, 1, 2, 3}:
            raise ValueError(
                f'Invalid configuration mode: {value}. Valid modes are 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped'
            )

        input_map = {1: 'J', 2: 'K'}
        command = f':{motor}{input_map[input]}{value}'
        self._send_command(command)

    def setInputConfig(
        self,
        motor: Literal[1, 2],
        input: Literal[1, 2, 3, 4],
        value: Literal[0, 1, 2, 3],
    ) -> None:
        """
        Set an input configuration mode.

        Args:
            motor (int): motor to command (1=x-axis, 2=y-axis)
            input (int): input to configure (1, 2, 3, or 4)
            value (int): config mode (0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped)
        """

        self._check_motor_input(motor)
        if not isinstance(input, int):
            raise TypeError(
                f'Expected int for input arg but got {type(input).__name__}.'
            )
        if input not in {1, 2, 3, 4}:
            raise ValueError('Invalid input selection. Valid inputs are 1, 2, 3, or 4.')
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in {0, 1, 2, 3}:
            raise ValueError(
                'Invalid configuration mode. Valid modes are 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped'
            )

        input_map = {1: 'T', 2: 'U', 3: 'V', 4: 'W'}

        command = f':{motor}{input_map[input]}{value}'
        self._send_command(command)

    def setIdxConfig(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the index configuration mode

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): config mode (0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped)
        """

        self._check_motor_input(motor)
        if not isinstance(value, int):
            raise TypeError(
                f'Expected int for value arg but got {type(value).__name__}.'
            )
        if value not in {0, 1, 2, 3}:
            raise ValueError(
                'Invalid configuration mode. Valid modes are 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped'
            )

        command = f':{motor}Z{value}'
        self._send_command(command)

    # --- Homing ---

    def setHomingLoadError(self, motor: Literal[1, 2], value: int) -> None:
        """
        Set the allowable error before hard stop is detected when homing the motor.

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int): the load error setting in steps during homing
        """

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

    def setHome(self, motor: Literal[0, 1, 2], position: int) -> None:
        """
        Home to position

        Args:
            motor (int): the motor to command (0=both, 1=x-axis, 2=y-axis)
            position (int): the home position
        """

        self._check_motor_input(motor)
        if not isinstance(position, int):
            raise TypeError(
                f'Expected int for position arg but got {type(position).__name__}.'
            )
        if not -self.MAX_MOTOR_POSITION <= position <= self.MAX_MOTOR_POSITION:
            raise ValueError(
                f'Invalid position setting: {position}. Position setting must be between {-self.MAX_MOTOR_POSITION} and {self.MAX_MOTOR_POSITION}.'
            )
        command = f':{motor}c{position}'
        self._send_command(command)

    # --- Communication ---

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
                    f'Invalid baud setting: {baud}. Valid baud settings: {sorted(list(self.BAUD_RATES))}'
                )

        command = f':{motor}B{value}'
        self._send_command(command)

    def setAddress(self, motor: Literal[1, 2], value: int | str) -> None:
        """
        Set the address of a motor

        Args:
            motor (int): the motor to command (1=x-axis, 2=y-axis)
            value (int | str): the new address of the motor (1-9, A-F)
        """

        self._check_motor_input(motor)
        if not isinstance(value, (int, str)):
            raise TypeError(
                f'Expected int or str for value arg but got {type(value).__name__}.'
            )
        if value not in self.ADDRESSES:
            raise ValueError(
                f'Invalid address value: {value}. Valid address values are {list(self.ADDRESSES)}'
            )

        command = f':{motor}D{value}'
        self._send_command(command)

    ###################################################################################
    ################################# Get Requests ####################################
    ###################################################################################

    # --- Non-Volatile Settings ---

    def getNVAccel(self, motor: Literal[1, 2]) -> int:
        """
        Get the non-volatile memory acceleration setting in steps/sec-sq

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the non-volatile acceleration setting in steps/sec-sq
        """

        self._check_motor_input(motor)
        command = f':{motor}A'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getNVVelocity(self, motor: Literal[1, 2]) -> int:
        """
        Get the non-volatile max velocity in steps/sec

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the non-volitile max velocity in steps/sec
        """

        self._check_motor_input(motor)
        command = f':{motor}v'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getNVSpeed(self, motor: Literal[1, 2]) -> int:
        """
        Get the non-volatile memory speed setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the speed setting in steps/sec from non-volatile memory.
        """

        command = f':{motor}S'
        response = self._send_query(command).replace(command, '')
        return int(response)

    # --- Set Points ---

    def getSetPoint(self, motor: Literal[1, 2], set_point: int) -> dict[str, int]:
        """
        Get a set point's assigned position

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)
            set_point (int): the set point to query (0-9)

        Returns:
            dict(str, int): the position, velocity, and acceleration settings for the set point.
        """

        self._check_motor_input(motor)
        if not isinstance(set_point, int):
            raise TypeError(
                f'Expected int for set_point arg but got {type(set_point).__name__}.'
            )
        if set_point not in self.SET_POINTS:
            raise ValueError(
                f'Invalid set point selection {set_point}. Valid set points are {sorted(list(self.SET_POINTS))}'
            )

        command = f':{motor}{set_point}'
        response = self._send_query(command).replace(command, '')
        return {
            'position': int(response.split(',')[0]),
            'velocity': int(response.split(',')[1]),
            'accleration': int(response.split(',')[2]),
        }

    # --- Movement Settings ---

    def getMSteps(self, motor: Literal[1, 2]) -> int:
        """
        Get the number of micro-steps per step setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the number of micro-steps per step
        """

        self._check_motor_input(motor)
        command = f':{motor}M'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getDirection(self, motor: Literal[1, 2]) -> str:
        """
        Get the direction setting of the motor (CW or CCW)

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            str: the direction setting of the motor, "CW" or "CCW"
        """

        self._check_motor_input(motor)
        command = f':{motor}C'
        response = self._send_query(command).replace(command, '')
        direction_map = {'0': 'CW', '1': 'CCW'}
        return direction_map[response]

    def getAccel(self, motor: Literal[1, 2]) -> int:
        """
        Get the acceleration setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the acceleration of the motor
        """

        self._check_motor_input(motor)
        command = f':{motor}a'
        response = self._send_query(command)
        return int(response.replace(command, ''))

    def getSpeed(self, motor: Literal[1, 2]) -> int:
        """
        Get the current speed of the motor in steps/sec

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the current speed of the motor in steps/sec
        """

        self._check_motor_input(motor)
        command = f':{motor}s'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getLoadError(self, motor: Literal[1, 2]) -> int:
        """
        Get the allowable following-error-before-faulting setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the allowable following error setting
        """

        self._check_motor_input(motor)
        command = f':{motor}L'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getRPM(self, motor: Literal[1, 2]) -> float:
        """
        Get the RPM of a motor. (xxxx = XX.XX)

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            float: the motor RPM
        """

        self._check_motor_input(motor)
        command = f':{motor}u'
        response = self._send_query(command).replace(command, '')
        if response == '!':
            return float('nan')
        return int(response) / 100.0

    # --- Positioning ---

    def getPos(self, motor: Literal[1, 2]) -> int:
        """
        Get the position of a motor

        Args:
            motor (int): motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the position of the motor
        """

        self._check_motor_input(motor)
        command = f':{motor}p'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getAbsPos(self, motor: Literal[1, 2]) -> float:
        """
        Get the absolute position of the motor in degrees.

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            float: the absolute position of the motor in degrees (0-360.0)
        """

        self._check_motor_input(motor)
        command = f':{motor}x'
        response = self._send_query(command).replace(command, '')
        if response == '!':
            return float('nan')
        return int(response) / 10.0

    def getEncoderPos(self, motor: Literal[1, 2]) -> int:
        """
        Get the encoder counts (can be negative)

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the encoder counts
        """

        self._check_motor_input(motor)
        command = f':{motor}y'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getFollowingError(self, motor: Literal[1, 2]) -> int:
        """
        Get the Following Error expressed as micro-steps relative to the encoder count (ratio)

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the ratio of micro-steps relative to the encoder count
        """

        self._check_motor_input(motor)
        command = f':{motor}b'
        response = self._send_query(command)
        return int(response.replace(command, ''))

    # --- Phase Current Settings ---

    def getCurrRange(self, motor: Literal[1, 2]) -> int:
        """
        Get the current range setting.

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the current range setting (0=high=2.0A, 1=low=1.0A)
        """

        self._check_motor_input(motor)
        command = f':{motor}O'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getHoldingCurr(self, motor: Literal[1, 2]) -> float:
        """
        Get the holding current setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            float: the holding current setting in amps
        """

        self._check_motor_input(motor)
        command = f':{motor}H'
        response = self._send_query(command).replace(command, '')
        value = int(response)

        amps = value * self.amps_per_step
        return round(amps, 3)

    def getRunCurr(self, motor: Literal[1, 2]) -> float:
        """
        Get the run current setting.

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            float: the run current setting in amps
        """

        self._check_motor_input(motor)
        command = f':{motor}R'
        response = self._send_query(command).replace(command, '')
        value = int(response)

        amps = value * self.amps_per_step
        return round(amps, 3)

    # --- Initialization ---

    def getInputConfig(self, motor: Literal[1, 2], input: Literal[1, 2, 3, 4]) -> int:
        """
        Get an input configuration setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)
            input (int): the input to query (1, 2, 3, or 4)

        Returns:
            int: config mode (0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped)
        """

        self._check_motor_input(motor)
        if not isinstance(input, int):
            raise TypeError(
                f'Expected int for input arg but got {type(input).__name__}.'
            )
        if input not in {1, 2, 3, 4}:
            raise ValueError(
                f'Invalid input selection: {input}. Valid inputs are [1, 2, 3, 4]'
            )

        input_map = {1: 'T', 2: 'U', 3: 'V', 4: 'W'}
        command = f':{motor}{input_map[input]}'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getOutputConfig(self, motor: Literal[1, 2], output: Literal[1, 2]) -> int:
        """
        Get an output configuration setting.

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)
            ouput (int): the output to query (1 or 2)

        Returns:
            int: the output setting where, 0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped
        """

        self._check_motor_input(motor)
        if not isinstance(output, int):
            raise TypeError(
                f'Expected int for output arg but got {type(output).__name__}.'
            )
        if output not in {1, 2}:
            raise ValueError(
                f'Invalid output selection: {output}. Valid outputs are 1 or 2.'
            )

        output_map = {1: 'J', 2: 'K'}
        command = f':{motor}{output_map[output]}'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getIdxConfig(self, motor: Literal[1, 2]) -> int:
        """
        Get the index configuration parameter

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: config mode (0=User Defined, 1=Motor Error, 2=Motor Moving, 3=Motor Stopped)
        """

        command = f':{motor}Z'
        response = self._send_query(command).replace(command, '')
        return int(response)

    def getEncoderCPR(self, motor: Literal[1, 2]) -> int:
        """
        Get the encoder counts-per-revolution setting

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the encoder counts-per-revolution setting
        """

        self._check_motor_input(motor)
        command = f':{motor}E'
        response = self._send_query(command).replace(command, '')
        return int(response)

    # --- Homing ---

    def getHomingLoadError(self, motor: Literal[1, 2]) -> int:
        """
        Get the allowable error setting before hard stop in detected

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the error setting
        """

        self._check_motor_input(motor)
        command = f':{motor}I'
        response = self._send_query(command).replace(command, '')
        return int(response)

    # --- Communication ---

    def getSoftwareRev(self, motor: Literal[1, 2]) -> str:
        """
        Get the series revision date

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            str: 'xyz' = Series Revision-Date
        """

        self._check_motor_input(motor)
        command = f':{motor}z'
        return self._send_query(command).replace(command, '')

    def getBaud(self, motor: Literal[1, 2]) -> int | None:
        """
        Get the baud rate for serial communication

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            int: the baud rate if set
            None: if the baud rate has not been set
        """

        self._check_motor_input(motor)
        command = f':{motor}B'
        response = self._send_query(command).replace(command, '')
        baud_map = {
            '0': None,
            '1': 9600,
            '2': 19200,
            '3': 38400,
            '4': 57600,
            '5': 115200,
        }
        return baud_map[response]

    def getAddresses(self) -> str:
        """Get the addresses of the motors"""
        # TODO: add the motor arg back in. Sending ":0D" actually sends ":1D"

        command = ':0D'
        return self._send_query(command).replace(command, '')

    # --- Statuses ---

    def getIdxStates(self, motor: Literal[1, 2]) -> list[int]:
        """
        Get status of all inputs 4 + index

        Args:
            motor (int): motor to query (1=x-axis, 2=y-axis)

        Returns:
            list(int): [i1, i2, i3, i4, idx] where:
                1=High
                0=Low
        """

        self._check_motor_input(motor)
        command = f':{motor}l'
        response = self._send_query(command).replace(command, '')
        return [int(char) for char in response]

    def getOutputStatus(self, motor: Literal[1, 2], output: Literal[1, 2]) -> int:
        """
        Get status of an output signal

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)
            output (int): the output to read (1 or 2)

        Returns:
            int: status of the output signal where 1=On and 0=Off.
        """

        self._check_motor_input(motor)
        if not isinstance(output, int):
            raise TypeError(
                f'Expected int for output arg but got {type(output).__name__}.'
            )
        if output not in {1, 2}:
            raise ValueError(
                f'Invalid output selection: {output}. Valid outputs are 1 or 2.'
            )

        output_map = {1: 'o', 2: 'n'}
        command = f':{motor}{output_map[output]}'
        response = self._send_query(command)
        return int(response.replace(command, ''))

    def getStatus(self, motor: Literal[1, 2]) -> str:
        """Get the (1) system status and (2) current active Set Point."""
        # TODO: check the response of getStatus and format the return value appropriately
        # response = ':1f0\x000'
        # response.replace(command, '') = '0\x000' even when motor 1 was sent to setpoint 1

        self._check_motor_input(motor)
        command = f':{motor}f'
        response = self._send_query(command).replace(command, '')
        return response

    def getMotorStatus(self, motor: Literal[1, 2]) -> list[int]:
        """
        Get the motor status

        Args:
            motor (int): the motor to query (1=x-axis, 2=y-axis)

        Returns:
            list(int): [x, y] where:
                x=1=Motor Running, x=2=Motor Stopped
                y=Motor Status:
                    0=Motor Ready
                    1=Motor Not Homed
                    2=Motor Not Initialized
                    3=Motor Error
        """

        self._check_motor_input(motor)
        command = f':{motor}g'
        response = self._send_query(command).replace(command, '')
        return [int(char) for char in response]
