import time
from typing import Literal, Optional

from src.model.stage import Stage

###################################################################################
###################################################################################
###################################################################################


class Controller:
    def __init__(self, stage: Stage) -> None:
        self.s = stage
        self.homed = False

    def home(self, motor: Literal[1, 2], speed: Optional[int] = None) -> None:
        try:
            speed = speed or self.s.getNVVelocity(motor)
            if speed != self.s.getNVVelocity(motor):
                self.s.setVelocity(motor, speed)
            self.s.gotoPos(motor, int(-self.s.MAX_MOTOR_POSITION))
            print(f'Homing motor {motor}... Press Ctrl+C to emergency stop.')
            input2 = self.s.getIdxStates(motor)[1]
            while input2 != 1:
                input2 = self.s.getIdxStates(motor)[1]
                pos = self.s.getPos(motor)
                print(f'{input2 = }, {pos = }')
                time.sleep(0.25)
            self.s.halt(motor)
            print('Input2 switch activated!')
            time.sleep(0.1)
            self.s.setVelocity(motor, 1000)
            self.s.jog(motor, 5000)
            while input2 != 0:
                input2 = self.s.getIdxStates(motor)[1]
                pos = self.s.getPos(motor)
                print(f'{input2 = }, {pos = }')
                time.sleep(0.25)
            self.s.initMotor(motor)  # reset motor position reading to zero
            self.homed = True
            print(f'Motor {motor} homed.')
        except KeyboardInterrupt:
            print('\n[!] User interrupted. Sending HALT command...')
            # Immediately stop the hardware
            self.s.halt(motor)
            print('Motor halted safely. Exiting.')
            # Re-raising allows the script to finish its shutdown process
            raise

    def center(self, motor: Literal[1, 2]) -> None:
        if self.homed:
            self.s.gotoSetPoint(motor, 0)
