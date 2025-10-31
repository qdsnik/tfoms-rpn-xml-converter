from __future__ import annotations
import json
import os
from pathlib import Path
from lxml import etree
import argparse
import sys
from datetime import datetime


DEFAULT_CONFIG = {
    'month_packet_counter': {"2025-10": 0},
    'code_lpu': '352530',  # Код МО из F032
}
CONFIG_PATH = os.path.join(os.getcwd(), 'conf.json')


def init_or_update_config() -> None:
    if os.path.exists(CONFIG_PATH):
        added_keys = []
        with open(CONFIG_PATH, 'r') as f:
            conf_data = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in conf_data:
                    conf_data[key] = value
                    added_keys.append(key)
        if added_keys:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(conf_data, f)
            print(f'В файл конфигурациии добавлены ключи: {added_keys}\n')
        else:
            print(f'Файл конфигурациии не изменен.\n')
    else:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)
            print('Конфиг не найден, создан дефолтный.\n')


class Config:
    def __init__(self):

        if not os.path.exists(CONFIG_PATH):
            init_or_update_config()

        today = datetime.now()
        self.month_packet_counter_key = f"{today.year}-{today.month}"
        self.conf_data = None
        self.load()

        # Проверяем актуальность счетчика относительно текущей даты, обновляем при необходимости.
        if self.month_packet_counter_key not in self.conf_data:
            self.conf_data['month_packet_counter'][self.month_packet_counter_key] = 0
            self.save()

    def load(self):
        with open(CONFIG_PATH, 'r') as f:
            self.conf_data = json.load(f)

    def save(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.conf_data, f)

    def inc_month_counter(self):
        if not self.conf_data:
            self.load()
        self.conf_data['month_packet_counter'][self.month_packet_counter_key] += 1
        self.save()
        return self.conf_data['month_packet_counter'][self.month_packet_counter_key]

    def get_month_counter(self):
        if not self.conf_data:
            self.load()
        return self.conf_data['month_packet_counter'][self.month_packet_counter_key]


def init() -> argparse.ArgumentParser:
    """Возвращает объект для разбора входных параметров."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-inconf',
        '--init_config',
        action='store_true',
        help=(
            'Инициализировать файл конфигурации, чтобы изменить настройки перед первым использованием. '
            'Если файл конфигурации уже существует, добавит только новые ключи.'
        )
    )
    parser.add_argument('-f', '--file', type=str, required=False, help='xml для обработки')
    parser.add_argument('--exclude_ids', type=str, default='', help='id записей для исключения из SZPM или ATM файлов')

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


def prepare_szpm(file_path: Path, config: Config, ids_for_exclude=None):
    """Преобразует и сохраняет измененный файл szpm в файл для прикрепления по терапевтическому профилю."""
    today = datetime.now()
    code_lpu = config['code_lpu']
    new_file_name = f'ATM{code_lpu}T35351_{str(today.year)[2:]}{str(today.month).zfill(2)}{str(config.inc_month_counter()).zfill(3)}'

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

    # Удаляем исключенные записи.
    if ids_for_exclude:
        pers_for_remove = []
        for pers in root.findall('REC'):        
            if pers.find('N_ZAP').text in ids_for_exclude.split(','): 
                pers_for_remove.append(pers)

        for item in pers_for_remove:
            root.remove(item)

    save_result(root, file_path, new_file_name=f'{new_file_name}.xml')
    print('Done.')


def prepare_atm(file_path: Path, ids_for_exclude=None):
    """Изменяет файл atm файл для прикрепления по терапевтическому профилю."""
    if not ids_for_exclude:
        return

    tree = etree.parse(str(file_path))
    root = tree.getroot()
    pers_for_remove = []
    for pers in root.findall('REC'):        
        if pers.find('N_ZAP').text in ids_for_exclude.split(','): 
            pers_for_remove.append(pers)

    for item in pers_for_remove:
        root.remove(item)
    
    save_result(root, file_path)
    print('Done.')


if __name__ == '__main__':
    parser = init()
    args = parser.parse_args()

    if args.init_config:
        init_or_update_config()
        sys.exit()
    
    conf = Config()


    file_param = args.file
    if not file_param:
        print('key "--file" is required for using conv')
        sys.exit()
    
    file_path = Path(file_param)
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
        prepare_szpm(file_path, conf, args.exclude_ids)

    elif file_path.name.lower().startswith('atm'):
        prepare_atm(file_path, args.exclude_ids)
