import os
from config import Config, logger

class GoogleDocsManager:
    def __init__(self):
        self.enabled = False
        self.diary_service = None
        self.novel_service = None
        if not Config.DIARY_DOC_ID or not Config.NOVEL_DOC_ID:
            logger.info("Google Docs отключён (нет ID документов)")
            return
        if not os.path.exists(Config.GOOGLE_CREDENTIALS_FILE):
            logger.warning(f"Файл {Config.GOOGLE_CREDENTIALS_FILE} не найден, Google Docs отключён")
            return
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(
                Config.GOOGLE_CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/documents']
            )
            self.diary_service = build('docs', 'v1', credentials=creds)
            self.novel_service = build('docs', 'v1', credentials=creds)
            self.enabled = True
            logger.info("Google Docs Manager инициализирован (сервисный аккаунт)")
        except Exception as e:
            logger.warning(f"Ошибка инициализации Google Docs: {e}")

    def _get_end_index(self, service, doc_id):
        doc = service.documents().get(documentId=doc_id).execute()
        return doc['body']['content'][-1]['endIndex'] - 1

    def append_diary(self, text, entry_id):
        if not self.enabled:
            return False
        try:
            end_idx = self._get_end_index(self.diary_service, Config.DIARY_DOC_ID)
            self.diary_service.documents().batchUpdate(
                documentId=Config.DIARY_DOC_ID,
                body={'requests': [{'insertText': {'location': {'index': end_idx}, 'text': f"\n[{entry_id}] {text.strip()}\n"}}]}
            ).execute()
            logger.info(f"Запись в дневник: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи в дневник: {e}")
            return False

    def append_novel_chapter(self, chapter_text, footnotes_text, chapter_num):
        if not self.enabled:
            return False
        try:
            end_idx = self._get_end_index(self.novel_service, Config.NOVEL_DOC_ID)
            insertion = f"\n\n{'─'*40}\n ГЛАВА {chapter_num}\n\n{chapter_text.strip()}\n\nПРИМЕЧАНИЯ СЛЕДОВАТЕЛЯ\n{footnotes_text}\n{'─'*40}\n"
            self.novel_service.documents().batchUpdate(
                documentId=Config.NOVEL_DOC_ID,
                body={'requests': [{'insertText': {'location': {'index': end_idx}, 'text': insertion}}]}
            ).execute()
            logger.info(f"Глава {chapter_num} добавлена в Google Docs")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи в роман: {e}")
            return False