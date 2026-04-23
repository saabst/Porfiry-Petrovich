import os
import yaml
from typing import Dict, Any, Optional

class StyleEngine:
    def __init__(self, style_name: str = "pelevin", styles_dir: str = "styles"):
        self.styles_dir = styles_dir
        self.base_config = self._load_yaml(os.path.join(styles_dir, "base.yaml"))
        self.author_config = self._load_yaml(os.path.join(styles_dir, f"{style_name}.yaml"))
        
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def build_prompt(
        self, 
        diary_entries: str,
        graph_context: str, 
        chapter_number: int,
        prev_chapter_context: Optional[str] = None
    ) -> dict:
        # Собираем system_prompt из базового и авторского
        system = self.base_config.get("system_prompt", "") + "\n\n" + \
                 self.author_config.get("system_prompt", "")
        
        user_template = self.base_config.get("user_template", "")
        user_prompt = user_template.format(
            diary_entries=diary_entries,
            graph_context=graph_context,
            chapter_number=chapter_number
        )
        
        # Если есть контекст предыдущей главы — добавляем
        if prev_chapter_context:
            context_block = (
                "\n=== ПРЕДЫДУЩАЯ ГЛАВА (продолжи сюжет с этого момента) ===\n"
                f"{prev_chapter_context}\n"
            )
            user_prompt = user_prompt.rstrip() + "\n" + context_block
        
        temperature = self.author_config.get("temperature", self.base_config.get("temperature", 0.85))
        max_tokens = self.author_config.get("max_tokens", self.base_config.get("max_tokens", 3000))
        
        return {
            "system_prompt": system,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }