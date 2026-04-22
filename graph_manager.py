import json
import networkx as nx
import os
from typing import List, Dict, Any
import asyncio
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    def __init__(self, storage_path: str = "knowledge_graph.json"):
        self.storage_path = storage_path
        self.graph = nx.DiGraph()
        self.load()
    
    def load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.graph = nx.node_link_graph(data)
        else:
            self.graph = nx.DiGraph()
    
    def save(self):
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_fact(self, subject: str, predicate: str, obj: str, chapter: int):
        # Фильтрация мусора
        stop_words = {"я", "меня", "мне", "ты", "он", "она", "оно", "мы", "вы", "они",
                      "это", "то", "так", "вот", "тут", "там", "здесь", "кто", "что",
                      "как", "без", "для", "на", "по", "с", "у", "же", "ли", "бы", "не"}
        
        # Пропускаем слишком короткие или слишком длинные узлы
        if len(subject) < 2 or len(obj) < 2:
            return
        if len(subject) > 50 or len(obj) > 50:
            return
        # Пропускаем стоп-слова
        if subject.lower() in stop_words or obj.lower() in stop_words:
            return
        # Пропускаем узлы, начинающиеся со строчной буквы (кроме известных понятий)
        if subject[0].islower() and subject not in ["демиург", "следователь", "порфирий"]:
            return
        if subject == obj:
            return
        
        self.graph.add_node(subject, type="entity")
        self.graph.add_node(obj, type="entity")
        self.graph.add_edge(subject, obj, label=predicate, chapter=chapter)
    
    def get_context_string(self) -> str:
        if self.graph.number_of_edges() == 0:
            return "Пока нет известных фактов."
        lines = []
        for u, v, data in self.graph.edges(data=True):
            lines.append(f"- {u} {data.get('label', 'связан с')} {v} (глава {data.get('chapter', '?')})")
        return "\n".join(lines[:30])
    
    def visualize(self, output_path: str = "graph_viz.html"):
        try:
            from pyvis.network import Network
            net = Network(height="750px", width="100%", directed=True)
            net.from_nx(self.graph)
            net.show(output_path, notebook=False)
            logger.info(f"Граф визуализирован в {output_path}")
        except Exception as e:
            logger.warning(f"Не удалось создать HTML-граф: {e}")
            try:
                nx.write_graphml(self.graph, output_path.replace('.html', '.graphml'))
                logger.info(f"Граф сохранён в GraphML: {output_path.replace('.html', '.graphml')}")
            except:
                pass

class FactExtractor:
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        self.model = model
    
    async def extract_facts(self, chapter_text: str, chapter_number: int) -> List[Dict[str, str]]:
        prompt = f"""
Ты — архивариус. Извлеки из текста главы **только важные факты** в формате (субъект, отношение, объект).

Правила:
- Субъект и объект — конкретные сущности: имена персонажей, названия локаций, ключевые предметы, важные понятия (не целые фразы).
- Отношение — глагол или краткая связка (например, «убил», «находится в», «использует»).
- Не извлекай обрывки предложений, местоимения («он», «она», «мне»), цитаты, фразы из 1-2 слов.
- Ограничься 3-5 фактами на главу. Если фактов меньше — ничего страшного.

Глава {chapter_number}:
{chapter_text[:3000]}

Ответ дай в формате JSON: {{"facts": [{{"subject": "...", "predicate": "...", "object": "..."}}]}}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("facts", [])