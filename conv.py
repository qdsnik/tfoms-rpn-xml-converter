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
    'allow_save_atm_to_new_package': True,
    'fap_oids': []
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


class ATMType:
    """Тип документа."""
    TERAPEVTS_ATTACHMENT = 'T35351'
    TERAPEVTS_OUT_OFF_TOWN_ATTACHMENT = 'T35001'
    FAP_ATTACHMENT = 'T35355'
    FAP_OUT_OFF_TOWN_ATTACHMENT = 'T35005'


def remove_node(parent, name):
    """Удаляет из указанного родителя тег с переданным именем."""
    node_for_remove = parent.find(name)
    if node_for_remove != None:
        parent.remove(node_for_remove)


def save_result(dom, src_file_path: Path, *, new_file_name: str = None) -> str:
    """Возвращает имя файла, сохраняет результат обработки рядом с исходным файлом в каталоге `converted`."""
    dst_path = Path(src_file_path.parent) / 'converted'
    if not dst_path.exists():
        dst_path.mkdir()
    dst_file_path = str(dst_path / (new_file_name or src_file_path.name))
    f = open(dst_file_path, "w", encoding='cp1251', errors=None, newline='\r\n')
    f.write(etree.tostring(dom, pretty_print=True, encoding='Windows-1251', xml_declaration=True).decode('cp1251'))
    f.close()

    return (new_file_name or src_file_path.name)


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


def get_new_atm_name(config: Config, file_type: int = ATMType.TERAPEVTS_ATTACHMENT) -> str:
    """
    Возвращает имя ATM файла с новым номером пакета.

    :param config: объект настроек
    :param file_type: тип файла:
        1 — терапевтическое прикрепление (T35351)
        2 — ФАП-прикрепление (T35355)
        Можно далее расширять при появлении новых типов.
    """
    today = datetime.now()
    code_lpu = config.conf_data['code_lpu']

    return f'ATM{code_lpu}{file_type}_{str(today.year)[2:]}{str(today.month).zfill(2)}{str(config.inc_month_counter()).zfill(3)}'


def get_fap_record_ids(root_node, config: Config) -> list[str]:
    """Возвращает номера записей с oid-ами ФАП-ов."""
    selected_ids = []
    fap_oids = set(config.conf_data.get("fap_oids", []))
    for pers in root_node.findall('PERS'):
        mo_dep = pers.find('MO_DEP_ID')
        if mo_dep is not None and mo_dep.text in fap_oids:
            selected_ids.append(pers.find('N_ZAP').text)
    
    return selected_ids


def prepare_att_header(root, filename):
    """Возвращает подготовленный заголовок ATT."""
    zglv_tag = root.find('ZGLV')
    zglv_tag.find('VERSION').text = '1.3'

    date_tag = zglv_tag.find('DATE')
    date_tag.tag = 'FDATE'

    filename_tag = zglv_tag.find('FILENAME')
    filename_tag.tag = 'FNAME'
    filename_tag.text = filename

    for tag_name in ('YEAR', 'MONTH', 'ZAP'):
        removing_tag = zglv_tag.find(tag_name)
        if removing_tag is not None:
            zglv_tag.remove(removing_tag)

    etree.SubElement(zglv_tag, 'AREA_TYPE').text = '1'

    return zglv_tag


