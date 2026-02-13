import json
import sys
from configparser import ConfigParser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog


def get_app_version() -> str:
    """
    Retrieves the current version of the application.

    Attempts to fetch the version metadata for the 'e_reg_controller' package.
    This is typically used when the application is installed via pip or
    bundled as a package.

    Returns:
        str: The version string (e.g., '1.0.0') if the package is installed,
            otherwise returns 'development-build'.

    Note:
        Relies on `importlib.metadata.version`.
    """
    try:
        return version('e_reg_controller')
    except PackageNotFoundError:
        return 'development-build'


def get_state_img(
    state: Literal['disabled', 'pressurized', 'venting', 'bypassed'],
) -> QPixmap:
    pixmap = QPixmap()
    root = get_root_dir()
    match state:
        case 'disabled':
            path = str(root / 'assets' / 'e-reg_disabled.png')
            return QPixmap(path)
        case 'pressurized':
            path = str(root / 'assets' / 'e-reg_pressurized.png')
            return QPixmap(path)
        case 'venting':
            path = str(root / 'assets' / 'e-reg_venting.png')
            return QPixmap(path)
        case 'bypassed':
            path = str(root / 'assets' / 'e-reg_bypassed.png')
            return QPixmap(path)
    return pixmap


def get_icon() -> QIcon:
    """
    Loads the application icon from the assets directory.

    Constructs the absolute path to the 'icon.ico' file using the root
    directory helper to ensure compatibility between development
    environments and compiled executables.

    Returns:
        QIcon: A Qt icon object. If the file is not found at the
            calculated path, an empty QIcon is returned.

    Note:
        Expects the icon to be located at 'assets/icon.ico' relative
        to the application root.
    """
    root_dir: Path = get_root_dir()
    icon_path: str = str(root_dir / 'assets' / 'icon.ico')
    return QIcon(icon_path)


def get_root_dir() -> Path:
    """
    Determines the base directory of the application.

    This function identifies the root path whether the script is running
    in a standard Python interpreter or as a bundled executable (e.g.,
    created by PyInstaller).

    Returns:
        Path: The absolute path to the application root directory.
            If frozen, returns the temporary extraction directory (_MEIPASS).
            If not frozen, returns the grandparent directory of this file.

    Notes:
        - 'sys.frozen' is a flag set by PyInstaller.
        - '_MEIPASS' is the internal attribute PyInstaller uses to store
          the path to the temporary folder where resources are unpacked.
    """
    if getattr(sys, 'frozen', False):  # Check if running from the PyInstaller EXE
        return Path(getattr(sys, '_MEIPASS', '.'))
    else:  # Running in a normal Python environment
        return Path(__file__).resolve().parents[1]


def _get_ini_filepath() -> Path:
    """
    Constructs the absolute path to the application's configuration file.

    This internal helper utilizes `get_root_dir()` to ensure the path is
    resolved correctly regardless of whether the application is running
    from source or as a bundled executable.

    Returns:
        Path: The absolute path pointing to 'configuration/config.ini'
            relative to the application root.

    Note:
        This function defines the expected project structure where the
        INI file must reside within a 'configuration' directory.
    """
    root_dir = get_root_dir()
    ini_filepath = Path(root_dir / 'configuration' / 'config.ini')
    return ini_filepath


def load_ini() -> ConfigParser:
    """
    Loads and parses the application configuration from an INI file.

    This helper function locates the configuration file path using
    `_get_ini_filepath()`, initializes a ConfigParser object, and
    reads the file data into memory.

    Returns:
        ConfigParser: A populated configuration object containing the
            settings defined in the INI file.

    Note:
        If the INI file does not exist at the resolved path, the returned
        ConfigParser object will be empty rather than raising a FileNotFoundError,
        per the standard behavior of `ConfigParser.read()`.
    """
    config_data = ConfigParser()
    ini_filepath: Path = _get_ini_filepath()
    config_data.read(str(ini_filepath))
    return config_data


def convert_psi_to_mbar(pressure: float) -> float:
    """
    Converts a pressure value from pounds per square inch (PSI) to millibars (mBar).

    The conversion uses the factor: 1 PSI ≈ 68.9476 mBar.

    Args:
        pressure (float): The pressure value in PSI to be converted.

    Returns:
        float: The equivalent pressure value in mBar.

    Raises:
        ValueError: If the provided pressure is not a numeric type (int or float).

    Note:
        This function performs a strict type check to ensure mathematical
        reliability during hardware data processing.
    """

    if not isinstance(pressure, int | float):
        raise ValueError(
            f'Received {type(pressure).__name__} but expected int or float.'
        )

    return round(pressure * 68.9476, 2)


def convert_mbar_to_psi(pressure: float) -> float:
    """
    Converts a pressure value from millibars (mBar) to pounds per square inch (PSI).

    The conversion uses the factor: 1 mBar ≈ 0.0145038 PSI.

    Args:
        pressure (float): The pressure value in mBar to be converted.

    Returns:
        float: The equivalent pressure value in PSI.

    Raises:
        ValueError: If the provided pressure is not a numeric type (int or float).

    Note:
        This is the inverse of the PSI-to-mBar conversion and is used to
        translate user setpoints into the units required by the hardware.
    """
    if not isinstance(pressure, int | float):
        raise ValueError(
            f'Received {type(pressure).__name__} but expected int or float.'
        )
    return round(pressure * 1.45038e-2, 2)


def get_json_data() -> list[dict[str, str]]:
    filepath: Path = get_root_dir() / 'data_cache' / 'history.json'
    with open(filepath, 'r') as f:
        data: list[dict[str, str]] = json.load(f)
    return data


def select_file(default_dir: str | None = None) -> str:
    filepath: str
    if not default_dir:
        default_dir = ''
    filepath, _ = QFileDialog.getOpenFileName(
        parent=None, caption='Choose File', dir=default_dir
    )
    return filepath


def select_folder(default_dir: str | None = None) -> str:
    """
    Open a file dialog to select a folder.

    Returns:
        str: The path to the selected folder. If the dialog is cancelled,
             an empty string is returned.
    """
    if not default_dir:
        default_dir = ''
    folder_path: str = QFileDialog.getExistingDirectory(
        parent=None,
        caption='Choose Folder',
        dir=default_dir,
        options=QFileDialog.Option.ShowDirsOnly,
    )
    return folder_path


def select_save_folder(default_dir: str | None = None) -> str:
    """
    Open a file dialog to select a folder.

    Returns:
        str: The path to the selected folder. If the dialog is cancelled,
             an empty string is returned.
    """
    if not default_dir:
        default_dir = ''
    filepath, _ = QFileDialog.getSaveFileName(
        parent=None,
        caption='Save Plot',
        dir=default_dir,
        filter='PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)',
    )
    return filepath


def get_most_recent_file() -> Path | None:
    # Create a path object
    basepath = Path('C://TeststandData')

    # Use rglob('*') to find all files recursively
    # We filter with is_file() to ignore directory modification times
    files = (f for f in basepath.rglob('*') if f.is_file())

    # Use max() with the stat().st_mtime as the key to find the latest
    try:
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        return latest_file
    except ValueError:
        # This happens if the directory is empty
        return None


if __name__ == '__main__':
    # --- How to get the data in the ini file ---
    # config_data = load_ini()
    # IPAddress = config_data.get('IPAddress', 'IPAddress')
    # print(IPAddress)

    # --- Data from history.json ---
    data = get_json_data()
    print(data)
