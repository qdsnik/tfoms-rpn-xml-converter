from __future__ import annotations
from pathlib import Path
from lxml import etree
import argparse
import sys
from datetime import datetime


# Код МО из F032
CODE_MO = '352530'


def init() -> argparse.ArgumentParser:
    """Возвращает объект для разбора входных параметров."""
    parser = argparse.ArgumentParser()

    parser.add_argument('file', type=str, help='xml file for handling')

    return parser


def remove_node(parent, name):
    """Удаляет из указанного родителя тег с переданным именем."""
    node_for_remove = parent.find(name)
    if node_for_remove != None:
        parent.remove(node_for_remove)


def save_result(dom, src_file_path: Path, *, new_file_name: str = None) -> None:
    """Сохраняет результат обработки рядом с исходным файлом в каталоге `converted`."""
    dst_path = Path(src_file_path.parent) / 'converted'
    if not dst_path.exists():
        dst_path.mkdir()
    dst_file_path = str(dst_path / (new_file_name or src_file_path.name))
    f = open(dst_file_path, "w", encoding='cp1251', errors=None, newline='\r\n')
    f.write(etree.tostring(dom, pretty_print=True, encoding='Windows-1251', xml_declaration=True).decode('cp1251'))
    f.close()


def prepare_prks(file_path: Path):
    """Преобразует и сохраняет измененный файл prks."""
    tree = etree.parse(str(file_path))
    root = tree.getroot()

    root.find('ZGLV').find('VERSION').text = '1.0'
    for pers in root.findall('PERS'):
        for node_name in ('MD_DEP_ID', 'AREA_TYPE', 'DOC_ID'):
            remove_node(pers, node_name)

        etree.SubElement(pers, "VPOLIS").text = '3'
        etree.SubElement(pers, "SPOLIS")
        etree.SubElement(pers, "NPOLIS").text = pers.find('ENP').text
        remove_node(pers, 'ENP')

    save_result(root, file_path)
    print('Done.')


def prepare_ozps(file_path: Path):
    """Преобразует и сохраняет измененный файл ozps."""
    tree = etree.parse(str(file_path))
    root = tree.getroot()
    
    root.find('ZGLV').find('VERSION').text = '1.0'

    inner_fname = root.find('ZGLV').find('FILENAME').text
    inner_fname = inner_fname.split('.')[0] if '.xml' in inner_fname.lower() else inner_fname
    root.find('ZGLV').find('FILENAME').text = inner_fname

    for pers in root.findall('PERS'):
        etree.SubElement(pers, "VPOLIS").text = '3'
        etree.SubElement(pers, "SPOLIS")
        etree.SubElement(pers, "NPOLIS").text = pers.find('ENP').text
        remove_node(pers, 'ENP')

    save_result(root, file_path)
    print('Done.')


def prepare_szpm(file_path: Path):
    """Преобразует и сохраняет измененный файл szpm в файл для прикрепления по терапевтическому профилю."""
    today = datetime.now()
    new_file_name = f'ATM{CODE_MO}T35351_{str(today.year)[2:]}{str(today.month).zfill(2)}{today.day}'

    tree = etree.parse(str(file_path))
    root = tree.getroot()
    
    root.tag = 'ATT'

    zglv_tag = root.find('ZGLV')
    zglv_tag.find('VERSION').text = '1.3'

    date_tag = zglv_tag.find('DATE')
    date_tag.tag = 'FDATE'

    filename_tag = zglv_tag.find('FILENAME')
    filename_tag.tag = 'FNAME'
    filename_tag.text = new_file_name

    for tag_name in ('YEAR', 'MONTH', 'ZAP'):
        removing_tag = zglv_tag.find(tag_name)
        if removing_tag != None:
            zglv_tag.remove(removing_tag)

    etree.SubElement(zglv_tag, 'AREA_TYPE').text = '1'

    pers_for_remove = []
    for pers in root.findall('PERS'):
        
        doc_code_tag = pers.find('DOC_CODE')
        # Проверяем, чтобы к пациенту был закреплен медик,
        # иначе удаляем из обработки такие заявления.
        if doc_code_tag is None:
            pers_for_remove.append(pers)
            continue
        
        pers.tag = 'REC'

        for tag_name in ('PR_NOV', 'ID_PAC', 'DOCSER', 'DOCNUM', 'VPOLIS', 'SMO', 'DOC_POST'):
            removing_tag = pers.find(tag_name)
            if removing_tag != None:
                pers.remove(removing_tag)
        
        enp_tag = pers.find('NPOLIS')
        enp_tag.tag = 'ENP'

        datez_tag = pers.find('DATEZ')
        datez_tag.tag = 'DATE_ATTACH_B'

        prz_tag = pers.find('PRZ')
        prz_tag.tag = 'ATTACH_METHOD'
        prz_tag.text = '2'

        # Убрать все разделители.
        doc_code_tag = pers.find('DOC_CODE')
        if doc_code_tag != None:
            doc_code_tag.text = doc_code_tag.text.replace('-', '').replace(' ', '')

        # Согласно спецификации должен указываться, но поле опциональное.
        # etree.SubElement(pers, 'DOC_ID').text = ''

    # Удаляем неподходящие данные.
    for item in pers_for_remove:
        root.remove(item)
    
    # Исправляем порядок номеров.
    for i, pers in enumerate(root.findall('REC'), start=1):
        pers.find('N_ZAP') = str(i)

    save_result(root, file_path, new_file_name=f'{new_file_name}.xml')
    print('Done.')


if __name__ == '__main__':
    parser = init()
    args = parser.parse_args()

    file_path = Path(args.file)

    if not file_path.exists():
        print(f'handling file not found in path "{file_path}"')
        sys.exit()

    if file_path.is_dir():
        print(f'handling file not found, current path "{file_path}" is directory.')
        sys.exit()

    if file_path.name.lower().startswith('prks'):
        prepare_prks(file_path)

    elif file_path.name.lower().startswith('ozps'):
        prepare_ozps(file_path)

    elif file_path.name.lower().startswith('szpm'):
        prepare_szpm(file_path)
