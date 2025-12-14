# coding: utf-8
from .common import Extractor
from .. import exception

class SankakuPostExtractor(Extractor):
    """
    Специальный экстрактор для отдельных постов Sankaku/IdolComplex.
    Использует /fu API для получения прямой ссылки.
    Должен стоять ПЕРВЫМ в файле, чтобы перехватывать ссылки раньше стандартного экстрактора.
    """
    category = "sankaku"
    subcategory = "post"
    
    # Ловим ссылки на посты sankaku.app и idolcomplex.com
    pattern = r'https?://(?:www\.)?(idolcomplex\.com|sankaku\.app)/posts/(\w+)'

    def __init__(self, match):
        super().__init__(match)
        self.domain = match.group(1)
        self.post_id = match.group(2)

        # Настраиваем домены API в зависимости от сайта
        if self.domain == 'idolcomplex.com':
            self.api_domain = 'i.sankakuapi.com'
            self.category = 'idolcomplex'
        else:
            self.api_domain = 'sankakuapi.com'
            self.category = 'sankaku'

    def items(self):
        # 1. Формируем заголовки. Без Referer и User-Agent сервер вернет 403.
        base_url = f'https://{self.domain}/'
        headers = {
            'Referer': base_url,
            'Origin': base_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # 2. Формируем URL для "fallback" API (/fu), который часто работает лучше основного
        api_url = f'https://{self.api_domain}/posts/{self.post_id}/fu'
        
        self.log.debug(f'Force-using fallback API: {api_url}')

        try:
            # self.request() - встроенный метод gallery-dl.
            # Он обрабатывает ошибки сети, прокси и куки.
            response = self.request(api_url, headers=headers)
            json_data = response.json()
            
            # Бывает, что данные лежат сразу в корне, а бывает в поле 'data' (зависит от версии API)
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

        # 3. Определяем расширение файла
        # Сначала пробуем из JSON, если нет — выдираем из URL
        ext = data.get('file_ext') or data.get('extension')
        if not ext:
            # file.jpg?k=... -> file.jpg -> jpg
            ext = file_url.partition('?')[0].rpartition('.')[2] or 'jpg'

        # Sankaku иногда возвращает null в file_url для удаленных картинок, но preview_url есть
        if 's.sankakucomplex.com/data/preview' in file_url:
             self.log.warning("Original file deleted, only preview available. Skipping.")
             return

        file_id = str(data.get('id') or self.post_id)
        
        # Имя файла для сохранения
        filename = f"{file_id}.{ext}"

        # 4. Собираем теги для метаданных (необязательно, но полезно)
        tags = []
        if 'tags' in data and isinstance(data['tags'], list):
            # API может возвращать теги как список словарей или строк
            for t in data['tags']:
                if isinstance(t, dict):
                    tags.append(t.get('name_en') or t.get('name') or '')
                elif isinstance(t, str):
                    tags.append(t)

        # 5. ВОЗВРАЩАЕМ ДАННЫЕ (YIELD)
        yield {
            "url": file_url,           # Прямая ссылка для скачивания
            "filename": filename,      # Имя файла
            "extension": ext,
            "id": file_id,
            "directory": [self.category], # Папка: sankaku/
            
            # Метаданные
            "width": data.get("width"),
            "height": data.get("height"),
            "rating": data.get("rating"),
            "tags": tags,
            "created_at": data.get("created_at"),
            
            # !!! ОЧЕНЬ ВАЖНО !!!
            "_headers": headers 
        }
