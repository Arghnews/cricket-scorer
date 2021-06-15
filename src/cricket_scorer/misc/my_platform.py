import platform

def _check_i2c_enabled():
    try:
        from smbus2 import SMBus
        return True
    except Exception:
        return False

IS_WINDOWS = platform.system() == "Windows"
EXCEL_ENABLED = IS_WINDOWS
I2C_ENABLED = _check_i2c_enabled()
