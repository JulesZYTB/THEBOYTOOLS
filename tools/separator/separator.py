import os
import sys
from typing import List, Any, Optional

class Separator:
    """
    Separator Tool — Computes the difference between two sets of tokens.
    A local tool for separating overlapping or duplicated tokens.
    """
    
    TOOL_NAME = "separator"

    def __init__(self):
        self._output_root = os.path.join(self._get_project_root(), "tools", self.TOOL_NAME, "output")

    def _get_project_root(self) -> str:
        """Get project root (EXE-safe)."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_output_dir(self, subfolder: str = "") -> str:
        """Get the output directory for this tool, creating it if needed."""
        path = os.path.join(self._output_root, subfolder)
        os.makedirs(path, exist_ok=True)
        return path

    def clear_output(self):
        """Clear all output files for a fresh run."""
        if not os.path.exists(self._output_root):
            return
        for root, dirs, files in os.walk(self._output_root):
            for file in files:
                if file.endswith(".txt"):
                    try:
                        os.remove(os.path.join(root, file))
                    except:
                        pass

    def separate_tokens(self, tokens_1: List[str], tokens_2: List[str], mode: str = "1_from_2") -> dict:
        """
        Subtracts one list from another based on mode.
        mode can be:
          "1_from_2" -> removes elements of tokens_1 from tokens_2 (Output tokens_2 - tokens_1)
          "2_from_1" -> removes elements of tokens_2 from tokens_1 (Output tokens_1 - tokens_2)

        Returns a dictionary with result metrics.
        """
        # We strip tokens to be sure
        set1 = set(t.strip() for t in tokens_1 if t.strip())
        set2 = set(t.strip() for t in tokens_2 if t.strip())
        
        result_list = []
        original_count = 0
        removed_count = 0
        
        if mode == "1_from_2":
            original_count = len(set2)
            result_set = set2 - set1
            result_list = sorted(list(result_set))
            removed_count = original_count - len(result_list)
        elif mode == "2_from_1":
            original_count = len(set1)
            result_set = set1 - set2
            result_list = sorted(list(result_set))
            removed_count = original_count - len(result_list)
        else:
            return {"success": False, "message": "Unknown separation mode."}

        out_dir = self._get_output_dir()
        filepath = os.path.join(out_dir, "separated_tokens.txt")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for item in result_list:
                    f.write(f"{item}\n")
            
            return {
                "success": True,
                "original_count": original_count,
                "removed_count": removed_count,
                "separated_count": len(result_list),
                "output_file": filepath
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

