from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import Config, logger

class GoogleDocsManager:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            Config.CREDS_FILE, scopes=['https://www.googleapis.com/auth/documents']
        )
        self.diary_service = build('docs', 'v1', credentials=self.creds)
        self.novel_service = build('docs', 'v1', credentials=self.creds)

    def _get_end_index(self, service, doc_id):
        doc = service.documents().get(documentId=doc_id).execute()
        return doc.get('body', {}).get('content', [])[-1].get('endIndex', 1) - 1

    def append_diary(self, text, entry_id):
        try:
            end_idx = self._get_end_index(self.diary_service, Config.DIARY_DOC_ID)
            req = [{'insertText': {'location': {'index': end_idx}, 'text': f"\n[{entry_id}] {text.strip()}\n"}}]
            self.diary_service.documents().batchUpdate(documentId=Config.DIARY_DOC_ID, body={'requests': req}).execute()
            logger.info(f"✅ Дневник: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка дневника: {e}")
            return False

    def append_novel_chapter(self, chapter_text, footnotes_text, chapter_num):
        try:
            end_idx = self._get_end_index(self.novel_service, Config.NOVEL_DOC_ID)
            header = f"\n\n{'─' * 40}\n📘 ГЛАВА {chapter_num}\n\n"
            footer = f"\n\n📖 ПРИМЕЧАНИЯ СЛЕДОВАТЕЛЯ\n{footnotes_text}\n{'─' * 40}\n"
            insertion = header + chapter_text.strip() + "\n" + footer
            req = [{'insertText': {'location': {'index': end_idx}, 'text': insertion}}]
            self.novel_service.documents().batchUpdate(documentId=Config.NOVEL_DOC_ID, body={'requests': req}).execute()
            logger.info(f"📘 Роман: Глава {chapter_num} записана.")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка романа: {e}")
            return False