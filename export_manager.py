import os
import markdown
from weasyprint import HTML, CSS
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExportManager:
    def __init__(self, output_dir: str = "output", use_pandoc: bool = True, pandoc_template: str = ""):
        # use_pandoc и pandoc_template игнорируются, оставлены для совместимости
        self.output_dir = output_dir
        self.markdown_path = os.path.join(output_dir, "book.md")
        self.images_dir = os.path.join(output_dir, "images")
        self.chapters = []
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def add_chapter(self, chapter_number: int, title: str, content: str, image_path: Optional[str] = None):
        self.chapters.append((chapter_number, title, content, image_path))
    
    def write_markdown(self):
        with open(self.markdown_path, 'w', encoding='utf-8') as f:
            f.write(f"# {self._get_book_title()}\n\n")
            for num, title, content, img in self.chapters:
                f.write(f"## Глава {num}: {title}\n\n")
                if img and os.path.exists(img):
                    # относительный путь от output_dir
                    rel_img = os.path.relpath(img, self.output_dir)
                    f.write(f"![Иллюстрация]({rel_img})\n\n")
                f.write(content)
                f.write("\n\n---\n\n")
        return self.markdown_path
    
    def export_to_pdf(self) -> str:
        """Генерация PDF через WeasyPrint"""
        if not os.path.exists(self.markdown_path):
            raise FileNotFoundError(f"Markdown файл {self.markdown_path} не найден")
        
        # Читаем Markdown
        with open(self.markdown_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        # Конвертируем Markdown в HTML
        html_body = markdown.markdown(md_text, extensions=['extra'])
        
        # Загружаем CSS (если есть)
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            css = CSS(filename=css_path)
        else:
            # минимальный встроенный CSS
            css = CSS(string=self._default_css())
        
        # Формируем полный HTML-документ
        html_doc = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Дело Порфирия Петровича</title>
</head>
<body>
{html_body}
</body>
</html>"""
        
        pdf_path = os.path.join(self.output_dir, "book.pdf")
        try:
            HTML(string=html_doc, base_url=self.output_dir).write_pdf(pdf_path, stylesheets=[css])
            logger.info(f"PDF успешно создан: {pdf_path}")
            return pdf_path
        except Exception as e:
            logger.error(f"Ошибка WeasyPrint: {e}")
            raise
    
    def _default_css(self) -> str:
        return """
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Дело Порфирия Петровича";
                font-family: sans-serif;
                font-size: 10pt;
            }
            @bottom-center {
                content: counter(page);
                font-family: sans-serif;
                font-size: 10pt;
            }
        }
        body {
            font-family: 'DejaVu Serif', 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.4;
        }
        h1 {
            font-size: 24pt;
            text-align: center;
            margin-top: 4cm;
        }
        h2 {
            font-size: 18pt;
            margin-top: 2cm;
        }
        img {
            max-width: 80%;
            display: block;
            margin: 1em auto;
        }
        """
    
    def _get_book_title(self):
        return f"Дело Порфирия Петровича (завершено {datetime.now().strftime('%Y-%m-%d')})"