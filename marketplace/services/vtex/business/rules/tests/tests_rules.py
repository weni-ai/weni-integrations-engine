import unittest

from marketplace.services.vtex.business.rules.round_up_calculate_by_weight import (
    RoundUpCalculateByWeight,
)
from marketplace.services.vtex.business.rules.calculate_by_weight_co import (
    CalculateByWeightCO,
)
from marketplace.services.vtex.business.rules.exclude_alcoholic_drinks import (
    ExcludeAlcoholicDrinks,
)
from marketplace.services.vtex.business.rules.currency_co import CurrencyCOP
from marketplace.services.vtex.business.rules.set_default_image_url import (
    SetDefaultImageURL,
)

from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class MockProductsDTO(unittest.TestCase):
    def setUp(self):
        self.products = [
            FacebookProductDTO(
                id="test1",
                title="Batata Doce Yakon Embalada",
                description="Batata Doce Yakon Embalada",
                availability="in stock",
                status="active",
                condition="new",
                price=2439,
                link="http://example.com/product",
                image_link="http://example.com/product.jpg",
                brand="ExampleBrand",
                sale_price=2439,
                product_details={
                    "UnitMultiplier": 0.5000,
                    "Dimension": {
                        "cubicweight": 0.3063,
                        "height": 5.0,
                        "length": 21.0,
                        "weight": 1000.0,
                        "width": 14.0,
                    },
                    "ProductCategories": {"1": "carnes e aves"},
                },
            ),
            FacebookProductDTO(
                id="test2",
                title="Iogurte Natural",
                description="Iogurte Natural 1L",
                availability="in stock",
                status="active",
                condition="new",
                price=450,
                link="http://example.com/yogurt",
                image_link="http://example.com/yogurt.jpg",
                brand="DairyBrand",
                sale_price=450,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1000},
                    "ProductCategories": {
                        "557": "Leite Fermentado",
                        "290": "Iogurte",
                        "220": "Frios e Laticínios",
                    },
                },
            ),
            FacebookProductDTO(
                id="test3",
                title="Produto 1000kg",
                description="Descrição do Produto",
                availability="in stock",
                status="active",
                condition="new",
                price=1000,
                link="http://example.com/product1",
                image_link="http://example.com/image1.jpg",
                brand="TestBrand",
                sale_price=1000,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1},
                    "ProductCategories": {"category": "padaria"},
                },
            ),
            FacebookProductDTO(
                id="test4",
                title="Produto",
                description="Descrição 1000ml",
                availability="in stock",
                status="active",
                condition="new",
                price=200,
                link="http://example.com/product2",
                image_link="http://example.com/image2.jpg",
                brand="TestBrand2",
                sale_price=200,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1},
                    "ProductCategories": {"category": "padaria"},
                },
            ),
            FacebookProductDTO(
                id="test5",
                title="Pequeno Produto",
                description="Peso menor que um kg",
                availability="in stock",
                status="active",
                condition="new",
                price=50,
                link="http://example.com/product3",
                image_link="http://example.com/image3.jpg",
                brand="TestBrand3",
                sale_price=50,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 0.5},
                    "ProductCategories": {"category": "hortifruti"},
                },
            ),
            FacebookProductDTO(
                id="test6",
                title="Grande Produto",
                description="Peso acima de um milhar",
                availability="in stock",
                status="active",
                condition="new",
                price=1050,
                link="http://example.com/product4",
                image_link="http://example.com/image4.jpg",
                brand="TestBrand4",
                sale_price=1050,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1050},
                    "ProductCategories": {"category": "hortifruti"},
                },
            ),
            FacebookProductDTO(
                id=24546,
                title="Carne molida de cordero Majada",
                description="Disfruta todos los mejores productos que tiene Majada para ti",
                availability="in stock",
                status="Active",
                condition="new",
                price=1164000,
                link="https://tiendasjumbo.co//batata-x-500-g/p?idsku=33689",
                image_link="https://jumbocolombiaio.vteximg.com.br/arquivos/ids/205437/2042.jpg",
                brand="A GRANEL",
                sale_price=1164000,
                product_details={
                    "Dimension": {"weight": 500.0},
                    "UnitMultiplier": 1.0,
                    "ProductCategories": {
                        "2000045": "carne y pollo",
                        "2000001": "Supermercado",
                    },
                },
            ),
        ]


