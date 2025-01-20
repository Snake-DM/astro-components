import csv
import logging
import os
import pathlib
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.dom import minidom
from xml.etree.ElementTree import Element

import requests
import yaml
from PIL import Image
from requests import HTTPError, RequestException

from config import dealer, model_mapping


# Initialize logging
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                    level=logging.DEBUG,
                    # filename='output.txt')
                    )

# Global variables
ELEMENTS = [
    'mark_id',
    'folder_id',
    'modification_id',
    'complectation_name',
    'color',
    'year'
]
# Предполагаем, что у вас есть элементы с именами
ELEMENTS_TO_LOCALIZE = [
    'mark_id',
    'folder_id',
    'modification_id',
    'complectation_name',
    'color']

# Перевод некоторых свойств, для читабельности
TRANSLATIONS = {
    # engineType
    "hybrid"        : "Гибрид",
    "petrol"        : "Бензин",
    "diesel"        : "Дизель",
    "petrol_and_gas": "Бензин и газ",
    "electric"      : "Электро",

    # driveType
    "full_4wd"      : "Постоянный полный",
    "optional_4wd"  : "Подключаемый полный",
    "front"         : "Передний",
    "rear"          : "Задний",

    # gearboxType
    "robotized"     : "Робот",
    "variator"      : "Вариатор",
    "manual"        : "Механика",
    "automatic"     : "Автомат",

    # transmission
    "RT"            : "Робот",
    "CVT"           : "Вариатор",
    "MT"            : "Механика",
    "AT"            : "Автомат",

    # ptsType
    "duplicate"     : "Дубликат",
    "original"      : "Оригинал",
    "electronic"    : "Электронный",

    # bodyColor
    "black"         : "Черный",
    "white"         : "Белый",
    "blue"          : "Синий",
    "gray"          : "Серый",
    "silver"        : "Серебристый",
    "brown"         : "Коричневый",
    "red"           : "Красный",
    "grey"          : "Серый",
    "azure"         : "Лазурный",
    "beige"         : "Бежевый",

    # steeringWheel
    "left"          : "Левый",
    "right"         : "Правый",
    "L"             : "Левый",
    "R"             : "Правый",

    # bodyType
    "suv"           : "SUV",
}

# car files list
existing_files = set()
# cars missed in mapping config
missing_cars = set()

# Глобальный список для хранения путей к текущим превьюшкам
image_filepath_set = set()  # relative path
thumb_filepath_set = set()  # absolute path

# setting environment folders
# project folder
current_dir = pathlib.Path(__file__).parent.parent.parent.resolve()
logger.info("Current directory: %s", current_dir)

# Папка Thumbs - создание чистой папки
thumbs_output_dir = pathlib.Path(current_dir, "public", "img", "thumbs")
logger.info("!!! thumbs output dir: %s", thumbs_output_dir)
try:
    if thumbs_output_dir.exists():
        shutil.rmtree(thumbs_output_dir)
    thumbs_output_dir.mkdir(parents=True)  # TODO create just Thumbs or Parents=True?
except Exception as e:
    logger.error("Failed to process output directory for thumbs: %s", e)

# Папка для автомобилей - создание чистой папки
cars_output_dir = pathlib.Path(current_dir, "src", "content", "cars")  #
# "src/content/cars"
try:
    if cars_output_dir.exists():
        shutil.rmtree(cars_output_dir)
    cars_output_dir.mkdir(parents=True)
except Exception as e:
    logger.error("Failed to process output directory for cars: %s", e)


