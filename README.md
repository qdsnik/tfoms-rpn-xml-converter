# tfoms-rpn-xml-converter

Временная утилита для преобразования формата xml файлов реестров прикрепленного населения
из текущего формата см. http://new.oms35.ru/upload/Inf_MO_i_SMO/Informazion_vzaim/Izm_Regl_160824.pdf
в предыдущий.

update 26.10.2025: доработка с учетом изменений в регламенте
http://new.oms35.ru/upload/Inf_MO_i_SMO/Informazion_vzaim/Reglament_030925.pdf

```
python3 conv.py <имя xml>.xml
```
Для удаления записей при повторной обработке можно передасть ключ `--exclude_ids`, пример:
```
    python3 conv.py <имя xml>.xml --exclude_ids=1,5,7
```


Для управления зависимоcтями используется uv. Для инициализации окружения предлагается использовать команду ниже.
```
uv sync
```
Либо развернуть виртуальное окружение вручную и взять зависимости из requirements.txt

Суть процесса:
    Файлы преобразуются к необходимому формату и сохраняются в каталог `./converted`
    Для PRKS, OZPS файлы ТФОМС преобразуются к формату, который поддерживает МИС.
    Для SZPM - файл из МИС преобразуется к файлу, поддерживаемому ТФОМС
    согласно спецификации http://new.oms35.ru/upload/Inf_MO_i_SMO/Informazion_vzaim/Reglament_030925.pdf

Для PRKS:
    переименовывается тег: ENP -> NPOLIS, 
    добавляются теги: <VPOLIS>3</VPOLIS><SPOLIS/>, 
    удаляются теги: MD_DEP_ID, AREA_TYPE, DOC_ID, 
    меняет версию в заголовке с 1.2 на 1.0 (PRK -> ZGLV -> VERSION)

Для OZPS:
    переименовывается тег: ENP -> NPOLIS, 
    добавляются теги: <VPOLIS>3</VPOLIS><SPOLIS/>, 
    убирается расширение из названии файла в ZL_LIST -> ZGLV -> FILENAME, 
    меняет версию в заголовке с 1.2 на 1.0 (ZL_LIST -> ZGLV -> VERSION)

Для преобразования SZPM -> ATM
    Меняем <ZL_LIST> -> <ATT>
    В заголовке:
        Меняем:
            <DATE> -> <FDATE>
            <FILENAME> -> <FNAME>
            <VERSION>  1.1 -> 1.3
            <FILENAME> -> <FNAME> + меняем содержимое
        Удаляем: YEAR, MONTH, ZAP
        Добавляем: <AREA_TYPE>1</AREA_TYPE>
    В записях:
        Переименовываем тег PERS -> REC
        Меняем:
            <NPOLIS> -> <ENP>
            <DATEZ> -> <DATE_ATTACH_B>
            <PRZ> -> <ATTACH_METHOD> + меняем значение на 2
            В <DOC_CODE> оставляем только цифры.
        Удаляем: PR_NOV, ID_PAC, DOCSER, DOCNUM, VPOLIS, SMO, DOC_POST

