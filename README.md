# tfoms-rpn-xml-converter

Временная утилита для преобразования формата xml файлов реестров прикрепленного населения
из текущего формата см. http://new.oms35.ru/upload/Inf_MO_i_SMO/Informazion_vzaim/Izm_Regl_160824.pdf
в предыдущий.

```
python3 conv.py <имя xml>.xml
```

Совместимость: python 3.7+
Зависимости: lxml

Суть процесса:
    Файлы преобразуются к поддерживаемому МИС формату и сохраняются в каталог `./converted`

    Для prks:
        Переименовывается тег: ENP -> NPOLIS
        Добавляются теги: <VPOLIS>3</VPOLIS><SPOLIS/>
        Удаляются теги: MD_DEP_ID, AREA_TYPE, DOC_ID
        Меняет версию в заголовке с 1.2 на 1.0 (PRK -> ZGLV -> VERSION)
    
    Для ozps:
        Переименовывается тег: ENP -> NPOLIS
        Добавляются теги: <VPOLIS>3</VPOLIS><SPOLIS/>
        Убирается расширение из названии файла в ZL_LIST -> ZGLV -> FILENAME
        Меняет версию в заголовке с 1.2 на 1.0 (ZL_LIST -> ZGLV -> VERSION)