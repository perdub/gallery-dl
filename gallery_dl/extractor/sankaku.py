# Файл: gallery_dl/extractor/sankaku.py
# -*- coding: utf-8 -*-

from .booru import BooruExtractor
from .. import exception
import json

# --- БАЗОВЫЙ КЛАСС С НОВОЙ ЛОГИКОЙ API ---
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
                # Добавляем file_ext, так как в /fu его нет
                if data and data.get('file_url'):
                    ext = data['file_url'].partition('?')[0].rpartition('.')[2]
                    data['file_ext'] = ext
                return data
            except Exception as e:
                raise exception.StopExtraction(f'All APIs failed for {post_id}: {e}')

    def items(self):
        post_id = self.match.group(2) # Теперь ID - это вторая группа в регулярке
        data = self._get_post_data(post_id, self.domain, self.api_domain)

        if not data or not data.get('file_url'):
            raise exception.StopExtraction(f"No file_url for {post_id}")
            
        yield {
            "src": data['file_url'],
            "id": data.get('id') or post_id,
            "author": (data.get('author') or {}).get('name'),
            "extension": data.get('file_ext'),
            "filename": f"{data.get('id') or post_id}.{data.get('file_ext')}",
            "_headers": {'Referer': f'https://{self.domain}/'},
        }

# --- КЛАСС ДЛЯ SANKAKU.APP И IDOLCOMPLEX (ОДИН НА ВСЕХ) ---
class SankakuPostExtractor(SankakuBase):
    category = "sankaku"
    subcategory = "post"
    # Регулярка теперь ловит домен в первую группу, а ID - во вторую
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'
    
    def __init__(self, match):
        SankakuBase.__init__(self, match)
        
        domain = self.match.group(1)
        if domain == 'idolcomplex.com':
            self.domain = domain
            self.api_domain = 'i.sankakuapi.com'
            # Важно: меняем категорию для idolcomplex, чтобы файлы не смешивались
            self.category = 'idolcomplex'
        else:
            self.domain = domain
            self.api_domain = 'sankakuapi.com'

# Остальные классы (SankakuTagExtractor, Pool и т.д.) нужно либо удалить,
# либо оставить как есть, если они тебе нужны. Для постов хватит этого.