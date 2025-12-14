# Файл: gallery_dl/extractor/sankaku.py
# -*- coding: utf-8 -*-
# ПОСЛЕДНЯЯ ВЕРСИЯ. С ИСПРАВЛЕННЫМ TRY/EXCEPT.

from .booru import BooruExtractor
from .. import exception
import json

class SankakuPostExtractor(BooruExtractor):
    category = "sankaku"
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

    def _get_post_data(self, post_id):
        headers = {'Referer': f'https://{self.domain}/'}
        try:
            # --- ПОПЫТКА №1 ---
            api_url = f'https://{self.api_domain}/posts/{post_id}'
            self.log.debug(f'Trying main API: {api_url}')
            response = self.session.get(api_url, headers=headers)
            
            # raise_for_status() САМ кинет ошибку HttpError, если статус 404
            response.raise_for_status() 
            return response.json()

        except exception.HttpError as e:
            # --- ПЕРЕХОД К ЗАПАСНОМУ API ---
            # Проверяем, что ошибка была именно 404
            if e.response and e.response.status_code == 404:
                self.log.debug(f'Main API failed with 404 for {post_id}, trying /fu')
                try:
                    fallback_url = f'https://{self.api_domain}/posts/{post_id}/fu'
                    response = self.session.get(fallback_url, headers=headers)
                    response.raise_for_status()
                    return response.json().get('data')
                except Exception as fallback_e:
                    raise exception.StopExtraction(f'All APIs failed for {post_id}: {fallback_e}')
            else:
                # Если была другая ошибка (500, 403) - просто падаем
                raise

    def items(self):
        post_id = self.match.group(2)
        data = self._get_post_data(post_id)

        if not data or not data.get('file_url'):
            return

        file_url = data['file_url']
        ext = data.get('file_ext') or file_url.partition('?')[0].rpartition('.')[2] or 'unknown'
        file_id = data.get('id') or post_id
        
        metadata = {
            "id": file_id, "author": (data.get('author') or {}).get('name'),
            "extension": ext, "_headers": {'Referer': f'https://{self.domain}/'},
        }
        filename = f"{file_id}.{ext}"

        yield (file_url, filename, metadata)
