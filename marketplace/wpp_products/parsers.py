import csv
import json
from xml.etree import ElementTree


class ProductFeedParser:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.content = self.try_decode(uploaded_file.read())

    def try_decode(self, byte_content, encodings=None):
        if encodings is None:
            encodings = ["utf-8", "ISO-8859-1", "windows-1252", "utf-16", "utf-32"]

        for encoding in encodings:
            try:
                return byte_content.decode(encoding)
            except UnicodeDecodeError:
                continue

        return byte_content.decode("utf-8", errors="replace")

    def detect_format(self):
        if self.content.startswith("<?xml"):
            if "<rss" in self.content:
                return "RSS_XML"
            elif "<feed" in self.content:
                return "ATOM_XML"
        elif "\t" in self.content:
            return "TSV"
        else:
            return "CSV"

    def parse(self):
        format_type = self.detect_format()

        if format_type == "CSV":
            products = self.parse_csv()
        elif format_type == "TSV":
            products = self.parse_csv(delimiter="\t")
        elif format_type == "RSS_XML":
            products = self.parse_rss_xml()
        elif format_type == "ATOM_XML":
            products = self.parse_atom_xml()
        else:
            raise ValueError("Unsupported format")

        # Normaliza todos os produtos extraídos
        return [self.normalize(product) for product in products]

    def normalize(self, product):
        # Ajustando namespaces do XML
        normalized = {}
        for key, value in product.items():
            new_key = key.split("}")[-1]  # Remove o namespace
            normalized[new_key] = value
        return normalized

    def parse_csv(self, delimiter=","):
        products = []
        csv_content = self.content.splitlines()
        reader = csv.DictReader(csv_content, delimiter=delimiter)
        for row in reader:
            product = {}
            for key, value in row.items():
                if value and (value.startswith("{") or value.startswith("[")):
                    try:
                        product[key] = json.loads(value)
                    except json.JSONDecodeError:
                        product[key] = value
                else:
                    product[key] = value
            products.append(product)
        return products

    def parse_rss_xml(self):
        products = []
        root = ElementTree.fromstring(self.content)
        for item in root.findall(".//item"):
            product = {child.tag: child.text for child in item}
            products.append(product)
        return products

    def parse_atom_xml(self):
        products = []
        root = ElementTree.fromstring(self.content)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            product = {child.tag: child.text for child in entry}
            products.append(product)
        return products

    def parse_as_dict(self):
        products = self.parse()
        return {product["id"]: product for product in products}