class TestRoundUpCalculateByWeight(MockProductsDTO):
    def setUp(self):
        super().setUp()
        self.rule = RoundUpCalculateByWeight()

    def test_apply_rounding_up_product_1(self):
        product = self.products[0]

        before_title = product.title
        expected_title = f"{before_title} Unidade"
        expected_description = (
            product.description + " - Aprox. 500g, Preço do KG: R$ 24.40"
        )
        product.price = 2439
        expected_price = 1220

        self.rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, expected_price)
        self.assertEqual(product.sale_price, expected_price)

    def test_not_apply_rule(self):
        product = self.products[1]

        before_title = product.title
        expected_title = f"{before_title}"
        before_description = product.description
        expected_description = before_description

        self.rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, 450)
        self.assertEqual(product.sale_price, 450)

    def test_title_ends_with_unit_indicator(self):
        product = self.products[2]
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_description_ends_with_unit_indicator(self):
        product = self.products[3]
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_weight_less_than_one_kg(self):
        product = self.products[4]
        weight = self.rule._get_weight(product)
        self.assertEqual(self.rule._format_grams(weight), "500g")

    def test_format_grams_above_thousand(self):
        product = self.products[5]
        weight = self.rule._get_weight(product)
        self.assertEqual(self.rule._format_grams(weight), "1.050g")


class TestCalculateByWeightCO(MockProductsDTO):
    def setUp(self):
        super().setUp()
        self.rule = CalculateByWeightCO()

    def test_apply_with_increase(self):
        product = self.products[-1]

        initial_price = product.price
        product.sale_price = initial_price

        self.rule.apply(product)

        ten_percent = initial_price * 0.10
        expected_price = initial_price + ten_percent

        self.assertAlmostEqual(product.price, expected_price, places=1)
        self.assertAlmostEqual(product.sale_price, expected_price, places=1)

    def test_apply_without_increase(self):
        product = self.products[
            4
        ]  # A product that doesn't qualify for a price increase

        product.price = 50
        product.sale_price = 50
        self.rule.apply(product)
        # Assert that the price remains the same
        self.assertEqual(product.price, 50)
        self.assertEqual(product.sale_price, 50)


class TestExcludeAlcoholicDrinks(MockProductsDTO):
    def setUp(self):
        super().setUp()
        self.rule = ExcludeAlcoholicDrinks()

    def test_apply_excludes_alcohol(self):
        # Mock a product that belongs to the alcoholic category
        product = FacebookProductDTO(
            id="test_alcohol",
            title="Wine Bottle",
            description="Red wine",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="Brand Name",
            product_details={
                "ProductCategories": {"1": "vinos y licores"},
            },
        )

        result = self.rule.apply(product)
        self.assertFalse(result)  # Expect the rule to exclude this product

    def test_apply_non_alcoholic(self):
        product = self.products[0]  # A non-alcoholic product

        result = self.rule.apply(product)
        self.assertTrue(result)  # Expect the rule to pass this product


class TestCurrencyCOP(MockProductsDTO):
    def setUp(self):
        super().setUp()
        self.rule = CurrencyCOP()

    def test_format_cop_price(self):
        product = self.products[0]

        self.rule.apply(product)

        # Assert that the prices have been formatted correctly
        self.assertEqual(product.price, "24.39 COP")
        self.assertEqual(product.sale_price, "24.39 COP")


class TestSetDefaultImageURL(MockProductsDTO):
    def setUp(self):
        super().setUp()
        self.rule = SetDefaultImageURL()

    def test_set_image_url(self):
        product = self.products[0]
        product.product_details["ImageUrl"] = "http://example.com/new_image.jpg"

        self.rule.apply(product)

        # Check if the image link is set correctly
        self.assertEqual(product.image_link, "http://example.com/new_image.jpg")
