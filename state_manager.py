import json
import os
from config import Config, logger

class StateManager:
    def __init__(self, state_file="story_state.json", cache_file="diary_cache.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.state_file = os.path.join(base_dir, state_file)
        self.cache_file = os.path.join(base_dir, cache_file)
        
        if not os.path.exists(self.state_file):
            self._save_state({
                "phase": "OBSERVE",
                "chapter_count": 1,
                "convergence_score": 0.0,
                "entries_count": 0,
                "themes_seen": [],
                "last_compile_at": 0
            })
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False)

    def load_state(self):
        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_state(self, state):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def add_entry(self, text, themes=None):
        state = self.load_state()
        state["entries_count"] += 1
        
        # Добавляем в кэш
        cache = self.get_diary_cache()
        entry_id = f"L{state['chapter_count']:03d}-{state['entries_count']:03d}"
        cache.append({"id": entry_id, "text": text, "themes": themes or []})
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)

        # Обновляем конвергенцию по темам
        if themes:
            for t in themes:
                if t in state.get("themes_seen", []):
                    state["convergence_score"] = min(1.0, state["convergence_score"] + 0.05)
            state.setdefault("themes_seen", []).extend(themes)
        
        self._save_state(state)

        # Проверка порога: И по количеству, И по конвергенции, И не чаще чем раз в 60 сек
        import time
        time_since_compile = time.time() - state.get("last_compile_at", 0)
        threshold_reached = (
            state["entries_count"] >= Config.COMPILE_THRESHOLD or
            state["convergence_score"] >= 0.9
        ) and time_since_compile > 60

        if threshold_reached:
            state["last_compile_at"] = time.time()
            self._save_state(state)
            return True
        return False

    def get_diary_cache(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def clear_cache(self):
        """Очищает кэш и сбрасывает счётчик после успешной компиляции."""
        state = self.load_state()
        state["entries_count"] = 0
        self._save_state(state)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)
        logger.info("📦 Кэш дневника очищён после компиляции.")