#!/usr/bin/env python3
"""
METATRON OS — agents/doc_agent.py
DocAgent (charge = 4)
Handles advanced document extraction (PDF, etc.) using opendataloader-pdf.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import opendataloader_pdf
    HAS_OPENDATALOADER = True
except ImportError:
    HAS_OPENDATALOADER = False

from agents.base_agent import Z9Agent


class DocAgent(Z9Agent):
    """Z9 agent with charge 4: document intelligence and extraction."""

    def __init__(self):
        super().__init__(name="DocAgent", charge=4)

    def execute(
        self,
        path: str,
        operation: str = "convert",
        format: str = "markdown",
        hybrid: bool = False,
    ) -> Dict[str, Any]:
        """
        Perform document extraction or conversion.

        Operations: convert | read | extract
        Formats: markdown | json | text | html
        """
        if not HAS_OPENDATALOADER:
            return {
                "success": False,
                "error": "opendataloader-pdf is not installed. Run 'pip install opendataloader-pdf[hybrid]'"
            }

        try:
            p = Path(path).expanduser().resolve()
            if not p.exists():
                return {"success": False, "error": f"Path not found: {p}"}

            if operation in ("convert", "read", "extract"):
                return self._convert(p, format, hybrid)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── private helpers ────────────────────────────────────────

    def _convert(self, p: Path, format: str, hybrid: bool) -> Dict[str, Any]:
        """Converts document to the specified format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # opendataloader_pdf.convert parameters:
                # input_path (list), output_dir (str), format (str), hybrid (str/None)
                
                hybrid_mode = "docling-fast" if hybrid else None
                
                opendataloader_pdf.convert(
                    input_path=[str(p)],
                    output_dir=tmp_dir,
                    format=format,
                    hybrid=hybrid_mode
                )
                
                # The output files are named after the input file but with the new extension
                # We need to find the output file in tmp_dir
                output_files = list(Path(tmp_dir).glob("*"))
                if not output_files:
                    return {"success": False, "error": "Conversion produced no output."}
                
                # For simplicity, we'll return the content of the first output file
                # If multiple formats were requested, they would all be here
                results = {}
                for out_f in output_files:
                    ext = out_f.suffix[1:] # remove the dot
                    try:
                        results[ext] = out_f.read_text(errors="replace")
                    except Exception:
                        results[ext] = f"[Binary data: {out_f.name}]"

                return {
                    "success": True,
                    "path": str(p),
                    "format": format,
                    "hybrid": hybrid,
                    "outputs": results,
                    # Primary content is usually the first one or the requested format
                    "content": results.get(format.split(',')[0], list(results.values())[0])
                }

            except Exception as exc:
                return {"success": False, "error": f"Opendataloader error: {exc}"}