def prepare_szpm(file_path: Path, config: Config, ids_for_exclude=None):
    """Преобразует и сохраняет измененный файл szpm в файл для прикрепления по терапевтическому профилю."""
    tree = etree.parse(str(file_path))
    root = tree.getroot()

    record_ids_for_fap = get_fap_record_ids(root, config)

    # Преобразование SZPM -> ATT (как раньше).
    root.tag = 'ATT'
    new_file_name = get_new_atm_name(config)
    zglv_tag = prepare_att_header(root, new_file_name)

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
            if removing_tag is not None:
                pers.remove(removing_tag)

        enp_tag = pers.find('NPOLIS')
        if enp_tag is not None:
            enp_tag.tag = 'ENP'
        else:
            pers_for_remove.append(pers)
            continue

        datez_tag = pers.find('DATEZ')
        if datez_tag is not None:
            datez_tag.tag = 'DATE_ATTACH_B'
        else:
            pers_for_remove.append(pers)
            continue

        prz_tag = pers.find('PRZ')
        if prz_tag is not None:
            prz_tag.tag = 'ATTACH_METHOD'
            prz_tag.text = '2'
        else:
            pers_for_remove.append(pers)
            continue

        doc_code_tag = pers.find('DOC_CODE')
        doc_code_tag.text = doc_code_tag.text.replace('-', '').replace(' ', '')

    for item in pers_for_remove:
        root.remove(item)

    # Удаляем исключенные записи из аргумента ids_for_exclude.
    if ids_for_exclude:
        pers_for_remove = []
        for pers in root.findall('REC'):
            if pers.find('N_ZAP').text in ids_for_exclude.split(','):
                pers_for_remove.append(pers)

        for item in pers_for_remove:
            root.remove(item)

    etree.indent(root, space="\t")
    filename = save_result(root, file_path, new_file_name=f'{new_file_name}.xml')
    print("[INFO] Создан TER файл: %s" % filename)

    # Создание варианта ATT для ФАП-ов.
    fap_file_name = get_new_atm_name(config, file_type = ATMType.FAP_ATTACHMENT)
    if record_ids_for_fap:
        fap_root = etree.Element("ATT")
        selected_zglv = etree.fromstring(etree.tostring(zglv_tag))
        selected_zglv.find('FNAME').text = fap_file_name
        selected_zglv.find('AREA_TYPE').text = '3'
        fap_root.append(selected_zglv)
        fap_root.extend([rec for rec in root.findall('REC') if rec.find('N_ZAP').text in record_ids_for_fap])
        etree.indent(fap_root, space="\t")
        filename = save_result(fap_root, file_path, new_file_name=f'{fap_file_name}.xml')
        print("[INFO] Создан FAP файл: %s" % filename)

    print('Done.')


def prepare_atm(file_path: Path, conf: Config, *, flk_path: Path, extended_ids_for_exclude=None) -> str:
    """Исправляет файл atm исключением дефектных строк из ФЛК."""
    ids_for_exclude = []
    if flk_path:
        flk_tree = etree.parse(str(flk_path))
        flk_root = flk_tree.getroot()
        flk_result = flk_root.find('ZGLV').find('FLK_RES').text

        if int(flk_result) == 0:
            return ''
    
        ids_for_exclude = [x.find('N_ZAP').text for x in flk_root.findall('ERROR')]
    
    if extended_ids_for_exclude:
        ids_for_exclude.extend(extended_ids_for_exclude.split(','))

    if not ids_for_exclude:
        raise RuntimeError('Нет данных для обрабоки ATM')

    tree = etree.parse(str(file_path))
    root = tree.getroot()
    pers_for_remove = []
    for pers in root.findall('REC'):        
        if pers.find('N_ZAP').text in ids_for_exclude: 
            pers_for_remove.append(pers)

    for item in pers_for_remove:
        root.remove(item)
    
    if conf.conf_data['allow_save_atm_to_new_package']:
        new_file_name = get_new_atm_name(conf)
        return save_result(root, file_path, new_file_name=f'{new_file_name}.xml')
    
    return save_result(root, file_path)


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
    parser.add_argument('--flk', type=str, required=False, help='xml c flk для обработки')
    parser.add_argument('--exclude_ids', type=str, default='', help='id записей для исключения из SZPM или ATM файлов')

    return parser


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
        flk_file_param = args.flk
        if not flk_file_param:
            print('key "--flk" is required for porocessed ATM')
            sys.exit()
        if not flk_file_param:
            flk_path = Path(flk_file_param)
            if not flk_path.exists():
                print(f'handling file not found in path "{flk_path}"')
                sys.exit()

            if flk_path.is_dir():
                print(f'handling file not found, current path "{flk_path}" is directory.')
                sys.exit()

        atm_name_for_copy = prepare_atm(file_path, conf, flk_path=flk_path, extended_ids_for_exclude=args.exclude_ids)
        print(atm_name_for_copy)
