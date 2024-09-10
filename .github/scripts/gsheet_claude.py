# python3 .github/scripts/gsheet_claude.py
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
from io import StringIO


# Загрузка CSV-данных
response = requests.get('data.csv')
csv_data = StringIO(response.text)

# Создание корневого элемента XML
root = ET.Element("data")
cars = ET.SubElement(root, "cars")

# Словарь для маппинга заголовков CSV на теги XML
header_mapping = {
    "Марка": "mark_id",
    "Модель": "folder_id",
    "Модификация": "modification_id",
    "Тип кузова": "body_type",
    "Комплектация": "complectation_name",
    "Руль": "wheel",
    "Цвет": "color",
    "Металлик": "metallic",
    "Наличие": "availability",
    "Растаможен": "custom",
    "Владельцев по ПТС": "owners_number",
    "Год выпуска": "year",
    "Цена": "price",
    "Скидка при кредите": "credit_discount",
    "Скидка при страховке": "insurance_discount",
    "Скидка при трейд-ин": "tradein_discount",
    "Скидка при доп. оборудовании": "optional_discount",
    "Максимальная скидка": "max_discount",
    "Год регистрации": "registry_year",
    "VIN": "vin",
    "Описание": "description",
    "Изображения": "images"
}

# Чтение CSV-файла
csv_reader = csv.DictReader(csv_data)

for row in csv_reader:
    car = ET.SubElement(cars, "car")
    
    for csv_header, xml_tag in header_mapping.items():
        value = row.get(csv_header, "")
        
        if xml_tag == "images" and value:
            images = ET.SubElement(car, "images")
            for img_url in value.split(","):
                ET.SubElement(images, "image").text = img_url.strip()
        else:
            ET.SubElement(car, xml_tag).text = value

    # Добавление стандартных значений
    ET.SubElement(car, "currency").text = "RUR"

# Создание красиво отформатированного XML
xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

# Запись XML в файл
with open("output.xml", "w", encoding="utf-8") as f:
    f.write(xmlstr)

print("XML-файл успешно создан: output.xml")