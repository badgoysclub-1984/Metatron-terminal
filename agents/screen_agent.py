import subprocess
import tempfile
import os
import time
from typing import Dict, Any
from .base_agent import Z9Agent

class ScreenAgent(Z9Agent):
    """
    ScreenAgent (charge 3): Capable of reading the screen via screenshots + OCR
    and writing to the screen via typing text (simulated keyboard input) or mouse actions.
    """

    def __init__(self):
        super().__init__(name="ScreenAgent", charge=3)

    def get_system_prompt(self) -> str:
        return (
            "You are the ScreenAgent.\n"
            "You can read the screen using OCR and write to it by typing text or using the mouse.\n"
            "Commands: 'read', 'type <text>', 'click', 'right_click', 'double_click', 'move <x> <y>'\n"
        )

    def execute(self, command: str, *args, **kwargs) -> Dict[str, Any]:
        cmd = command.strip().lower()
        if cmd == "read":
            return self._read_screen()
        elif cmd == "type":
            text = " ".join(args) if args else ""
            if not text and "text" in kwargs:
                text = kwargs["text"]
            return self._type_text(text)
        elif cmd == "click":
            return self._mouse_action("click")
        elif cmd == "right_click":
            return self._mouse_action("click", button="right")
        elif cmd == "double_click":
            return self._mouse_action("click", repeat="2")
        elif cmd.startswith("move"):
            try:
                parts = cmd.split()
                if len(parts) >= 3:
                    x, y = parts[1], parts[2]
                elif "x" in kwargs and "y" in kwargs:
                    x, y = kwargs["x"], kwargs["y"]
                else:
                    x, y = args[0], args[1]
                return self._mouse_action("move", x=str(x), y=str(y))
            except Exception as e:
                return {"success": False, "error": f"Invalid move arguments: {e}"}
        else:
            return {"success": False, "error": f"Unknown command '{cmd}'."}

    def _read_screen(self) -> Dict[str, Any]:
        """Takes a screenshot using grim and extracts text using tesseract."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Take screenshot
            res = subprocess.run(["grim", tmp_path], capture_output=True, text=True)
            if res.returncode != 0:
                # Fallback to scrot if grim is not available (X11)
                res = subprocess.run(["scrot", "-o", tmp_path], capture_output=True, text=True)
                if res.returncode != 0:
                    return {"success": False, "error": f"Failed to take screenshot: {res.stderr}"}
            
            # OCR
            res_ocr = subprocess.run(["tesseract", tmp_path, "stdout"], capture_output=True, text=True)
            if res_ocr.returncode != 0:
                return {"success": False, "error": f"Failed OCR: {res_ocr.stderr}"}
            
            text = res_ocr.stdout.strip()
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _type_text(self, text: str) -> Dict[str, Any]:
        """Types text using wtype or xdotool."""
        if not text:
            return {"success": False, "error": "No text provided to type."}
        
        try:
            # Try wtype first (Wayland)
            res = subprocess.run(["wtype", text], capture_output=True, text=True)
            if res.returncode != 0:
                # Fallback to xdotool (X11/Xwayland)
                res = subprocess.run(["xdotool", "type", text], capture_output=True, text=True)
                if res.returncode != 0:
                    return {"success": False, "error": f"Failed to type text: {res.stderr}"}
            
            return {"success": True, "message": f"Successfully typed: {text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _mouse_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """Performs mouse actions using ydotool or xdotool."""
        try:
            if action == "click":
                button = kwargs.get("button", "left")
                btn_code = "1" if button == "left" else "3" if button == "right" else "2"
                repeat = kwargs.get("repeat", "1")
                
                # Try ydotool
                res = subprocess.run(["ydotool", "click", "0xC0" if button=="left" else "0xC1"], capture_output=True, text=True)
                if res.returncode != 0:
                    # Fallback to xdotool
                    cmd = ["xdotool", "click", "--repeat", repeat, btn_code]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                return {"success": res.returncode == 0, "message": f"{button} click {repeat}x"}
                
            elif action == "move":
                x, y = kwargs.get("x", "0"), kwargs.get("y", "0")
                # Try ydotool
                res = subprocess.run(["ydotool", "mousemove", "--absolute", "-x", x, "-y", y], capture_output=True, text=True)
                if res.returncode != 0:
                    # Fallback to xdotool
                    res = subprocess.run(["xdotool", "mousemove", x, y], capture_output=True, text=True)
                return {"success": res.returncode == 0, "message": f"Moved to {x}, {y}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Unknown mouse action."}

