import subprocess
import tempfile
import os
import time
from typing import Dict, Any
from .base_agent import Z9Agent

class ScreenAgent(Z9Agent):
    """
    ScreenAgent (charge 3): Capable of reading the screen via screenshots + OCR
    and writing to the screen via typing text (simulated keyboard input).
    """

    def __init__(self):
        super().__init__(name="ScreenAgent", charge=3)

    def get_system_prompt(self) -> str:
        return (
            "You are the ScreenAgent.\n"
            "You can read the screen using OCR and write to it by typing text.\n"
            "Commands: 'read', 'type <text>'\n"
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
        else:
            return {"success": False, "error": f"Unknown command '{cmd}'. Use 'read' or 'type'."}

    def _read_screen(self) -> Dict[str, Any]:
        """Takes a screenshot using grim and extracts text using tesseract."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Take screenshot
            res = subprocess.run(["grim", tmp_path], capture_output=True, text=True)
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
        """Types text using wtype."""
        if not text:
            return {"success": False, "error": "No text provided to type."}
        
        try:
            # wtype handles string arguments as text to type
            res = subprocess.run(["wtype", text], capture_output=True, text=True)
            if res.returncode != 0:
                return {"success": False, "error": f"Failed to type text: {res.stderr}"}
            
            return {"success": True, "message": f"Successfully typed: {text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

