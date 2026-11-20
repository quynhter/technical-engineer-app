"""Explicit public origin for NAT/proxies; forwarded headers are never authority."""
from urllib.parse import urlsplit


def public_origin(value):
    if not value:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username is not None
                or url.password is not None or url.path not in ('', '/') or url.query or url.fragment
                or any(c.isspace() for c in value) or not value.isascii()):
            raise ValueError
        port = url.port
        authority = url.netloc.lower()
        if port == {'http': 80, 'https': 443}[url.scheme]:
            authority = authority.rsplit(':', 1)[0]
        return url.scheme + '://' + authority
    except ValueError as error:
        raise ValueError('Укажите внешний адрес --public-origin в виде http(s)://адрес[:порт] без пути') from error


def request_origin(hosts, local_host, scheme, configured=None):
    if configured and hosts == [urlsplit(configured).netloc]:
        return configured
    if hosts == [local_host]:
        return scheme + '://' + local_host
    raise PermissionError('Недопустимый адрес сервера')
