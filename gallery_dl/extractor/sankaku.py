# Файл: gallery_dl/extractor/sankaku.py
# -*- coding: utf-8 -*-

from .booru import BooruExtractor
from .. import exception
import json

# --- БАЗОВЫЙ КЛАСС С ИСПРАВЛЕННЫМ YIELD ---
class SankakuBase(BooruExtractor):
    def __init__(self, match):
        BooruExtractor.__init__(self, match)

    def _get_post_data(self, post_id, domain, api_domain):
        headers = {'Referer': f'https://{domain}/'}
        try:
            api_url = f'https://{api_domain}/posts/{post_id}'
            response = self.session.get(api_url, headers=headers)
            if response.status_code == 404: raise exception.HttpError(response)
            response.raise_for_status()
            return response.json()
        except exception.HttpError:
            self.log.debug(f'Main API failed for {post_id}, trying /fu')
            try:
                fallback_url = f'https://{api_domain}/posts/{post_id}/fu'
                response = self.session.get(fallback_url, headers=headers)
                response.raise_for_status()
                data = response.json().get('data')
                if data and data.get('file_url'):
                    ext = data['file_url'].partition('?')[0].rpartition('.')[2]
                    data['file_ext'] = ext
                return data
            except Exception as e:
                raise exception.StopExtraction(f'All APIs failed for {post_id}: {e}')

    def items(self):
        post_id = self.match.group(2)
        data = self._get_post_data(post_id, self.domain, self.api_domain)

        if not data or not data.get('file_url'):
            raise exception.StopExtraction(f"No file_url for {post_id}")
        
        # --- ГЛАВНЫЙ ФИКС ЗДЕСЬ ---
        # 1. Собираем всю инфу в один словарь, как раньше
        metadata = {
            "id": data.get('id') or post_id,
            "author": (data.get('author') or {}).get('name'),
            "extension": data.get('file_ext'),
            "_headers": {'Referer': f'https://{self.domain}/'},
        }

        # 2. Генерируем имя файла
        filename = f"{metadata['id']}.{metadata['extension']}"

        # 3. Возвращаем КОРТЕЖ (url, filename, metadata)
        # Именно этого ждет gallery-dl
        yield (data['file_url'], filename, metadata)

# --- КЛАССЫ-НАСЛЕДНИКИ (ОСТАЮТСЯ КАК БЫЛИ) ---
class SankakuPostExtractor(SankakuBase):
    category = "sankaku"
    subcategory = "post"
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'
    
    def __init__(self, match):
        SankakuBase.__init__(self, match)
        
        domain = self.match.group(1)
        if domain == 'idolcomplex.com':
            self.domain = domain
            self.api_domain = 'i.sankakuapi.com'
            self.category = 'idolcomplex'
        else:
            self.domain = domain
            self.api_domain = 'sankakuapi.com'
