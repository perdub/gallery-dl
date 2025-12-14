# Файл: gallery_dl/extractor/sankaku.py
# -*- coding: utf-8 -*-
# ВЕРСИЯ, КОТОРАЯ ХОДИТ ТОЛЬКО НА РАБОЧИЙ /fu ЭНДПОИНТ

from .booru import BooruExtractor
from .. import exception
import json

class SankakuPostExtractor(BooruExtractor):
    category = "sankaku"
    # Регулярка ловит оба сайта
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'
    
    def __init__(self, match):
        super().__init__(match)
        domain = self.match.group(1)
        if domain == 'idolcomplex.com':
            self.domain = domain
            self.api_domain = 'i.sankakuapi.com'
            self.category = 'idolcomplex'
        else:
            self.domain = domain
            self.api_domain = 'sankakuapi.com'

    # Главный метод
    def items(self):
        post_id = self.match.group(2)
        headers = {'Referer': f'https://{self.domain}/'}

        # --- ИДЕМ СРАЗУ НА /fu ---
        try:
            api_url = f'https://{self.api_domain}/posts/{post_id}/fu'
            self.log.debug(f'Force-using fallback API: {api_url}')
            response = self.session.get(api_url, headers=headers)
            response.raise_for_status() # Если тут ошибка, значит пост реально не существует
            data = response.json().get('data')
        except Exception as e:
            raise exception.StopExtraction(f'Failed to fetch from /fu API for {post_id}: {e}')

        if not data or not data.get('file_url'):
            return

        file_url = data['file_url']
        ext = data.get('file_ext') or file_url.partition('?')[0].rpartition('.')[2] or 'unknown'
        file_id = data.get('id') or post_id
        
        metadata = {
            "id": file_id,
            "extension": ext,
            "_headers": headers,
        }
        filename = f"{file_id}.{ext}"

        yield (file_url, filename, metadata)
