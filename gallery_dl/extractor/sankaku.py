# Файл: gallery_dl/extractor/sankaku.py
# -*- coding: utf-8 -*-
# ПОЛНОСТЬЮ ПЕРЕПИСАННЫЙ ЭКСТРАКТОР ДЛЯ SANKAKU / IDOLCOMPLEX

from .booru import BooruExtractor
from .. import exception
import json

class SankakuPostExtractor(BooruExtractor):
    """
    Универсальный экстрактор для постов с idolcomplex.com и sankaku.app.
    Использует новый API и умеет переключаться на запасной (/fu).
    """
    category = "sankaku"
    # Регулярка, которая ловит ОБА домена. Домен - 1-я группа, ID - 2-я.
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'
    
    # Конструктор. Вызывается gallery-dl, когда находит подходящую ссылку.
    def __init__(self, match):
        super().__init__(match) # Обязательный вызов родителя
        
        # Определяем, с какого сайта пришла ссылка, и настраиваем переменные
        domain = self.match.group(1)
        if domain == 'idolcomplex.com':
            self.domain = domain
            self.api_domain = 'i.sankakuapi.com'
            self.category = 'idolcomplex' # Чтобы файлы сохранялись в папку idolcomplex
        else: # sankaku.app
            self.domain = domain
            self.api_domain = 'sankakuapi.com'
            self.category = 'sankaku'

    # Вспомогательный метод для похода в API
    def _get_post_data(self, post_id):
        headers = {
            'Referer': f'https://{self.domain}/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            # Попытка №1: Основной API
            api_url = f'https://{self.api_domain}/posts/{post_id}'
            self.log.debug(f'Trying main API: {api_url}')
            response = self.session.get(api_url, headers=headers)
            if response.status_code == 404:
                raise exception.HttpError(response) # Принудительно вызываем except
            response.raise_for_status()
            return response.json()
        except exception.HttpError as e:
            # Если словили 404, пробуем запасной. Иначе - падаем.
            if e.response and e.response.status_code == 404:
                self.log.debug(f'Main API failed for {post_id}, trying /fu')
                try:
                    # Попытка №2: Запасной API
                    fallback_url = f'https://{self.api_domain}/posts/{post_id}/fu'
                    self.log.debug(f'Trying fallback API: {fallback_url}')
                    response = self.session.get(fallback_url, headers=headers)
                    response.raise_for_status()
                    return response.json().get('data') # Ответ от /fu вложен в 'data'
                except Exception as fallback_e:
                    raise exception.StopExtraction(f'All APIs failed for {post_id}: {fallback_e}')
            else:
                raise

    # Главный метод, который отдает файлы gallery-dl
    def items(self):
        # ID поста - это вторая группа из нашей регулярки
        post_id = self.match.group(2)
        
        data = self._get_post_data(post_id)

        if not data or not data.get('file_url'):
            self.log.error(f"No file_url found for post {post_id}")
            return

        file_url = data['file_url']
        
        # Надежно получаем расширение и ID, даже если API вернул мало данных
        ext = data.get('file_ext') or file_url.partition('?')[0].rpartition('.')[2] or 'unknown'
        file_id = data.get('id') or post_id
        
        metadata = {
            "id": file_id,
            "author": (data.get('author') or {}).get('name'),
            "extension": ext,
            "_headers": {'Referer': f'https://{self.domain}/'},
        }

        filename = f"{file_id}.{ext}"

        # ФИНАЛЬНЫЙ ФИКС: Возвращаем кортеж (url, имя_файла, метаданные)
        self.log.debug(f"Yielding file: {filename} from URL: {file_url}")
        yield (file_url, filename, metadata)

# --- ВАЖНО: УДАЛИ ВСЕ ОСТАЛЬНЫЕ КЛАССЫ ИЗ ЭТОГО ФАЙЛА ---
# Оставь только класс SankakuPostExtractor.
