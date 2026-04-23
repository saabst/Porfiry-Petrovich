import aiohttp
import asyncio
import os
import re
from typing import Optional

class ImageGenerator:
    def __init__(self, provider: str = "pollinations", width: int = 1024, height: int = 1024):
        self.provider = provider
        self.width = width
        self.height = height
    
    def _extract_keywords(self, text: str, max_words: int = 30) -> str:
        """Извлекает ключевые образы из текста главы"""
        # Убираем примечания и заголовки
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        
        # Ищем предложения с визуальными образами
        visual_cues = [
            'комнат', 'улиц', 'неб', 'свет', 'тьм', 'окн', 'двер',
            'лиц', 'глаз', 'рук', 'город', 'дом', 'стен', 'пол',
            'стол', 'кресл', 'камин', 'туман', 'дожд', 'снег',
            'темн', 'ярк', 'син', 'красн', 'черн', 'бел', 
            'цифр', 'экран', 'монитор', 'код', 'матриц',
            'тень', 'призрак', 'монстр', 'существ',
            'Петербург', 'Москв', 'Бейкер'
        ]
        
        sentences = text.split('.')
        visual_sentences = []
        
        for sent in sentences:
            sent = sent.strip()
            if any(cue in sent.lower() for cue in visual_cues) and len(sent) > 10:
                visual_sentences.append(sent)
        
        # Если нашли визуальные предложения, берём их
        if visual_sentences:
            result = ' '.join(visual_sentences[:5])
        else:
            # Иначе первые предложения текста
            result = ' '.join(sentences[:5])
        
        words = result.split()
        return ' '.join(words[:max_words])
    
    def _build_prompt(self, text: str, style: str = "pelevin") -> str:
        """Строит промпт для Pollinations на основе текста и стиля"""
        keywords = self._extract_keywords(text)
        
        # Определяем стиль рисунка
        if style == "pelevin":
            style_desc = "digital art, cyberpunk aesthetic, neon colors on dark background, glitch effects, abstract, metaphysical, vaporwave, 4k"
        elif style == "dostoevsky":
            style_desc = "oil painting, dark romanticism, 19th century St. Petersburg, dramatic chiaroscuro, moody atmosphere, Fyodor Dostoevsky illustration, somber tones"
        elif style == "holmes":
            style_desc = "Victorian illustration, Sherlock Holmes style, foggy London, sepia tones, detailed line art, gaslight atmosphere, vintage detective novel cover"
        else:
            style_desc = "cinematic, dramatic lighting, detailed, atmospheric, illustration"
        
        prompt = f"{keywords}, {style_desc}"
        return prompt[:400]  # Ограничиваем длину промпта
    
    async def generate(self, prompt: str, output_path: str, style: str = "pelevin") -> Optional[str]:
        if self.provider != "pollinations":
            return None
        
        # Строим осмысленный промпт из текста главы
        image_prompt = self._build_prompt(prompt, style)
        safe_prompt = image_prompt.replace(" ", "%20").replace(",", "%2C")
        
        # Используем разные размеры в зависимости от стиля
        if style == "pelevin":
            width, height = 1024, 768  # Широкоформатный для киберпанка
        elif style == "dostoevsky":
            width, height = 768, 1024  # Портретный для портретов и атмосферы
        else:
            width, height = self.width, self.height
        
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(await resp.read())
                        return output_path
                    else:
                        print(f"Image generation failed: {resp.status}")
                        return None
        except Exception as e:
            print(f"Image error: {e}")
            return None