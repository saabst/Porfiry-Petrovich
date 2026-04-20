import requests
import re
import time
from config import Config, logger
from state_manager import StateManager
from docs_manager import GoogleDocsManager

PROMPT = """[SYSTEM]
Ты — Порфирий Петрович. Твои сырые записи накопились. Сформируй главу и примечания.
ВХОД: {entries}

ЗАДАЧА:
1. Напиши главу (800-1200 слов). Тон: циничный, метафизический, ранний Пелевин.
2. В конце добавь блок ПРИМЕЧАНИЙ с 4-6 выводами, каждый с указанием ID записи [Lxxx].

КРИТИЧЕСКИ ВАЖНО — ФОРМАТ ВЫВОДА:
Твой ответ ДОЛЖЕН начинаться с <CHAPTER> и заканчиваться </FOOTNOTES>.
Никакого вступительного текста, никаких объяснений ДО или ПОСЛЕ этих тегов.

Пример структуры:
<CHAPTER>Текст главы здесь...</CHAPTER>
<FOOTNOTES>
[L001-001]: Пояснение...
[L001-005]: Пояснение...
</FOOTNOTES>

Начни ответ ПРЯМО с <CHAPTER>.
"""

class Compiler:
    def __init__(self, docs: GoogleDocsManager, state: StateManager):
        self.docs = docs
        self.state = state
        self._compiling = False

    def _parse_response(self, content: str):
        """Гибкий парсер: ищет теги, потом фоллбэк по ключевым словам."""
        # Попытка 1: строгие теги
        chapter = re.search(r"<CHAPTER>(.*?)</CHAPTER>", content, re.DOTALL | re.IGNORECASE)
        footnotes = re.search(r"<FOOTNOTES>(.*?)</FOOTNOTES>", content, re.DOTALL | re.IGNORECASE)
        
        if chapter and footnotes:
            return chapter.group(1).strip(), footnotes.group(1).strip()
        
        # Попытка 2: теги без слешей или с пробелами
        chapter = re.search(r"<CHAPTER>(.*?)(?:</CHAPTER>|<FOOTNOTES>|ПРИМЕЧАНИЯ)", content, re.DOTALL | re.IGNORECASE)
        footnotes = re.search(r"(?:<FOOTNOTES>|ПРИМЕЧАНИЯ.*?)(.*?)(?:</FOOTNOTES>|$)", content, re.DOTALL | re.IGNORECASE)
        
        if chapter and footnotes and len(footnotes.group(1).strip()) > 50:
            logger.warning("⚠️ Использован фоллбэк-парсер (теги неидеальны)")
            return chapter.group(1).strip(), footnotes.group(1).strip()
        
        # Попытка 3: эвристика по ключевым словам
        if "ПРИМЕЧАНИЯ" in content or "footnotes" in content.lower():
            parts = re.split(r"(?:ПРИМЕЧАНИЯ|ПРИМЕЧАНИЯ СЛЕДОВАТЕЛЯ|<FOOTNOTES|footnotes)", content, flags=re.IGNORECASE)
            if len(parts) >= 2:
                logger.warning("⚠️ Использован эвристический парсер (разделение по ключевым словам)")
                return parts[0].strip(), parts[1].strip()
        
        return None, None

    def run(self):
        if self._compiling:
            logger.info("⏳ Компиляция уже идёт, пропускаю дубликат.")
            return
        self._compiling = True

        try:
            cache = self.state.get_diary_cache()
            if len(cache) < 2:
                logger.info("ℹ️ Кэш пуст, компиляция отменена.")
                return

            state = self.state.load_state()
            entries_text = "\n".join([f"[{e['id']}] {e['text']}" for e in cache])
            prompt = PROMPT.format(entries=entries_text)

            headers = {
                "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔍 Запуск компилятора (попытка {attempt+1}/{max_retries})...")
                    payload = {
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "Отвечай ТОЛЬКО в формате <CHAPTER>...</CHAPTER><FOOTNOTES>...</FOOTNOTES>. Никакого лишнего текста."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,  # Ниже = строже формат
                        "max_tokens": 2200
                    }

                    res = requests.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120
                    )
                    res.raise_for_status()
                    raw_content = res.json()["choices"][0]["message"]["content"]
                    
                    # 🔍 ОТЛАДКА: пишем сырой ответ в лог
                    logger.debug(f"📦 RAW DeepSeek response (first 500 chars):\n{raw_content[:500]}...")
                    
                    chapter_text, footnotes_text = self._parse_response(raw_content)
                    
                    if chapter_text and footnotes_text:
                        logger.info("✅ Парсинг успешен. Запись в роман...")
                        success = self.docs.append_novel_chapter(chapter_text, footnotes_text, state["chapter_count"])
                        
                        if success:
                            state["chapter_count"] += 1
                            state["convergence_score"] = 0.0
                            self.state._save_state(state)
                            self.state.clear_cache()
                            logger.info(f"📘 Глава {state['chapter_count']-1} успешно записана в роман.")
                            return
                        else:
                            logger.error("❌ Ошибка записи в Google Docs. Проверь права доступа к NOVEL_DOC_ID.")
                    else:
                        logger.warning(f"⚠️ Не удалось распарсить ответ. Сырой контент:\n{raw_content[:800]}")
                        time.sleep(10)

                except requests.exceptions.Timeout:
                    logger.warning(f"⏱ Таймаут DeepSeek (попытка {attempt+1}). Жду {2**attempt * 5} сек...")
                    time.sleep(2**attempt * 5)
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ Ошибка сети (попытка {attempt+1}): {e}")
                    time.sleep(2**attempt * 5)

            logger.error("❌ Все попытки компиляции исчерпаны. Кэш сохранён.")
            # Сохраняем сырой ответ в файл для ручной отладки
            with open("debug_last_response.txt", "w", encoding="utf-8") as f:
                f.write(raw_content if 'raw_content' in locals() else "No response received")
            logger.info("📁 Сырой ответ сохранён в debug_last_response.txt")

        except Exception as e:
            import traceback
            logger.error(f"❌ Неожиданная ошибка компилятора:\n{traceback.format_exc()}")
        finally:
            self._compiling = False