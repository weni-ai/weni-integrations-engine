# marketplace/services/vtex/business/rules/rule_mappings.py
from .currency_pt_br import CurrencyBRL
from .calculate_by_weight import CalculateByWeight
from .exclude_alcoholic_drinks import ExcludeAlcoholicDrinks
from .unifies_id_with_seller import UnifiesIdWithSeller
from .round_up_calculate_by_weight import RoundUpCalculateByWeight


RULE_MAPPINGS = {
    "currency_pt_br": CurrencyBRL,
    "calculate_by_weight": CalculateByWeight,
    "exclude_alcoholic_drinks": ExcludeAlcoholicDrinks,
    "unifies_id_with_seller": UnifiesIdWithSeller,
    "round_up_calculate_by_weight": RoundUpCalculateByWeight,
}
