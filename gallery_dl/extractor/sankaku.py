# coding: utf-8
from .common import Extractor, Message
from .. import exception

class SankakuPostExtractor(Extractor):
    """
    Специальный экстрактор для отдельных постов Sankaku/IdolComplex.
    Использует /fu API для получения прямой ссылки.
    Должен стоять ПЕРВЫМ в файле.
    """
    category = "sankaku"
    subcategory = "post"
    
    # Ловим ссылки на посты sankaku.app и idolcomplex.com
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'

    def __init__(self, match):
        super().__init__(match)
        self.domain = match.group(1)
        self.post_id = match.group(2)

        if self.domain == 'idolcomplex.com':
            self.api_domain = 'i.sankakuapi.com'
            self.category = 'idolcomplex'
        else:
            self.api_domain = 'sankakuapi.com'
            self.category = 'sankaku'

    def items(self):
        # 1. Заголовки для API
        base_url = f'https://{self.domain}/'
        headers = {
            'Referer': base_url,
            'Origin': base_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # 2. API URL
        api_url = f'https://{self.api_domain}/posts/{self.post_id}/fu'
        
        self.log.debug(f'Force-using fallback API: {api_url}')

        try:
            response = self.request(api_url, headers=headers)
            json_data = response.json()
            data = json_data.get('data') if 'data' in json_data else json_data
            
        except exception.HttpError as e:
            if e.code == 404:
                self.log.error(f"Post {self.post_id} not found (404).")
                return
            raise exception.StopExtraction(f'API Error: {e}')
        except Exception as e:
            raise exception.StopExtraction(f'Failed to fetch/parse API: {e}')

        if not data or not data.get('file_url'):
            self.log.warning(f"No file URL found for post {self.post_id}")
            return

        file_url = data['file_url']

        # 3. Данные файла
        ext = data.get('file_ext') or data.get('extension')
        if not ext:
            ext = file_url.partition('?')[0].rpartition('.')[2] or 'jpg'

        if 's.sankakucomplex.com/data/preview' in file_url:
             self.log.warning("Original file deleted, only preview available. Skipping.")
             return

        file_id = str(data.get('id') or self.post_id)
        filename = f"{file_id}.{ext}"

        tags = []
        if 'tags' in data and isinstance(data['tags'], list):
            for t in data['tags']:
                if isinstance(t, dict):
                    tags.append(t.get('name_en') or t.get('name') or '')
                elif isinstance(t, str):
                    tags.append(t)

        # 4. Формируем словарь метаданных
        post_data = {
            "url": file_url,
            "filename": filename,
            "extension": ext,
            "id": file_id,
            "width": data.get("width"),
            "height": data.get("height"),
            "rating": data.get("rating"),
            "tags": tags,
            "created_at": data.get("created_at"),
            "_headers": headers 
        }

        # 5. ВАЖНО: Возвращаем кортежи (Тип, URL, Данные)
        
        # Сначала сообщаем папку/метаданные галереи (для формирования пути)
        yield Message.Directory, "", post_data
        
        # Затем сообщаем сам файл для скачивания
        yield Message.Url, file_url, post_data

# Ниже должен идти оригинальный класс SankakuExtractor, если он там был,
# но твой класс должен быть объявлен РАНЬШЕ него.
