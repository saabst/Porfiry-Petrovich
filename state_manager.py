import json
import os
import time
from config import Config, logger
from graph_manager import KnowledgeGraph

class StateManager:
    def __init__(self):
        base = os.path.dirname(os.path.abspath(__file__))
        self.state_file = os.path.join(base, "story_state.json")
        self.cache_file = os.path.join(base, "diary_cache.json")
        self.graph = KnowledgeGraph() if Config.USE_GRAPH else None
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.state_file):
            self._save_state({"phase": "OBSERVE", "chapter_count": 1, "convergence_score": 0.0,
                              "entries_count": 0, "themes_seen": [], "last_compile_at": 0})
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def load_state(self):
        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_state(self, state):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

    def add_entry(self, text, themes=None):
        state = self.load_state()
        state["entries_count"] += 1
        cache = self.get_cache()
        entry_id = f"L{state['chapter_count']:03d}-{state['entries_count']:03d}"
        cache.append({"id": entry_id, "text": text, "themes": themes or []})
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)

        if themes:
            for t in themes:
                if t in state.get("themes_seen", []):
                    state["convergence_score"] = min(1.0, state["convergence_score"] + 0.05)
            state.setdefault("themes_seen", []).extend(themes)

        self._save_state(state)

        time_since = time.time() - state.get("last_compile_at", 0)
        if (state["entries_count"] >= Config.COMPILE_THRESHOLD or state["convergence_score"] >= 0.9) and time_since > 60:
            state["last_compile_at"] = time.time()
            self._save_state(state)
            return True
        return False

    def get_cache(self):
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def clear_cache(self):
        state = self.load_state()
        state["entries_count"] = 0
        self._save_state(state)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info("Кэш дневника очищен")

    def increment_chapter(self):
        state = self.load_state()
        state["chapter_count"] += 1
        state["convergence_score"] = 0.0
        self._save_state(state)

    def get_graph_context(self):
        if self.graph:
            return self.graph.get_context_string()
        return ""

    def update_graph_from_facts(self, facts, chapter_num):
        if self.graph and facts:
            for fact in facts:
                self.graph.add_fact(fact["subject"], fact["predicate"], fact["object"], chapter_num)
            self.graph.save()
            self.graph.visualize(os.path.join(Config.OUTPUT_DIR, "graph_viz.html"))