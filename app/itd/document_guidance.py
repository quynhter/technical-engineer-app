"""Справочные пояснения стороннего источника; не нормативные проверки."""
import json
from functools import lru_cache

from .paths import ROOT


@lru_cache(maxsize=1)
def example_guidance():
    data = json.loads((ROOT / 'app/reference/id_prosto_examples.json').read_text())
    return {row['form_code']: {'summary': row['summary'], 'url': row['url'],
                              'norm': row['norm'], 'reviewed_on': data['reviewed_on']}
            for row in data['examples'] if row['form_code']}


def guidance_for(code):
    return example_guidance().get(code)
