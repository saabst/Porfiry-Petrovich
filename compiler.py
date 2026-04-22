import asyncio
import os
import re
import aiohttp
from config import Config, logger
from state_manager import StateManager
from docs_manager import GoogleDocsManager
from style_engine import StyleEngine
from image_generator import ImageGenerator
from export_manager import ExportManager
from graph_manager import FactExtractor

class Compiler:
    def __init__(self, docs: GoogleDocsManager, state: StateManager):
        self.docs = docs
        self.state = state
        self.style_engine = StyleEngine(Config.AUTHOR_STYLE)
        self.image_gen = ImageGenerator() if Config.USE_IMAGES else None
        # export_manager теперь использует WeasyPrint (USE_PANDOC игнорируется)
        self.export_mgr = ExportManager(Config.OUTPUT_DIR, use_pandoc=False, pandoc_template="")
        self.fact_extractor = FactExtractor(Config.DEEPSEEK_API_KEY, Config.DEEPSEEK_MODEL) if Config.USE_GRAPH else None
        self._compiling = False

    def _clean_text(self, text: str) -> str:
        """Удаляет XML-теги <chapter>, <footnotes> и лишние пробелы"""
        # Удаляем открывающие и закрывающие теги (с учётом регистра)
        text = re.sub(r'</?chapter>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?footnotes>', '', text, flags=re.IGNORECASE)
        # Убираем множественные пустые строки
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _parse_response(self, content: str):
        """Извлекает текст главы и примечаний, удаляя служебные теги"""
        # Ищем содержимое между тегами
        chapter_match = re.search(r"<chapter>(.*?)</chapter>", content, re.DOTALL | re.IGNORECASE)
        footnotes_match = re.search(r"<footnotes>(.*?)</footnotes>", content, re.DOTALL | re.IGNORECASE)

        if chapter_match:
            chapter_text = chapter_match.group(1).strip()
        else:
            # Если тегов нет, пробуем разделить по ключевому слову "ПРИМЕЧАНИЯ"
            if "ПРИМЕЧАНИЯ" in content:
                parts = re.split(r"(?:ПРИМЕЧАНИЯ|ПРИМЕЧАНИЯ СЛЕДОВАТЕЛЯ)", content, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    chapter_text = parts[0].strip()
                    footnotes_text = parts[1].strip()
                    # Очищаем от возможных остатков тегов
                    chapter_text = self._clean_text(chapter_text)
                    footnotes_text = self._clean_text(footnotes_text)
                    return chapter_text, footnotes_text
            chapter_text = content.strip()

        footnotes_text = footnotes_match.group(1).strip() if footnotes_match else "Без примечаний."

        # Очищаем оба текста от служебных тегов
        chapter_text = self._clean_text(chapter_text)
        footnotes_text = self._clean_text(footnotes_text)

        return chapter_text, footnotes_text

    async def run(self):
        if self._compiling:
            logger.info("Компиляция уже идёт, пропускаю")
            return
        self._compiling = True
        logger.info("🚀 Компилятор запущен")
        try:
            cache = self.state.get_cache()
            if len(cache) < 2:
                logger.info("Кэш пуст, компиляция отменена")
                return

            state = self.state.load_state()
            entries_text = "\n".join([f"[{e['id']}] {e['text']}" for e in cache])
            graph_context = self.state.get_graph_context()
            prompt_data = self.style_engine.build_prompt(entries_text, graph_context, state["chapter_count"])
            logger.info(f"Стиль: {Config.AUTHOR_STYLE}, глава {state['chapter_count']}")

            headers = {"Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": Config.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": prompt_data["system_prompt"]},
                    {"role": "user", "content": prompt_data["user_prompt"]}
                ],
                "temperature": prompt_data["temperature"],
                "max_tokens": prompt_data["max_tokens"]
            }

            raw_content = None
            async with aiohttp.ClientSession() as session:
                for attempt in range(3):
                    try:
                        logger.info(f"Попытка {attempt+1}/3")
                        async with session.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                logger.error(f"Ошибка API: {resp.status} - {text[:500]}")
                                continue
                            data = await resp.json()
                            raw_content = data["choices"][0]["message"]["content"]
                            chapter_text, footnotes_text = self._parse_response(raw_content)
                            if not chapter_text:
                                logger.warning("Не удалось распарсить ответ")
                                continue

                            logger.info("Глава успешно сгенерирована")

                            # 1. Запись в Google Docs (если включён)
                            if self.docs.enabled:
                                self.docs.append_novel_chapter(chapter_text, footnotes_text, state["chapter_count"])

                            # 2. Генерация иллюстрации (если включена)
                            image_path = None
                            if self.image_gen:
                                try:
                                    img_filename = f"chap_{state['chapter_count']}.png"
                                    img_path = await self.image_gen.generate(
                                        chapter_text[:600],
                                        os.path.join(Config.OUTPUT_DIR, "images", img_filename)
                                    )
                                    if img_path:
                                        image_path = img_path
                                        logger.info(f"Иллюстрация сохранена: {image_path}")
                                except Exception as e:
                                    logger.warning(f"Ошибка иллюстрации: {e}")

                            # 3. Добавляем главу в экспортёр (с указанием пути к иллюстрации)
                            self.export_mgr.add_chapter(
                                state["chapter_count"],
                                f"Глава {state['chapter_count']}",
                                chapter_text,
                                image_path   # теперь передаём реальный путь
                            )
                            self.export_mgr.write_markdown()

                            # 4. Извлечение фактов для графа знаний
                            if self.fact_extractor:
                                try:
                                    facts = await self.fact_extractor.extract_facts(chapter_text, state["chapter_count"])
                                    self.state.update_graph_from_facts(facts, state["chapter_count"])
                                except Exception as e:
                                    logger.warning(f"Ошибка графа: {e}")

                            # 5. Обновление состояния (номер главы и очистка кэша)
                            self.state.increment_chapter()
                            self.state.clear_cache()

                            # 6. Генерация PDF (через WeasyPrint, если включено)
                            use_pdf = os.getenv("USE_PDF", "true").lower() == "true"
                            pdf_threshold = int(os.getenv("PDF_AFTER_CHAPTER", "1"))
                            if use_pdf and state["chapter_count"] >= pdf_threshold:
                                try:
                                    pdf_path = self.export_mgr.export_to_pdf()
                                    logger.info(f"PDF создан: {pdf_path}")
                                except Exception as e:
                                    logger.warning(f"Ошибка PDF: {e}")

                            # 7. Речевой маркер (после 10 глав)
                            if state["chapter_count"] >= 10:
                                logger.info("Порфирий Петрович: «Дельце подшито, голубчик!»")

                            logger.info(f"✅ Компиляция главы {state['chapter_count']} завершена")
                            return  # успех, выходим

                    except asyncio.TimeoutError:
                        logger.error(f"Таймаут DeepSeek (попытка {attempt+1})")
                    except Exception as e:
                        logger.exception(f"Ошибка в попытке {attempt+1}: {e}")
                    await asyncio.sleep(5)

            logger.error("Компиляция не удалась после 3 попыток")
            if raw_content:
                with open("debug_response.txt", "w", encoding="utf-8") as f:
                    f.write(raw_content)
        finally:
            self._compiling = False