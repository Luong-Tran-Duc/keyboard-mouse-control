"""Configuration for KM Bridge Desktop Client."""

# Network Configuration
ESP32_IP = "192.168.1.217"
UDP_PORT = 9876

# Hotkey to toggle control between Laptop A and Laptop B
TOGGLE_HOTKEY = "<ctrl>+<alt>+<space>"

# Mouse settings
# Sensitivity multiplier (1.0 = original 1:1 raw hardware movement)
MOUSE_SENSITIVITY = 1.0

# Disable acceleration for pure 1:1 linear tracking
MOUSE_ACCELERATION = False

# Mouse transmission rate in Hz (100Hz = 10ms, perfectly matched to USB HID 10ms polling interval)
MOUSE_POLL_RATE_HZ = 100

# Invert axes if desired
INVERT_X = False
INVERT_Y = False
