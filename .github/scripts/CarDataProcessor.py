import os
import re
import requests
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps
from io import BytesIO
import csv

class CarDataProcessor:
    def __init__(self, dealer, model_mapping, repo_name):
        self.dealer = dealer
        self.model_mapping = model_mapping
        self.repo_name = repo_name

        # Путь к папке для сохранения уменьшенных изображений
        self.output_dir = "public/img/thumbs/"
        # Проверка наличия папки, если нет - создаем
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Список для хранения путей к текущим превьюшкам
        self.current_thumbs = []
        self.existing_files = set()
        self.error_404_found = False

        # Перевод некоторых свойств, для читабельности
        self.translations = {
            # engineType
            "hybrid": "Гибрид",
            "petrol": "Бензин",
            "diesel": "Дизель",
            "petrol_and_gas": "Бензин и газ",
            "electric": "Электро",

            # driveType
            "full_4wd": "Постоянный полный",
            "optional_4wd": "Подключаемый полный",
            "front": "Передний",
            "rear": "Задний",

            # gearboxType
            "robotized": "Робот",
            "variator": "Вариатор",
            "manual": "Механика",
            "automatic": "Автомат",

            # transmission
            "RT": "Робот",
            "CVT": "Вариатор",
            "MT": "Механика",
            "AT": "Автомат",

            # ptsType
            "duplicate": "Дубликат",
            "original": "Оригинал",
            "electronic": "Электронный",

            # bodyColor
            "black": "Черный",
            "white": "Белый",
            "blue": "Синий",
            "gray": "Серый",
            "silver": "Серебристый",
            "brown": "Коричневый",
            "red": "Красный",
            "grey": "Серый",
            "azure": "Лазурный",
            "beige": "Бежевый",

            # steeringWheel
            "left": "Левый",
            "right": "Правый",
            "L": "Левый",
            "R": "Правый",

            # bodyType
            "suv": "SUV",
        }

    def process_xml(self, xml_file_or_url):
        if os.path.exists(xml_file_or_url):
            tree = ET.parse(xml_file_or_url)
            root = tree.getroot()
        else:
            response = requests.get(xml_file_or_url)
            response.raise_for_status()
            content = response.content
            
            # Убрать BOM, если он присутствует
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]
            
            # Декодируем содержимое из байтов в строку
            xml_content = content.decode('utf-8')

            # Parsing the provided XML data
            root = ET.fromstring(xml_content)

        self.process_cars(root.find('cars'))

    def process_csv(self, csv_file):
        # Здесь будет реализация обработки CSV
        pass

    def process_cars(self, cars):
        for car in cars:
            self.process_car(car)

    def process_car(self, car):
        # Логика обработки отдельного автомобиля
        unique_id = self.build_unique_id(car, 'mark_id', 'folder_id', 'modification_id', 'complectation_name', 'color', 'year')
        unique_id = self.process_unique_id(unique_id)
        file_name = f"{unique_id}.mdx"
        file_path = os.path.join("src/content/cars", file_name)

        if os.path.exists(file_path):
            self.update_yaml(car, file_path, unique_id)
        else:
            self.create_file(car, file_path, unique_id)

    def create_file(self, car, filename, unique_id):
        # Логика создания файла
        pass

    def update_yaml(self, car, filename, unique_id):
        # Логика обновления YAML
        pass

    def process_unique_id(self, unique_id, replace="-"):
        return re.sub(r'[\/\\?%*:|"<>.,;\'\[\]()&]', '', unique_id).replace("+", "-plus").replace(" ", replace).lower()

    def build_unique_id(self, car, *elements):
        return " ".join(car.find(element).text.strip() for element in elements if car.find(element) is not None and car.find(element).text is not None)
    
    def process_vin_hidden(vin):
        return f"{vin[:5]}-{vin[-4:]}"

    # Helper function to process permalink
    def process_permalink(vin):
        return f"/cars/{vin[:5]}-{vin[-4:]}/"

    # Helper function to process description and add it to the body
    def process_description(desc_text):
        lines = desc_text.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip() == '':
                processed_lines.append("<p>&nbsp;</p>")
            else:
                processed_lines.append(f"<p>{line}</p>")
        return '\n'.join(processed_lines)

    def createThumbs(self, image_urls, unique_id):
        # Определение относительного пути для возврата
        relative_output_dir = "/img/thumbs/"

        # Список для хранения путей к новым или существующим файлам
        new_or_existing_files = []

        # Обработка первых 5 изображений
        for index, img_url in enumerate(image_urls[:5]):
            try:
                output_filename = f"thumb_{unique_id}_{index}.webp"
                output_path = os.path.join(self.output_dir, output_filename)
                relative_output_path = os.path.join(relative_output_dir, output_filename)

                # Проверка существования файла
                if not os.path.exists(output_path):
                    # Загрузка и обработка изображения, если файла нет
                    response = requests.get(img_url)
                    image = Image.open(BytesIO(response.content))
                    aspect_ratio = image.width / image.height
                    new_width = 360
                    new_height = int(new_width / aspect_ratio)
                    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    resized_image.save(output_path, "WEBP")
                    print(f"Создано превью: {relative_output_path}")
                # else:
                    # print(f"Файл уже существует: {relative_output_path}")

                # Добавление относительного пути файла в списки
                new_or_existing_files.append(relative_output_path)
                self.current_thumbs.append(output_path)  # Здесь сохраняем полный путь для дальнейшего использования
            except Exception as e:
                print(f"Ошибка при обработке изображения {img_url}: {e}")

        return new_or_existing_files

    def cleanup_unused_thumbs(self):
        all_thumbs = [os.path.join(self.output_dir, f) for f in os.listdir(self.output_dir)]
        unused_thumbs = [thumb for thumb in all_thumbs if thumb not in self.current_thumbs]

        for thumb in unused_thumbs:
            os.remove(thumb)
            print(f"Удалено неиспользуемое превью: {thumb}")


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

    def convert_to_string(element):
        if element.text is not None:
            element.text = str(element.text)
        for child in element:
            convert_to_string(child)


# Пример использования:
# processor = CarDataProcessor(dealer, model_mapping, os.getenv('REPO_NAME', 'localhost'))
# processor.process_xml('cars.xml')
# или
# processor.process_xml('http://example.com/cars.xml')
# или
# processor.process_xml(os.environ['XML_URL'])
# 
# В будущем:
# processor.process_csv('cars.csv')