"""Configuration for KM Bridge Desktop Client."""

# Network Configuration
ESP32_IP = "192.168.1.216"
UDP_PORT = 9876

# Hotkey to toggle control between Laptop A and Laptop B
TOGGLE_HOTKEY = "<ctrl>+<alt>+<space>"

# Mouse settings
# Sensitivity multiplier (1.0 = original 1:1 raw hardware movement)
MOUSE_SENSITIVITY = 1.0

# Disable acceleration for pure 1:1 linear tracking
MOUSE_ACCELERATION = False

# Mouse transmission rate in Hz (125Hz = 8ms interval for smooth tracking)
MOUSE_POLL_RATE_HZ = 125

# Invert axes if desired
INVERT_X = False
INVERT_Y = False
