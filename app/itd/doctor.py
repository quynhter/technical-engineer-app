"""Проверки на временных данных, без изменения системного окружения."""
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile


def renderer_path(explicit=None):
    value=explicit or os.environ.get('ITD_LIBREOFFICE')
    if value:
        found=shutil.which(str(value))
        return found or str(Path(value).absolute())
    return shutil.which('soffice') or shutil.which('libreoffice')


def renderer_environment():
    env=os.environ.copy()
    overrides=json.loads(env.get('ITD_RENDER_ENV_JSON','{}'))
    if not isinstance(overrides,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in overrides.items()):
        raise ValueError('ITD_RENDER_ENV_JSON должен быть объектом строк')
    env.update(overrides)
    return env


def convert_docx(source, directory, renderer=None):
    executable=renderer_path(renderer)
    if not executable:
        raise FileNotFoundError('LibreOffice не найден; укажите --renderer или ITD_LIBREOFFICE (в Codex найдите runtime через load_workspace_dependencies)')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='itd-lo-profile-') as profile:
        result=subprocess.run([executable,'-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(directory),str(Path(source).resolve())],
                              capture_output=True,text=True,timeout=45,env=renderer_environment())
    target=directory/(Path(source).stem+'.pdf')
    if result.returncode or not target.is_file():
        message=(result.stdout+'\n'+result.stderr)[-2500:]
        raise RuntimeError(message or 'Конвертер не создал PDF')
    return target


def diagnose(renderer=None):
    from . import __version__
    report={'tool_version':__version__, 'python':sys.version.split()[0],'executable':sys.executable,'platform':platform.platform(),
            'modules':{},'checks':{},'renderer':renderer_path(renderer)}
    for name,distribution in [('docxtpl','docxtpl'),('docx','python-docx'),('pypdf','pypdf'),('openpyxl','openpyxl'),('pymupdf','PyMuPDF')]:
        available=False
        try:
            available=importlib.util.find_spec(name) is not None
            importlib.import_module(name)
            try:
                version=importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                version='unknown'
            report['modules'][name]={'available':available,'import':'ok','version':version}
        except Exception as error:
            report['modules'][name]={'available':available,'import':'failed','error':str(error)}
    def check(name, action):
        try:
            details=action()
            report['checks'][name]={'status':'ready','details':details}
        except Exception as error:
            message=str(error)
            reason='missing_tool' if isinstance(error,(ImportError,FileNotFoundError)) else 'launch_error'
            if any(term in message for term in ('CURL_OPENSSL','error while loading shared libraries','version `','GLIBC_')):
                reason='incompatible_library'
            report['checks'][name]={'status':'unavailable','reason':reason,'error':message}
    with tempfile.TemporaryDirectory(prefix='itd-doctor-') as directory:
        root=Path(directory)
        def sqlite_check():
            with sqlite3.connect(':memory:') as conn:
                conn.execute('CREATE TABLE smoke(value TEXT)')
                conn.execute('INSERT INTO smoke VALUES (?)',('проверка',))
                assert conn.execute('SELECT value FROM smoke').fetchone()[0]=='проверка'
            return sqlite3.sqlite_version
        def docx_check():
            from docx import Document
            from .docx_render import render_docx
            doc=Document();doc.add_paragraph('Проверка {{ value }}');doc.save(root/'template.docx')
            render_docx(root/'template.docx',{'value':'ИТД'},root/'result.docx',draft=True)
            assert Document(root/'result.docx').paragraphs[0].text=='Проверка ИТД'
            return 'DOCX создан, подстановка и повторное чтение проверены'
        def knowledge_check():
            from .knowledge import default_root, build_index, search
            index = root / 'knowledge.db'
            result = build_index(default_root(), index)
            assert search(default_root(), index, 'изоляц')['count'] > 0
            return {'entries': result['entries'], 'fts5': 'ready'}
        def xlsx_check():
            from .statement import _portable_export
            from openpyxl import load_workbook
            payload={'section':'ТЕСТ','object_name':'Проверка','section_label':'Раздел (ТЕСТ)','project_code':'ТЕСТ','rows':[['001','Приборы','Тест','Тип','0007','шт.',0,None,None]]}
            _portable_export(payload,root/'test.xlsx')
            book=load_workbook(root/'test.xlsx');sheet=book.active
            assert sheet['G8'].value==0 and sheet['H8'].value is None and sheet['E8'].value=='0007'
            book.close()
            return 'XLSX создан и прочитан: ноль, NULL, ведущие нули сохранены'
        def pdf_check():
            from pypdf import PdfWriter
            from .readers import read_document
            writer=PdfWriter();writer.add_blank_page(200,200)
            with (root/'test.pdf').open('wb') as handle:writer.write(handle)
            data=read_document(root/'test.pdf')
            assert data['pdf_page_count']==1
            return 'PDF создан и прочитан'
        def pdf_images():
            from .readers import read_document
            if not (root/'test.pdf').exists():
                pdf_check()
            data=read_document(root/'test.pdf',pages='1',dpi=72,scan_dir=root/'images')
            return {'image':Path(data['parts'][0]['image']).name,'dpi':72}
        def conversion():
            if not (root/'result.docx').exists():docx_check()
            pdf=convert_docx(root/'result.docx',root/'pdf',renderer)
            from pypdf import PdfReader
            return {'pages':len(PdfReader(pdf).pages),'executable':report['renderer']}
        for name,action in [('sqlite',sqlite_check),('knowledge_search',knowledge_check),('docx_generate_read',docx_check),('xlsx_generate_read',xlsx_check),('pdf_read',pdf_check),('pdf_images',pdf_images),('docx_to_pdf',conversion)]:
            check(name,action)
    ready=sum(check['status']=='ready' for check in report['checks'].values())
    report['status']='ready' if ready==len(report['checks']) else 'partial' if ready else 'unavailable'
    report['note']='ready — готово; partial — частично доступно; unavailable — недоступно. Конвертация не заменяет визуальную проверку. Windows проверяется отдельно.'
    return report
