# http_client.py
import requests
from typing import Optional


class HttpClient:
    @staticmethod
    def get_http_client(proxy: Optional[str] = None, timeout: int = 5) -> requests.Session:
        session = requests.Session()
        session.timeout = timeout

        if proxy:
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
        return session

    @staticmethod
    def get_mobile_request(proxy: Optional[str] = None) -> requests.Session:
        session = HttpClient.get_http_client(proxy)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'
        })
        return session