class Car:
    def __init__(self, _car: ET.Element):
        self.car = _car

    @property
    def get_vin(self):
        if self.car.find('vin') is not None:
            return self.car.find('vin').text
        return


    @property
    def get_vin_mask(self):
        if self.car.find('vin') is not None:
            return f"{self.car.find('vin').text[:5]}-{self.car.find('vin').text[-4:]}"
        return

    @property
    def get_mark_id(self):
        if self.car.find('mark_id') is not None:
            return self.car.find('mark_id').text
        return

    @property
    def get_folder_id(self):
        if self.car.find('folder_id') is not None:
            return self.car.find('folder_id').text.strip()
        return

    @property
    def get_modification_id(self):
        if self.car.find('modification_id') is not None:
            return self.car.find('modification_id').text
        return

    @property
    def get_complectation_name(self):
        if self.car.find('complectation_name') is not None:
            return self.car.find('complectation_name').text
        return

    @property
    def get_color(self):
        if self.car.find('color') is not None:
            return self.car.find('color').text.strip().capitalize()
        return

    @property
    def get_year(self):
        if self.car.find('year') is not None:
            return self.car.find('year').text
        return

    @property
    def get_run(self):
        if self.car.find('run') is not None:
            return self.car.find('run').text
        return

    @property
    def get_price(self):
        if self.car.find('price') is not None:
            return self.car.find('price').text
        return

    @property
    def get_price_with_discount(self):
        if self.car.find('priceWithDiscount') is not None:
            return self.car.find('priceWithDiscount').text
        return

    @property
    def get_description(self):
        if self.car.find('description') is not None:
            return self.car.find('description').text
        return

    @property
    def get_total(self):
        if self.car.find('total') is not None:
            return self.car.find('total').text
        return

    @property
    def get_url(self):
        if self.car.find('url') is not None:
            return self.car.find('url').text
        return

    @property
    def get_image(self):
        if self.car.find('image') is not None:
            return self.car.find('image').text
        return

    @property
    def get_images(self) -> list[str] | None:
        all_images = self.car.find('images')
        if all_images is not None:
            return [image.text.strip() for image in all_images.findall('image')]
        return


    def get_any_property(self, name: str):
        if self.car.find(name) is not None:
            return self.car.find(name).text
        return

    def get_unique_id(self, *elements):
        """
        Builds a unique ID string by extracting specified elements from the XML car data.
        """
        return " ".join(self.car.find(element).text.strip()
                        for element in elements  # TODO ELEMENTS?
                        if self.car.find(element) is not None
                        and
                        self.car.find(element).text is not None)

    # # TODO Option 1 (separate unique_id, filepath) - Remove?
    # def get_unique_id_file_prefix(self, *elements, delimiter: str = "-"):
    #     """
    #     Builds a unique ID string by extracting specified elements from the XML car
    #     data.
    #     """
    #     unique_id_draft = f"{delimiter}".join(self.car.find(element).text.strip()
    #                                           for element in elements # TODO ELEMENTS?
    #                                           if self.car.find(element) is not None
    #                                           and
    #                                           self.car.find(element).text is not None)
    #
    #     return (re.sub(r'[/\\?%*:|"<>.,;\'\[\]()&]', '', unique_id_draft).
    #                  replace("+", "-plus").
    #                  lower())
    #
    # def get_filepath(self, _unique_id_prefix: str) -> Path:
    #     """
    #     Get a file path for the MDX file with the given unique ID
    #     """
    #
    #     return pathlib.Path("src", "content", "cars", f"{_unique_id_prefix}.mdx")

    # TODO Option 2 (joined unique_id + filepath)
    def get_unique_id_filepath(self, *elements, delimiter: str = "-") -> Path:
        """
        Get a file path for the MDX file with the generated unique ID
        """

        unique_id_draft = f"{delimiter}".join(self.car.find(element).text.strip()
                                              for element in elements  # TODO ELEMENTS?
                                              if self.car.find(element) is not None
                                              and
                                              self.car.find(element).text is not None)

        unique_id_prefix = (
            re.sub(r'[/\\?%*:|"<>.,;\'\[\]()& ]', '', unique_id_draft).
            replace("+", "-plus").
            lower()
        )

        logger.info("!!! Unique_id Normalized: %s", unique_id_prefix)

        return pathlib.Path(cars_output_dir, f"{unique_id_prefix}.mdx")


def process_url_to_xml(data) -> ET.Element:
    """
    Try to get xml data from provided URL
    """
    try:
        response = requests.get(data)
        content = response.content
        # "Bytes to String" Decode (BOM is removed)
        xml_content = content.lstrip(b'\xef\xbb\xbf').decode('utf-8')

        # Parsing the provided XML data
        try:
            root = ET.fromstring(xml_content)
            return root

        except ET.ParseError as e:
            logger.error("Error parsing XML: %s", e)
        except SyntaxError as e:
            logger.error("Syntax error in XML: %s", e)

    except RequestException as e:
        logger.error("An error occurred: %s", e)


def process_file_to_xml(data) -> Element:
    """
    Try to get xml data from provided file
    """
    if pathlib.Path(data).exists():

        try:
            tree = ET.parse(data)
            root = tree.getroot()
            return root

        except ET.ParseError as e:
            logger.error("Error parsing XML: %s", e)
        except SyntaxError as e:
            logger.error("Syntax error in XML: %s", e)


def create_file(_car: Car, filename) -> None:
    # Логика создания файла
    # TODO make it for path or filename? One or Multiply files?

    global ELEMENTS_TO_LOCALIZE, TRANSLATIONS

    vin = _car.get_vin_mask  # hidden vin
    logger.info("!!! VIN: %s", vin)
    # Преобразование цвета
    color = _car.get_color
    logger.info("!!! Цвет автомобиля: %s", color)
    model = _car.get_folder_id

    try:
        model_data_all = model_mapping[model]
        try:
            model_data_color = model_data_all['color']
        except KeyError as e:
            logger.error(f"VIN: {vin}. Color not found")
            # Если 'color' не найден, используем путь к изображению ошибки 404
            thumb = pathlib.Path("img", "404.jpg")
            # TODO Model more appropriate error
            # raise ValueError(f"VIN: {vin}. Model color {model_data_color} not found")
            raise HTTPError(404, f"VIN: {vin}. Color not found")

        # Проверяем, существует ли 'model' в 'model_mapping' и есть ли соответствующий
        # 'color'

        try:
            folder = model_data_all['folder']
            color_image = model_data_color[color]
            logger.info("!!! Картинка Цвет автомобиля: %s", color_image)
            thumb = pathlib.Path(thumbs_output_dir,
                                 "img",
                                 "models",
                                 folder,
                                 "colors",
                                 color_image)
        except KeyError as e:
            thumb = pathlib.Path("img", "404.jpg")
            logger.error(f"VIN: {vin}. Model/Color not found. Error: {e}")
    except KeyError as e:
        logger.error(f"VIN: {vin}. Model {model} not found")
        # Если 'model' не найден, используем путь к изображению ошибки 404
        missing_cars.add((vin, model))
        thumb = pathlib.Path("img", "404.jpg")
        # TODO Color more appropriate error
        # raise ValueError(f"Model {model} not found")
        # TODO raise and stop execution or continue running a script?
        # raise HTTPError(404, f"VIN: {vin}. Model {model} not found")

    # Forming the YAML frontmatter
    content = "---\n"
    # content += "layout: car-page\n"
    total_element = _car.get_total
    if total_element is None:
        content += f"total: {1}\n"
    else:
        content += f"total: {int(total_element or 0)}\n"
    # content += f"permalink: {unique_id}\n"
    content += f"vin_hidden: {vin}\n"

    h1 = _car.get_unique_id('folder_id', 'modification_id')
    content += f"h1: {h1}\n"

    content += (f"breadcrumb: "
                f"{_car.get_unique_id('mark_id', 'folder_id', 'complectation_name')}\n")

    title = (f"{_car.get_unique_id('mark_id', 'folder_id', 'modification_id')} "
             f"купить у официального дилера в {dealer.get('where')}")  # TODO exists?
    content += f"title: {title}\n"

    description = ""

    # TODO move to a function?
    # elements text normalization
    for elem_name in ELEMENTS_TO_LOCALIZE:
        element = _car.get_any_property(elem_name)
        if element is not None and element in TRANSLATIONS:
            element.text = TRANSLATIONS[element.text]

    # TODO move to a function?
    # Создаем множество для отслеживания встреченных тегов
    encountered_tags = set()

    for child in _car.car:
        # Skip nodes with child nodes (except images) and attributes
        if list(child) and child.tag != 'images':
            continue
        if child.tag == 'total':
            continue
        if child.tag == 'images':
            images = [img.text.strip() for img in child.findall('image')]
            thumb_filepaths = create_thumbs(images, _car.get_unique_id(*ELEMENTS))
            content += f"images: {images}\n"
            content += f"thumbs: {thumb_filepaths}\n"  # TODO clear for each car?
        elif child.tag == 'color':
            content += f"{child.tag}: {color}\n"
            content += f"image: {thumb}\n"
        elif child.tag == 'extras' and child.text:
            extras = child.text
            flat_extras = extras.replace('\n', '<br>\n')
            content += f"{child.tag}: |\n"
            for line in flat_extras.split("\n"):
                content += f"  {line}\n"
        elif child.tag == 'description' and child.text:
            description = child.text
            content += f"description: |\n"
            content += (f"  Купить автомобиль"
                        f" {_car.get_unique_id('mark_id', 'folder_id')}"
                        f"{f' {_car.get_year} года выпуска' if _car.get_year else ''}"
                        f"{f', комплектация {_car.get_complectation_name}' if _car.get_complectation_name is not None else ''}"
                        f"{f', цвет - {_car.get_color}' if _car.get_color is not None else ''}"
                        f"{f', двигатель - {_car.get_modification_id}' if _car.get_modification_id is not None else ''}"
                        f" у официального дилера в г. {dealer.get('city')}."
                        f" Стоимость данного автомобиля "
                        f"{_car.get_unique_id('mark_id', 'folder_id')} – "
                        f"{f'{_car.get_price_with_discount}' if {_car.get_price_with_discount} is not None else 'цена'}\n")
            # flat_description = description.replace('\n', '<br>\n')  # TODO not used?
            # for line in flat_description.split("\n"):
            # content += f"  {line}\n"
        else:
            # TODO "if" not required as set stores unique values
            # if child.tag not in encountered_tags:  # Проверяем, встречался ли уже такой
            encountered_tags.add(child.tag)  # Добавляем встреченный тег в множество
            if child.text:  # Only add if there's content
                content += f"{child.tag}: {child.text}\n"

    content += "---\n"

    # process_description
    content += process_description(description)

    # Write a file
    try:
        with open(filename, 'w') as f:
            f.write(content)
        logger.info(f"Processed {filename}")
    except Exception as e:
        logger.error(f"Failed to write {filename}: {e}")

    existing_files.add(filename)

    return


