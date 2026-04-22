import os
import yaml
from typing import Dict, Any

class StyleEngine:
    def __init__(self, style_name: str = "pelevin", styles_dir: str = "styles"):
        self.styles_dir = styles_dir
        self.base_config = self._load_yaml(os.path.join(styles_dir, "base.yaml"))
        self.author_config = self._load_yaml(os.path.join(styles_dir, f"{style_name}.yaml"))
        
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def build_prompt(self, diary_entries: list, graph_context: str, chapter_number: int) -> dict:
        system = self.base_config.get("system_prompt", "") + "\n\n" + self.author_config.get("system_prompt", "")
        
        user_template = self.base_config.get("user_template", "")
        user_prompt = user_template.format(
            diary_entries="\n".join(diary_entries),
            graph_context=graph_context,
            chapter_number=chapter_number
        )
        
        temperature = self.author_config.get("temperature", self.base_config.get("temperature", 0.85))
        max_tokens = self.author_config.get("max_tokens", self.base_config.get("max_tokens", 3000))
        
        return {
            "system_prompt": system,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }