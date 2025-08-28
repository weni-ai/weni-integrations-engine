from .unifies_id_with_salles_channel import UnifiesIdWithSallesChannel
from .currency_pt_br import CurrencyBRL
from .calculate_by_weight import CalculateByWeight
from .exclude_alcoholic_drinks import ExcludeAlcoholicDrinks
from .unifies_id_with_seller import UnifiesIdWithSeller
from .calculate_by_weight_co import CalculateByWeightCO
from .currency_co import CurrencyCOP
from .round_up_calculate_by_weight import RoundUpCalculateByWeight
from .categories_by_seller_gbarbosa import CategoriesBySeller
from .use_extra_imgs import UseExtraImgs
from .use_rich_description import UseRichDescription
from .set_default_image_url import SetDefaultImageURL
from .exclude_categories_co import ExcludeCustomizedCategoriesCO
from .calculate_by_area import CalculateByArea
from .currency_pt_br_round_floor import CurrencyBRLRoudingFloor
from .currency_clp import CurrencyCLP
from .currency_ars import CurrencyARS
from .currency_gtq import CurrencyGTQ


"""
When configuring rules in an application, the order of the list in the App
will be the order in which the rules will be applied
"""
RULE_MAPPINGS = {
    "currency_pt_br": CurrencyBRL,
    "calculate_by_weight": CalculateByWeight,
    "exclude_alcoholic_drinks": ExcludeAlcoholicDrinks,
    "unifies_id_with_seller": UnifiesIdWithSeller,
    "calculate_by_weight_co": CalculateByWeightCO,
    "currency_co": CurrencyCOP,
    "round_up_calculate_by_weight": RoundUpCalculateByWeight,
    "categories_by_seller_gbarbosa": CategoriesBySeller,
    "use_extra_imgs": UseExtraImgs,
    "use_rich_description": UseRichDescription,
    "set_default_image_url": SetDefaultImageURL,
    "exclude_categories_co": ExcludeCustomizedCategoriesCO,
    "calculate_by_area": CalculateByArea,
    "currency_pt_br_round_floor": CurrencyBRLRoudingFloor,
    "currency_clp": CurrencyCLP,
    "currency_ars": CurrencyARS,
    "unifies_id_with_salles_channel": UnifiesIdWithSallesChannel,
    "currency_gtq": CurrencyGTQ,
}