def update_yaml(_car: Car, filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Yaml update: reading {filename} complete.")
    except Exception as e:
        logger.error(f"Failed to read {filename}: {e}")

    # Split the content by the YAML delimiter
    yaml_delimiter = "---\n"
    parts = content.split(yaml_delimiter)

    # If there's no valid YAML block, raise an exception
    if len(parts) < 3:
        raise ValueError("No valid YAML block found in file {filename}.")

    # Parse the YAML block
    yaml_block = parts[1].strip()
    data = yaml.safe_load(yaml_block)

    data['total'] = int(_car.get_total or 0) + int(data.setdefault('total', 0))
    data['run'] = min(int(_car.get_run or 0), int(data.setdefault('run', 0)))
    data['priceWithDiscount'] = (
        min(int(_car.get_price_with_discount or 0),
            data.setdefault('priceWithDiscount', 0))
    )

    images: list[str | None] | None = _car.get_images
    if images is not None:
        if len(images) > 0:
            data.setdefault('images', []).extend(images)
            if 'thumbs' not in data or (len(data['thumbs']) < 5):
                thumbs_files = create_thumbs(images, _car.get_unique_id(*ELEMENTS))
                # TODO Обнуляем то, что было в data и пишем новые пути thumbs?
                data.setdefault('thumbs', []).extend(thumbs_files)

    # Convert data back to a YAML string
    updated_yaml_block = yaml.safe_dump(data,
                                        default_flow_style=False,
                                        allow_unicode=True)

    # Reassemble content with updated YAML block
    updated_content = yaml_delimiter.join(
            [
                parts[0],
                updated_yaml_block,
                yaml_delimiter.join(parts[2:])
            ]
    )

    # Save the updated content to the output file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(updated_content)
        logger.info(f"Yaml update {filename} complete.")
    except Exception as e:
        logger.error(f"Failed to write {filename}: {e}")
    return filename


def process_csv(csv_file: Any):
    """
    Process a CSV file and generate XML
    """

    logger.info("!!! Start processing CSV file..")

    # file source
    url = ""
    file_path = ""
    data = csv_file

    cars_result_file = pathlib.Path(__file__).parent / "cars.xml"
    if cars_result_file.exists():
        os.remove(cars_result_file)

    if data is None:
        raise ValueError("No data to process.")
    elif isinstance(data, str):
        # File read
        try:
            with open(data, mode='r', encoding='utf-8') as file:
                data = file.readlines()
        except FileNotFoundError as e:
            logger.error("File not found: %s", e)
        except (IOError, OSError) as e:
            logger.error("Error reading a file: %s", e)
    else:
        # URL read
        try:
            response = requests.get(url)
            data = response.text.splitlines()
        except RequestException as e:
            logger.error("An error occurred while reading URL data: %s", e)

    reader = csv.DictReader(data)

    root = ET.Element('data')
    cars = ET.SubElement(root, 'cars')

    for row in reader:
        car = ET.SubElement(cars, 'car')
        ET.SubElement(car, 'mark_id').text = row.get('Марка', 'GAC')
        ET.SubElement(car, 'folder_id').text = row.get('Модель', '')
        ET.SubElement(car, 'modification_id').text = row.get('Модификация', '')
        ET.SubElement(car, 'body_type').text = row.get('Тип кузова', '')
        ET.SubElement(car, 'complectation_name').text = row.get('Комплектация', '')
        ET.SubElement(car, 'wheel').text = row.get('Руль', 'Правый')
        ET.SubElement(car, 'color').text = row.get('Цвет', '')
        ET.SubElement(car, 'metallic').text = row.get('Металлик', '')
        ET.SubElement(car, 'availability').text = row.get('Наличие', 'в наличии')
        ET.SubElement(car, 'driveType').text = row.get('Привод', 'Передний')
        ET.SubElement(car, 'engineType').text = row.get('Топливо', 'Бензин')
        ET.SubElement(car, 'gearboxType').text = row.get('Коробка', '')
        ET.SubElement(car, 'run').text = row.get('Пробег', '0')
        ET.SubElement(car, 'custom').text = row.get('Таможня', 'растаможен')
        ET.SubElement(car, 'owners_number').text = row.get('Владельцы',
                                                           'Не было владельцев')
        ET.SubElement(car, 'year').text = row.get('Год', '2023')
        ET.SubElement(car, 'price').text = row.get('Цена', '')
        ET.SubElement(car, 'credit_discount').text = row.get('Скидка по кредиту', '0')
        ET.SubElement(car, 'insurance_discount').text = row.get('Скидка по страховке',
                                                                '0')
        ET.SubElement(car, 'tradein_discount').text = row.get('Скидка по trade-in', '0')
        ET.SubElement(car,
                      'optional_discount').text = row.get('Дополнительная скидка', '0')
        ET.SubElement(car, 'max_discount').text = row.get('Максимальная скидка', '')
        ET.SubElement(car, 'currency').text = row.get('Валюта', 'RUR')
        ET.SubElement(car, 'vin').text = row.get('VIN', '')
        ET.SubElement(car, 'description').text = row.get('Описание', '')
        ET.SubElement(car, 'total').text = row.get('Количество', '1')
        # ET.SubElement(car, 'registry_year').text = row.get('Год регистрации', '2023')
        # images = ET.SubElement(car, 'images')
        # ET.SubElement(images, 'image').text = row.get('Ссылка на изображение', '')

    xml_tree = ET.ElementTree(root)

    try:
        rough_string = ET.tostring(xml_tree.getroot(), 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_string = reparsed.toprettyxml(indent="  ", encoding="UTF-8")
        with open(cars_result_file, 'wb') as f:
            f.write(pretty_xml_as_string)

        logger.info("!!! Finish processing CSV file.. Success")

    except ET.ParseError:
        logger.error("Error parsing XML: %s", e)
    except SyntaxError:
        logger.error("Error parsing XML: %s", e)
    except (IOError, OSError) as e:
        logger.error("Error writing a file: %s", e)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
    except TypeError as e:
        logger.error("Type error: %s", e)

    return


def build_unique_id(self, car, *elements):
    return " ".join(car.find(element).text.strip() for element in elements if
                    car.find(element) is not None and car.find(element).text is not None)


# def build_unique_id(self, car, *elements):
#     return " ".join(car.find(element).text.strip() for element in elements if
#                     car.find(element) is not None and car.find(element).text is not
#                     None)


# Helper function to process permalink
def mask_permalink(vin):
    return f"/cars/{vin[:5]}-{vin[-4:]}/"


# Helper function to process description and add it to the body
def process_description(desc_text):
    lines = desc_text.split('\n')
    processed_lines = [f"<p>{line}</p>" if line.strip() != '' else "<p>&nbsp;</p>"
                       for line in lines]
    return '\n'.join(processed_lines)


def create_thumbs(image_urls: list[str], _unique_id: str) -> list[str]:
    """
    Функция для создания превью изображений
    """

    # Определение относительного пути для возврата
    # self.output_dir
    relative_output_dir = pathlib.Path("img", "thumbs")
    image_filepath_for_a_car = list()
    # # Список для хранения путей к новым или существующим файлам
    # # use set to store unique file paths
    # image_files_set = set()
    # current_thumbs_set = set()

    # Обработка первых 5 изображений  # TODO remove limits?
    for index, img_url in enumerate(image_urls[:5]):
        output_filename = f"thumb_{_unique_id}_{index}.webp"
        output_path = pathlib.Path(thumbs_output_dir, output_filename)
        relative_output_path = pathlib.Path(relative_output_dir, output_filename)

        # Проверка существования файла
        if not output_path.exists():
            # Загрузка и обработка изображения, если файла нет
            image_download = ''
            response = ''
            try:
                response = requests.get(img_url)
                logger.info("!!! Image downloaded successfully: %s",
                            response)

            except (RequestException, urllib.error.HTTPError) as e:
                logger.error(f"Error downloading image {img_url}: {e}")
            try:
                # image = Image.open(image_download[0])
                image = Image.open(BytesIO(response.content))
                aspect_ratio = image.width / image.height
                new_width = 360
                new_height = int(new_width / aspect_ratio)
                resized_image = image.resize(
                        (new_width, new_height),
                        Image.Resampling.LANCZOS)
                resized_image.save(output_path, "WEBP")
                logger.info(f"Image thumb created: {relative_output_path}")
            except ValueError as e:
                logger.error(f"Error processing image {img_url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error while processing image {img_url}: {e}")
        else:
            logger.info(f"File already exists: {relative_output_path}")

        # TODO to clear current sets globally or for each car?
        # Добавление относительного пути файла в глобальный список
        # global set
        image_filepath_set.add(relative_output_path.as_posix())
        # Добавление полного пути файла в глобальный список
        # global set
        thumb_filepath_set.add(output_path.as_posix())

        # Добавление относительного пути файла для одного объекта
        # local set
        image_filepath_for_a_car.append(relative_output_path.as_posix())
    return image_filepath_for_a_car


def cleanup_unused_thumbs() -> None:
    # TODO use global for output_dir and current_thumbs_set?
    logger.info("!!! Cleanup unused thumbs...")
    all_thumbs = [str(pathlib.Path(thumbs_output_dir, file)) for file in
                  os.listdir(thumbs_output_dir)]
    unused_thumbs = [thumb for thumb in all_thumbs if thumb not in thumb_filepath_set]

    try:
        for thumb in unused_thumbs:
            os.remove(thumb)
            logger.info(f"An unused thumb deleted: {thumb}")
        logger.info("!!! Cleanup unused thumbs... complete successfully")
    except Exception as e:
        logger.error(f"Не удалось удалить неиспользуемые превью: {e}")
    return None


def create_child_element(parent, new_element_name, text):
    # Поиск существующего элемента
    old_element = parent.find(new_element_name)
    if old_element is not None:
        parent.remove(old_element)

    # Создаем новый элемент с нужным именем и текстом старого элемента
    new_element = ET.Element(new_element_name)
    new_element.text = str(text)

    # Добавление нового элемента в конец списка дочерних элементов родителя
    parent.append(new_element)


def rename_child_element(parent, old_element_name, new_element_name):
    old_element = parent.find(old_element_name)
    if old_element is not None:
        # Создаем новый элемент с нужным именем и текстом старого элемента
        new_element = ET.Element(new_element_name)
        new_element.text = old_element.text

        # Заменяем старый элемент новым
        parent.insert(list(parent).index(old_element), new_element)
        parent.remove(old_element)


def update_element_text(parent, element_name, new_text):
    element = parent.find(element_name)
    if element is not None:
        element.text = new_text
    else:
        # Ваш код для обработки случая, когда элемент не найден
        print(f"Элемент '{element_name}' не найден.")


def localize_element_text(element, translations):
    if element is not None and element.text in translations:
        element.text = translations[element.text]


def convert_to_string(element: ET.Element):
    if element.text is not None:
        element.text = str(element.text)
    for child in element:
        convert_to_string(child)


if __name__ == "__main__":

    # Input data:
    dealer = dealer
    # model_mapping = "model_map"
    url_input = os.getenv('REPO_NAME', 'localhost')
    # data_source = url_input

    # Temporary input:
    data_source = 'stock47_n.xml'

    # Process data with input options:
    if data_source.startswith("http"):
        xml_root = process_url_to_xml(data_source)
    elif isinstance(data_source, str):
        xml_root = process_file_to_xml(data_source)
    else:
        raise ValueError("Invalid data source format")

    # Create a cars list
    # Find the <cars> element (first occurrence)
    cars = xml_root.find('cars')

    if cars:
        logger.info("Cars found: %s", cars)
        for i_car in cars:
            new_car = Car(i_car)
            car_filepath = new_car.get_unique_id_filepath(*ELEMENTS)

            if car_filepath.exists():
                update_yaml(new_car, str(car_filepath)) # TODO update_yaml
            else:
                create_file(new_car, str(car_filepath))
    else:
        raise ValueError("Cars not found")

    work_cars_file: Path = pathlib.Path(__file__).parent / "data.csv"
    # 'public/cars.xml'
    process_csv(str(work_cars_file))

    logger.info("---------------------------------\n"
                "SUMMARY: program completed. \n"
                "Cars missing in mapping configuration: \n"
                "%s", "\n".join(": ".join(i) for i in missing_cars) + "\n"
                )
    #
    #
    # convert_to_string(xml_root)
    # tree.write(str(result_path), encoding='utf-8', xml_declaration=True)
    #
    # for existing_file in os.listdir(cars_output_dir):
    #     filepath = os.path.join(cars_output_dir, existing_file)
    #     if filepath not in existing_files:
    #         os.remove(filepath)

    # Удаление неиспользуемых превьюшек
    cleanup_unused_thumbs()


# processor.process_xml('cars.xml')
# # или
# processor.process_xml('http://example.com/cars.xml')
# # или
# processor.process_xml(os.environ['XML_URL'])
# 
# В будущем:
# processor.process_csv('cars.csv')
