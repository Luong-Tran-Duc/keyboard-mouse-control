"""Windows Raw Input Mouse Capture with click suppression for KM Bridge."""

import threading
import ctypes
from ctypes import wintypes
import win32gui
import win32con

user32 = ctypes.windll.user32

WM_INPUT = 0x00FF
RID_INPUT = 0x10000003

RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
RI_MOUSE_LEFT_BUTTON_UP = 0x0002
RI_MOUSE_RIGHT_BUTTON_DOWN = 0x0004
RI_MOUSE_RIGHT_BUTTON_UP = 0x0008
RI_MOUSE_MIDDLE_BUTTON_DOWN = 0x0010
RI_MOUSE_MIDDLE_BUTTON_UP = 0x0020
RI_MOUSE_WHEEL = 0x0400

WH_MOUSE_LL = 14
HOOKPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
MOUSE_BLOCK_MSGS = {
    0x0201, 0x0202,  # WM_LBUTTONDOWN, WM_LBUTTONUP
    0x0204, 0x0205,  # WM_RBUTTONDOWN, WM_RBUTTONUP
    0x0207, 0x0208,  # WM_MBUTTONDOWN, WM_MBUTTONUP
    0x020A, 0x020E   # WM_MOUSEWHEEL, WM_MOUSEHWHEEL
}


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ('usUsagePage', wintypes.USHORT),
        ('usUsage', wintypes.USHORT),
        ('dwFlags', wintypes.DWORD),
        ('hwndTarget', wintypes.HWND)
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ('dwType', wintypes.DWORD),
        ('dwSize', wintypes.DWORD),
        ('hDevice', wintypes.HANDLE),
        ('wParam', wintypes.WPARAM)
    ]


class _RAWMOUSE_BUTTONS(ctypes.Structure):
    _fields_ = [
        ('usButtonFlags', wintypes.USHORT),
        ('usButtonData', wintypes.USHORT)
    ]


class _RAWMOUSE_U(ctypes.Union):
    _anonymous_ = ('s',)
    _fields_ = [
        ('ulButtons', wintypes.ULONG),
        ('s', _RAWMOUSE_BUTTONS)
    ]


class RAWMOUSE(ctypes.Structure):
    _anonymous_ = ('u',)
    _fields_ = [
        ('usFlags', wintypes.USHORT),
        ('u', _RAWMOUSE_U),
        ('ulRawButtons', wintypes.ULONG),
        ('lLastX', wintypes.LONG),
        ('lLastY', wintypes.LONG),
        ('ulExtraInformation', wintypes.ULONG)
    ]


class RAWINPUT(ctypes.Structure):
    class _DATA(ctypes.Union):
        _fields_ = [('mouse', RAWMOUSE)]
    _fields_ = [
        ('header', RAWINPUTHEADER),
        ('data', _DATA)
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('message', wintypes.UINT),
        ('wParam', wintypes.WPARAM),
        ('lParam', wintypes.LPARAM),
        ('time', wintypes.DWORD),
        ('pt', wintypes.POINT)
    ]


class RawMouseListener:
    def __init__(self, on_move, on_click, on_scroll):
        self.on_move = on_move
        self.on_click = on_click
        self.on_scroll = on_scroll
        self.running = False
        self.suppress = False  # True when controlling Laptop B to block clicks on Laptop A
        self.thread = None
        self.hwnd = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run(self):
        raw_input = RAWINPUT()
        header_size = ctypes.sizeof(RAWINPUTHEADER)

        def wnd_proc(hwnd, msg, wp, lp):
            if msg == WM_INPUT:
                size = wintypes.UINT(ctypes.sizeof(RAWINPUT))
                res = user32.GetRawInputData(
                    lp, RID_INPUT, ctypes.byref(raw_input), ctypes.byref(size), header_size
                )
                if res != 0xFFFFFFFF and self.running:
                    m = raw_input.data.mouse
                    dx = m.lLastX
                    dy = m.lLastY
                    if dx != 0 or dy != 0:
                        self.on_move(dx, dy)

                    flags = m.usButtonFlags
                    if flags != 0:
                        if flags & RI_MOUSE_LEFT_BUTTON_DOWN:
                            self.on_click(1, True)
                        if flags & RI_MOUSE_LEFT_BUTTON_UP:
                            self.on_click(1, False)
                        if flags & RI_MOUSE_RIGHT_BUTTON_DOWN:
                            self.on_click(2, True)
                        if flags & RI_MOUSE_RIGHT_BUTTON_UP:
                            self.on_click(2, False)
                        if flags & RI_MOUSE_MIDDLE_BUTTON_DOWN:
                            self.on_click(4, True)
                        if flags & RI_MOUSE_MIDDLE_BUTTON_UP:
                            self.on_click(4, False)

                        if flags & RI_MOUSE_WHEEL:
                            delta = ctypes.c_short(m.usButtonData).value // 120
                            if delta != 0:
                                self.on_scroll(delta)

                return 0
            elif msg == win32con.WM_CLOSE:
                win32gui.DestroyWindow(hwnd)
                return 0
            elif msg == win32con.WM_DESTROY:
                win32gui.PostQuitMessage(0)
                return 0

            return win32gui.DefWindowProc(hwnd, msg, wp, lp)

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = wnd_proc
        wc.lpszClassName = 'KMBridgeRawMouseWndClass'
        try:
            atom = win32gui.RegisterClass(wc)
        except Exception:
            atom = 'KMBridgeRawMouseWndClass'

        self.hwnd = win32gui.CreateWindow(atom, 'KMBridgeRawMouse', 0, 0, 0, 0, 0, 0, 0, 0, None)

        # Register Raw Input Device
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01  # Generic Desktop Controls
        rid.usUsage = 0x02      # Mouse
        rid.dwFlags = 0x00000100  # RIDEV_INPUTSINK (receive input even when unfocused)
        rid.hwndTarget = self.hwnd
        user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE))

        # Install low level mouse hook to swallow clicks on Laptop A when active
        def hook_proc(code, wp, lp):
            if code >= 0 and self.suppress and wp in MOUSE_BLOCK_MSGS:
                return 1  # Suppress click on Laptop A!
            return user32.CallNextHookEx(None, code, wp, lp)

        hook_cb = HOOKPROCTYPE(hook_proc)
        h_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, hook_cb, 0, 0)

        try:
            msg = MSG()
            while self.running:
                res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if res <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if h_hook:
                user32.UnhookWindowsHookEx(h_hook)
