"""
Electricity-only estimation based on pylovo CONSUMER_CATEGORIES definitions.

Research-backed benchmarks updated from:
  - Stromspiegel 2025 (co2online / BMWK) — 57,000 real household bills
    https://www.stromspiegel.de/stromverbrauch-verstehen/stromverbrauch-im-haushalt/
  - BDEW standard load profiles (H0, G0–G6, L0–L2) and sector statistics
    https://www.bdew.de
  - DIN 18015-1:2020-05 — coincidence factors for residential installations
  - AMEV 2019 — measured peak loads for 1,270 German public buildings
  - EHI Retail Institute 2024 — retail electricity benchmarks
  - MDPI / González et al. 2018 — German hospital energy benchmarks
  - CIBSE TM46:2008 — non-residential energy benchmarks
"""

from typing import Dict, Optional
import re
import math

from src.config_loader import CONSUMER_CATEGORIES, PEAK_LOAD_HOUSEHOLD


def _to_float(value) -> Optional[float]:
    """Convert numeric-ish values to float while handling NaN/None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return f


class BuildingEnergyEstimator:
    """
    Estimates electricity demand directly from configured f_class categories.

    All benchmark values are sourced from authoritative German and EU publications
    (2018–2025). See module docstring for full citation list.

    Key design decisions (backed by research):
    ─────────────────────────────────────────
    • Residential electricity (appliances/lighting) does NOT vary significantly
      with building age — that is a heating energy phenomenon (TABULA).
      Age factors are therefore applied as a moderate correction to total
      household electricity, reflecting older appliance efficiency in older stock.
    • Building age multipliers are calibrated for Germany with EnEV-2002
      buildings as the 1.0 baseline.
    • Peak load diversity follows DIN 18015-1:2020 coincidence curve, approximated
      as g(N) = N^(-0.45) which fits the DIN table within ±5 % for N = 1–200.
    • Non-residential kWh/m² benchmarks align with BDEW Verbrauchskennwerte,
      Bekanntmachung 2015, EHI 2024, and CIBSE TM46.
    • Full load hours are individual-building values (not SLP aggregate values),
      appropriate for sizing calculations.
    • Supermarket electricity (284 kWh/m²) is on Verkaufsfläche basis (EHI 2024);
      the model uses a discounted value on gross floor area.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Residential reference constants
    # ──────────────────────────────────────────────────────────────────────────

    _DEFAULT_AREA_FOR_HOUSEHOLD = 100.0  # m² fallback when area-based calc needed

    # Stromspiegel 2025 — annual kWh/household WITHOUT electric hot water
    # Source: co2online Stromspiegel 2025 (published May 2025, n=57,000 bills)
    # Mid-range (D-class) values used as the representative average.
    _STROMSPIEGEL_2025_APARTMENT_KWH = {
        1: 1_200.0,  # 1-person apartment
        2: 1_900.0,  # 2-person apartment
        3: 2_400.0,  # 3-person apartment
        4: 2_600.0,  # 4-person apartment
        5: 3_100.0,  # 5-person apartment
    }
    _STROMSPIEGEL_2025_HOUSE_KWH = {
        1: 1_800.0,  # 1-person house
        2: 2_700.0,  # 2-person house
        3: 3_500.0,  # 3-person house
        4: 3_800.0,  # 4-person house
        5: 4_500.0,  # 5-person house
    }

    # Stromspiegel 2025 class upper bounds (kWh/yr) — WITHOUT electric hot water
    # Each list: [A_upper, B_upper, C_upper, D_upper, E_upper, F_upper]
    # G class = everything above F_upper
    _STROMSPIEGEL_2025_HOUSE_BOUNDS: Dict[int, list] = {
        1: [1_100, 1_500, 1_700, 2_000, 2_400, 3_000],
        2: [1_900, 2_200, 2_500, 2_900, 3_300, 4_000],
        3: [2_400, 2_800, 3_200, 3_600, 4_000, 5_000],
        4: [2_600, 3_100, 3_500, 4_000, 4_500, 5_600],
        5: [3_000, 3_600, 4_100, 4_800, 5_500, 7_000],
    }
    _STROMSPIEGEL_2025_APARTMENT_BOUNDS: Dict[int, list] = {
        1: [700, 900, 1_100, 1_400, 1_500, 2_000],
        2: [1_200, 1_500, 1_700, 2_000, 2_400, 3_000],
        3: [1_500, 1_900, 2_200, 2_600, 3_000, 3_700],
        4: [1_700, 2_000, 2_500, 2_900, 3_400, 4_100],
        5: [2_000, 2_400, 2_800, 3_500, 4_000, 5_000],
    }
    _ENERGY_LABEL_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}

    # Stromspiegel 2025 — annual kWh/household WITH electric hot water
    _STROMSPIEGEL_2025_APARTMENT_EWH_KWH = {
        1: 1_500.0, 2: 2_500.0, 3: 3_200.0, 4: 3_500.0, 5: 4_100.0,
    }
    _STROMSPIEGEL_2025_HOUSE_EWH_KWH = {
        1: 2_400.0, 2: 3_500.0, 3: 4_500.0, 4: 4_700.0, 5: 5_500.0,
    }
    # Class bounds WITH electric hot water
    _STROMSPIEGEL_2025_HOUSE_EWH_BOUNDS: Dict[int, list] = {
        1: [1_300, 1_600, 2_000, 2_300, 2_900, 4_000],
        2: [2_000, 2_500, 3_000, 3_500, 4_000, 5_500],
        3: [2_700, 3_400, 3_900, 4_500, 5_100, 7_000],
        4: [3_000, 3_700, 4_300, 5_000, 6_000, 7_900],
        5: [3_700, 4_600, 5_400, 6_300, 7_400, 10_000],
    }
    _STROMSPIEGEL_2025_APARTMENT_EWH_BOUNDS: Dict[int, list] = {
        1: [900, 1_200, 1_500, 1_700, 2_000, 2_700],
        2: [1_600, 2_000, 2_500, 2_800, 3_200, 4_000],
        3: [2_000, 2_500, 2_800, 3_300, 3_700, 4_500],
        4: [2_400, 2_800, 3_300, 3_700, 4_200, 4_900],
        5: [2_500, 3_700, 4_500, 5_000, 6_500, 8_000],
    }

    # Reference floor areas (m²) associated with each household size.
    # Derived from Destatis microcensus wohnen 2022 and Stromspiegel methodology.
    _STROMSPIEGEL_REF_AREA_APARTMENT = {1: 45.0, 2: 65.0, 3: 80.0, 4: 100.0, 5: 120.0}
    _STROMSPIEGEL_REF_AREA_HOUSE = {1: 90.0, 2: 115.0, 3: 140.0, 4: 160.0, 5: 190.0}

    # Per-household peak factor relative to 2-person reference (BDEW H0 profile analysis)
    _HOUSEHOLD_PEAK_FACTOR = {1: 0.80, 2: 1.00, 3: 1.10, 4: 1.20, 5: 1.30}

    # Per-household base peak load (kW) — DIN 18015-1:2020
    _BASE_PEAK_LOAD_KW = 2.5

    # Area scaling for single-family electricity (sub-linear)
    _RESIDENTIAL_AREA_EXPONENT = 0.15
    _RESIDENTIAL_PEAK_AREA_EXPONENT = 0.10
    _RESIDENTIAL_AREA_FACTOR_MIN = 0.70
    _RESIDENTIAL_AREA_FACTOR_MAX = 1.35
    _RESIDENTIAL_PEAK_AREA_FACTOR_MIN = 0.85
    _RESIDENTIAL_PEAK_AREA_FACTOR_MAX = 1.25

    # Multi-household apartment building parameters
    _APARTMENT_HOUSEHOLD_COUNT_MAX = 80.0
    _MULTI_DWELLING_MIN_TOTAL_AREA_M2 = 300.0
    _MULTI_DWELLING_MIN_FLOORS = 3
    _MULTI_DWELLING_MIN_HOUSEHOLDS = 2.0
    _MULTI_DWELLING_REF_AREA_MIN_M2 = 70.0
    _MULTI_DWELLING_MIN_UNIT_AREA_M2 = 35.0  # smallest viable apartment in Germany

    # DIN 18015-1:2020 coincidence: peak ∝ N^0.55
    _APARTMENT_PEAK_DIVERSITY_EXPONENT = 0.55

    # ──────────────────────────────────────────────────────────────────────────
    # DIN 18015-1 effective power (PSeff) — Stromnetz Berlin TAB NS Nord 2019
    # Tabelle 2: "Effektiver Leistungsbedarf für Wohneinheiten"
    # Sorted (N_dwellings, PSeff_kVA). Tail rule: +0.2 kVA per dwelling >100
    # (without EWH) or +0.4 kVA per dwelling >100 (with EWH).
    # ──────────────────────────────────────────────────────────────────────────
    _DIN_PSEFF_NO_EWH: list = [
        (1, 14.5), (2, 24.0), (3, 32.0), (4, 37.0), (5, 41.0),
        (6, 44.0), (7, 46.0), (8, 48.0), (9, 50.0), (10, 55.0),
        (12, 57.0), (14, 59.0), (16, 61.0), (18, 63.0), (20, 72.0),
        (25, 77.0), (30, 80.0), (40, 88.0), (50, 95.0),
        (60, 98.0), (70, 101.0), (80, 104.0), (90, 106.0), (100, 108.0),
    ]
    _DIN_PSEFF_WITH_EWH: list = [
        (1, 34.0), (2, 52.0), (3, 63.0), (4, 73.0), (5, 81.0),
        (6, 86.0), (7, 91.0), (8, 95.0), (9, 99.0), (10, 105.0),
        (12, 111.0), (14, 117.0), (16, 122.0), (18, 127.0), (20, 131.0),
        (25, 142.0), (30, 151.0), (40, 167.0), (50, 180.0),
        (60, 188.0), (70, 193.0), (80, 198.0), (90, 202.0), (100, 205.0),
    ]
    _DIN_TAIL_PER_DWELLING_NO_EWH = 0.2   # kVA per additional dwelling >100
    _DIN_TAIL_PER_DWELLING_WITH_EWH = 0.4

    _APARTMENT_LIKE_CLASSES = {"apartment", "apartments", "residential", "dormitory", "flat"}
    _HOUSE_LIKE_CLASSES = {
        "house", "detached", "semidetached_house", "terrace", "townhouse",
        "bungalow", "farmhouse", "houseboat", "boathouse", "boat_house",
        "allotment_house", "villa",
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Full load hours — INDIVIDUAL BUILDING values (not SLP aggregate)
    # ──────────────────────────────────────────────────────────────────────────
    _FULL_LOAD_HOURS = {
        "residential":    1_200,
        "commercial":     2_000,
        "public":         2_200,
        "industrial":     3_500,
        "agricultural":   2_800,
        "infrastructure": 4_000,
        "default":        2_000,
    }

    # Fine-grained full load hours by specific building sub-type
    _FULL_LOAD_HOURS_BY_FCLASS = {
        # Residential
        "house": 900, "detached": 900, "semidetached_house": 950, "terrace": 950,
        "bungalow": 900, "apartments": 1_800, "apartment": 1_800, "dormitory": 2_200,
        "residential": 1_200,
        # Commercial
        "office": 2_676, "offices": 2_676, "retail": 2_200, "supermarket": 4_500,
        "shop": 2_200, "kiosk": 2_200, "mall": 3_000, "commercial": 2_000,
        "hotel": 3_000, "motel": 3_000, "hostel": 2_800, "restaurant": 2_000,
        "cafe": 1_800, "fast_food": 2_500, "fuel": 4_000, "bank": 1_800,
        "hairdresser": 1_600, "beauty": 1_600, "laundry": 2_500, "dry_cleaning": 2_500,
        "car_wash": 2_500, "storage": 1_200, "warehouse": 1_500, "parking": 4_200,
        "garage": 1_500,
        # Public / civic
        "school": 2_066, "kindergarten": 1_400, "university": 2_200, "college": 2_000,
        "library": 1_800, "hospital": 5_000, "clinic": 2_500, "doctors": 1_800,
        "dentist": 1_600, "pharmacy": 1_800, "social_facility": 1_800,
        "community_centre": 1_600, "civic": 1_800, "government": 1_800,
        "courthouse": 1_800, "police": 3_598, "fire_station": 3_000,
        "post_office": 1_800, "museum": 2_000, "theatre": 2_200, "cinema": 2_500,
        "arts_centre": 1_800, "sports_centre": 2_500, "stadium": 1_200,
        "sports_hall": 2_000, "swimming_pool": 4_500, "gymnasium": 2_000,
        "church": 1_000, "cathedral": 1_200, "mosque": 1_000, "synagogue": 1_000,
        "temple": 1_000, "place_of_worship": 1_000,
        # Industrial
        "industrial": 3_500, "factory": 3_500, "manufacture": 3_500,
        "workshop": 2_000, "mill": 4_000, "cold_storage": 6_000,
        "sewage": 5_500, "water_works": 5_500, "slaughterhouse": 3_000,
        # Agricultural
        "farm": 3_000, "barn": 2_000, "greenhouse": 4_500, "stable": 3_500,
        "cowshed": 4_000, "farmhouse": 900,
        # Infrastructure
        "train_station": 5_000, "bus_station": 4_000, "ferry_terminal": 4_500,
        "airport": 5_500, "substation": 7_000, "power": 7_000,
        "pumping_station": 6_000, "service": 2_500, "data_center": 7_500,
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Non-residential specific electricity demand benchmarks (kWh/m²/year)
    # ──────────────────────────────────────────────────────────────────────────
    _SPECIFIC_ELECTRICITY_KWH_M2 = {
        # Residential (electricity for appliances/lighting only)
        "house": 25.0, "detached": 25.0, "semidetached_house": 25.0,
        "terrace": 23.0, "bungalow": 25.0, "villa": 22.0,
        "apartments": 20.0, "apartment": 20.0, "dormitory": 25.0, "residential": 22.0,
        # Office / business
        "office": 35.0, "offices": 35.0, "commercial": 40.0,
        # Retail / shopping
        "retail": 71.0, "shop": 50.0, "kiosk": 55.0, "supermarket": 200.0,
        "mall": 45.0, "department_store": 90.0, "hairdresser": 45.0, "beauty": 40.0,
        "laundry": 80.0, "dry_cleaning": 90.0, "car_wash": 60.0, "fuel": 80.0,
        "bank": 70.0, "post_office": 40.0,
        # Hospitality / gastronomy
        "hotel": 60.0, "motel": 50.0, "hostel": 40.0, "restaurant": 95.0,
        "cafe": 80.0, "fast_food": 170.0,
        # Storage / logistics
        "storage": 15.0, "warehouse": 30.0, "cold_storage": 145.0,
        "parking": 15.0, "garage": 20.0,
        # Public / civic
        "school": 21.0, "kindergarten": 22.0, "university": 70.0, "college": 50.0,
        "library": 40.0, "hospital": 100.0, "clinic": 60.0, "doctors": 45.0,
        "dentist": 40.0, "pharmacy": 50.0, "social_facility": 30.0,
        "community_centre": 25.0, "civic": 35.0, "government": 40.0,
        "courthouse": 35.0, "police": 54.0, "fire_station": 35.0,
        "museum": 55.0, "theatre": 60.0, "cinema": 80.0, "arts_centre": 45.0,
        "sports_centre": 60.0, "sports_hall": 40.0, "swimming_pool": 150.0,
        "gymnasium": 35.0, "stadium": 20.0,
        # Religion
        "church": 10.0, "cathedral": 12.0, "mosque": 8.0, "synagogue": 8.0,
        "temple": 8.0, "place_of_worship": 9.0,
        # Industrial
        "industrial": 80.0, "factory": 100.0, "manufacture": 100.0,
        "workshop": 50.0, "mill": 90.0, "sewage": 80.0, "water_works": 70.0,
        "slaughterhouse": 100.0,
        # Agricultural
        "farm": 20.0, "barn": 10.0, "greenhouse": 80.0, "stable": 25.0,
        "cowshed": 35.0, "farmhouse": 22.0, "agricultural": 20.0,
        # Infrastructure
        "train_station": 80.0, "bus_station": 40.0, "ferry_terminal": 60.0,
        "airport": 120.0, "substation": 50.0, "pumping_station": 90.0,
        "data_center": 1_000.0, "service": 35.0,
    }

    # Peak load density W/m² for non-residential buildings
    _PEAK_LOAD_W_M2 = {
        "house": 8.0, "apartments": 10.0, "dormitory": 12.0,
        "office": 13.0, "offices": 13.0, "commercial": 25.0,
        "retail": 35.0, "shop": 30.0, "supermarket": 50.0, "mall": 35.0,
        "fuel": 40.0, "bank": 40.0, "restaurant": 80.0, "cafe": 50.0,
        "fast_food": 100.0, "hotel": 30.0, "hostel": 20.0,
        "school": 10.0, "kindergarten": 15.0, "university": 40.0,
        "hospital": 65.0, "clinic": 35.0, "doctors": 25.0,
        "police": 15.0, "fire_station": 25.0, "museum": 30.0,
        "theatre": 40.0, "cinema": 30.0, "sports_centre": 40.0,
        "swimming_pool": 80.0, "gymnasium": 20.0,
        "industrial": 60.0, "factory": 80.0, "warehouse": 15.0,
        "cold_storage": 60.0, "workshop": 35.0, "sewage": 50.0,
        "farm": 12.0, "greenhouse": 40.0, "cowshed": 20.0, "stable": 15.0,
        "parking": 8.0, "train_station": 50.0, "airport": 70.0, "substation": 30.0,
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Building age / construction year multipliers
    # Baseline: EnEV 2002 buildings (2002–2009) = 1.0
    # ──────────────────────────────────────────────────────────────────────────

    _AGE_MULTIPLIERS_ANNUAL = {
        "<1945":     1.22,
        "1945-1978": 1.16,
        "1979-1983": 1.11,
        "1984-1994": 1.08,
        "1995-2001": 1.04,
        "2002-2009": 1.00,
        "2010-2015": 0.95,
        "2016-2023": 0.90,
        ">2023":     0.90,
    }

    _AGE_MULTIPLIERS_PEAK = {
        "<1945":     1.14,
        "1945-1978": 1.11,
        "1979-1983": 1.07,
        "1984-1994": 1.06,
        "1995-2001": 1.03,
        "2002-2009": 1.00,
        "2010-2015": 0.97,
        "2016-2023": 0.94,
        ">2023":     0.94,
    }

    _NONRES_AGE_MULTIPLIERS_ANNUAL = {
        "<1945":     1.00,
        "1945-1978": 1.00,
        "1979-1983": 1.00,
        "1984-1994": 1.00,
        "1995-2001": 1.00,
        "2002-2009": 1.00,
        "2010-2015": 1.00,
        "2016-2023": 1.00,
        ">2023":     1.00,
    }
    _NONRES_AGE_MULTIPLIERS_PEAK = {
        "<1945":     1.00,
        "1945-1978": 1.00,
        "1979-1983": 1.00,
        "1984-1994": 1.00,
        "1995-2001": 1.00,
        "2002-2009": 1.00,
        "2010-2015": 1.00,
        "2016-2023": 1.00,
        ">2023":     1.00,
    }

    @staticmethod
    def _year_to_age_key(year: int) -> str:
        if year < 1945:   return "<1945"
        if year <= 1978:  return "1945-1978"
        if year <= 1983:  return "1979-1983"
        if year <= 1994:  return "1984-1994"
        if year <= 2001:  return "1995-2001"
        if year <= 2009:  return "2002-2009"
        if year <= 2015:  return "2010-2015"
        if year <= 2023:  return "2016-2023"
        return ">2023"

    def _get_age_multiplier(
        self,
        construction_year: Optional[int],
        renovation_year: Optional[int] = None,
        is_residential: bool = True,
        for_peak: bool = False,
    ) -> float:
        """Return an electricity demand age multiplier.

        Renovation year overrides construction year when >= 2002.
        """
        if renovation_year is not None and renovation_year >= 2002:
            year = renovation_year
        elif construction_year is None:
            return 1.0
        else:
            year = int(construction_year)

        key = self._year_to_age_key(year)

        if is_residential:
            table = self._AGE_MULTIPLIERS_PEAK if for_peak else self._AGE_MULTIPLIERS_ANNUAL
        else:
            table = self._NONRES_AGE_MULTIPLIERS_PEAK if for_peak else self._NONRES_AGE_MULTIPLIERS_ANNUAL

        return table[key]

    def _age_factor(
        self,
        year_of_construction: Optional[int],
        is_residential: bool = True,
        renovation_year: Optional[int] = None,
    ) -> float:
        """Thin wrapper — returns annual age multiplier."""
        return self._get_age_multiplier(
            construction_year=year_of_construction,
            renovation_year=renovation_year,
            is_residential=is_residential,
            for_peak=False,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Aliases and type mappings
    # ──────────────────────────────────────────────────────────────────────────
    _ALIASES = {
        "semi_detached": "semidetached_house",
        "semi-detached": "semidetached_house",
        "semi_detached_house": "semidetached_house",
        "town_house": "terrace",
        "townhouse": "terrace",
        "community_center": "community_centre",
        "doctor": "doctors",
        "boat_house": "boathouse",
        "single_family": "house",
        "flat": "apartments",
        "flats": "apartments",
        "apartment_block": "apartments",
        "apartment_house": "apartments",
        "block_of_flats": "apartments",
        "multifamily": "apartments",
        "multi_family": "apartments",
        "detached_house": "house",
        "villa": "house",
        "bungalow": "house",
        "dorm": "dormitory",
        "student_housing": "dormitory",
        "office_building": "office",
        "office_block": "office",
        "superstore": "supermarket",
        "hypermarket": "supermarket",
        "convenience": "shop",
        "convenience_store": "shop",
        "pub": "restaurant",
        "bar": "restaurant",
        "nightclub": "restaurant",
        "food_court": "restaurant",
        "college": "university",
        "gymnasium": "school",
        "medical_center": "clinic",
        "health_centre": "clinic",
        "health_center": "clinic",
        "surgery": "doctors",
        "vet": "doctors",
        "veterinary": "doctors",
        "sports_hall": "sports_centre",
        "leisure_centre": "sports_centre",
        "leisure_center": "sports_centre",
        "fire_house": "fire_station",
        "shed": "barn",
        "hut": "barn",
        "cowhouse": "cowshed",
        "pigsty": "stable",
        "glasshouse": "greenhouse",
        "packinghouse": "warehouse",
        "distribution_center": "warehouse",
        "distribution_centre": "warehouse",
        "logistics": "warehouse",
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Construction
    # ──────────────────────────────────────────────────────────────────────────

    def __init__(self):
        self._consumer_index = self._build_consumer_index()
        self._default_row = self._consumer_index.get("_default")
        self._parent_templates = self._build_parent_templates()

    # ──────────────────────────────────────────────────────────────────────────
    # Index construction helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(value: str) -> str:
        if not value:
            return "yes"
        norm = str(value).strip().lower()
        norm = re.sub(r"[\s\-/]+", "_", norm)
        norm = re.sub(r"[^a-z0-9_]", "", norm)
        norm = re.sub(r"_+", "_", norm).strip("_")
        if norm in {"", "unknown", "none", "null", "nan", "n_a", "na"}:
            return "yes"
        return norm

    def _build_consumer_index(self) -> Dict[str, Dict]:
        index: Dict[str, Dict] = {}
        if CONSUMER_CATEGORIES is None or CONSUMER_CATEGORIES.empty:
            return index

        for _, row in CONSUMER_CATEGORIES.iterrows():
            definition = self._normalize(row.get("definition"))
            if not definition:
                continue

            parent = self._normalize(row.get("parent_category") or "commercial")
            load_method = str(row.get("load_method") or "area").strip().lower()
            if load_method not in {"household", "area"}:
                load_method = "area"

            peak_load = _to_float(row.get("peak_load"))
            if peak_load is None and load_method == "household":
                peak_load = float(PEAK_LOAD_HOUSEHOLD)

            index[definition] = {
                "definition": definition,
                "parent_category": parent,
                "load_method": load_method,
                "peak_load": peak_load,
                "yearly_consumption": _to_float(row.get("yearly_consumption")),
                "peak_load_per_m2": _to_float(row.get("peak_load_per_m2")),
                "yearly_consumption_per_m2": _to_float(row.get("yearly_consumption_per_m2")),
                "sim_factor": _to_float(row.get("sim_factor")),
            }

        return index

    def _build_parent_templates(self) -> Dict[str, Dict]:
        templates: Dict[str, Dict] = {}
        for row in self._consumer_index.values():
            parent = str(row.get("parent_category") or "commercial")
            if parent not in templates:
                templates[parent] = row
        return templates

    # ──────────────────────────────────────────────────────────────────────────
    # Classification helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _infer_parent_category(self, f_class: str) -> str:
        fc = self._normalize(f_class)
        if any(k in fc for k in (
            "house", "apartment", "residential", "dormitory",
            "villa", "terrace", "townhouse", "bungalow", "flat",
        )):
            return "residential"
        if any(k in fc for k in (
            "school", "hospital", "university", "college", "church",
            "government", "museum", "theatre", "clinic", "public",
            "police", "fire", "library", "sports", "swimming", "civic",
            "community", "social", "religious", "mosque", "cathedral",
            "temple", "synagogue",
        )):
            return "public"
        if any(k in fc for k in (
            "factory", "industrial", "warehouse", "workshop",
            "manufactur", "mill", "silo", "sewage", "water_works",
            "slaughter", "cold_storage",
        )):
            return "industrial"
        if any(k in fc for k in (
            "farm", "barn", "greenhouse", "agricultural",
            "stable", "cowshed", "pigsty", "orchard",
        )):
            return "agricultural"
        if any(k in fc for k in (
            "station", "terminal", "substation", "utility", "power",
            "bridge", "airport", "parking", "infrastructure", "pumping",
            "data_center",
        )):
            return "infrastructure"
        return "commercial"

    def _resolve_row(self, building_type: str) -> Dict:
        f_class = self._normalize(building_type)
        f_class = self._ALIASES.get(f_class, f_class)
        row = self._consumer_index.get(f_class)
        if row:
            return row

        parent = self._infer_parent_category(f_class)
        template = self._parent_templates.get(parent) or self._default_row
        if template:
            synthetic = dict(template)
            synthetic["definition"] = f_class
            synthetic["parent_category"] = parent
            return synthetic

        return {
            "definition": f_class or "yes",
            "parent_category": parent,
            "load_method": "area",
            "peak_load": None,
            "yearly_consumption": None,
            "peak_load_per_m2": None,
            "yearly_consumption_per_m2": 40.0,
            "sim_factor": 0.5,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Residential sizing helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _estimate_residential_household_size(self, f_class: str, area_m2: float) -> int:
        """Estimate mean household size from building type and floor area."""
        fc = self._normalize(f_class)
        area = max(float(area_m2 or 0.0), 1.0)

        if fc in self._APARTMENT_LIKE_CLASSES:
            if area < 45:   return 1
            if area < 75:   return 2
            if area < 100:  return 3
            if area < 130:  return 4
            return 5

        if fc in self._HOUSE_LIKE_CLASSES:
            if area < 80:   return 1
            if area < 120:  return 2
            if area < 160:  return 3
            if area < 220:  return 4
            return 5

        if area < 55:   return 1
        if area < 90:   return 2
        if area < 130:  return 3
        if area < 180:  return 4
        return 5

    @staticmethod
    def _normalize_household_size(household_size: Optional[int]) -> Optional[int]:
        if household_size is None:
            return None
        try:
            value = int(household_size)
        except (TypeError, ValueError):
            return None
        return max(1, min(5, value))

    @staticmethod
    def _normalize_num_floors(num_floors: Optional[int]) -> Optional[int]:
        if num_floors is None:
            return None
        try:
            floors = int(num_floors)
        except (TypeError, ValueError):
            return None
        return floors if floors > 0 else None

    @staticmethod
    def _normalize_energy_label(label: Optional[str]) -> Optional[str]:
        if label is None:
            return None
        normalized = str(label).strip().upper()
        if normalized in ("A", "B", "C", "D", "E", "F", "G"):
            return normalized
        return None

    def _energy_label_factor(
        self, is_apartment: bool, household_size: int, energy_label: Optional[str],
        hot_water_electric: bool = False,
    ) -> float:
        """Scaling factor relative to D-class for a Stromspiegel energy label."""
        label = self._normalize_energy_label(energy_label)
        if label is None or label == "D":
            return 1.0

        if hot_water_electric:
            bounds = (self._STROMSPIEGEL_2025_APARTMENT_EWH_BOUNDS if is_apartment
                      else self._STROMSPIEGEL_2025_HOUSE_EWH_BOUNDS)
        else:
            bounds = (self._STROMSPIEGEL_2025_APARTMENT_BOUNDS if is_apartment
                      else self._STROMSPIEGEL_2025_HOUSE_BOUNDS)
        hh = min(max(household_size, 1), 5)
        b = bounds[hh]
        d_mid = (b[2] + b[3]) / 2.0  # D-class midpoint

        idx = self._ENERGY_LABEL_INDEX[label]
        if idx == 0:      # A
            class_mid = b[0] * 0.85
        elif idx <= 5:    # B–F
            class_mid = (b[idx - 1] + b[idx]) / 2.0
        else:             # G
            class_mid = b[5] * 1.15

        return class_mid / d_mid if d_mid > 0 else 1.0

    def _is_multi_household_residential(
        self, f_class: str, area_m2: float, num_floors: Optional[int],
        household_size: Optional[int] = None,
    ) -> bool:
        """Return True when residential load should be modelled as multiple dwelling units.

        Rules for house-like classes:
        - Total area ≥ 300 m² → always multi-household (large building)
        - 2+ floors with floor area ≥ 35 m² AND total area exceeds the largest
          single-family reference (190 m²) → multi-household
        Apartment-like classes are always multi-household.

        NOTE: The reference area is intentionally NOT derived from household_size
        to prevent the classification from flipping when the user adjusts occupancy.
        """
        fc = self._normalize(f_class)
        area = max(float(area_m2 or 0.0), 1.0)
        floors = self._normalize_num_floors(num_floors)

        if fc in self._APARTMENT_LIKE_CLASSES:
            return True
        if fc in self._HOUSE_LIKE_CLASSES:
            if area >= self._MULTI_DWELLING_MIN_TOTAL_AREA_M2:
                return True
            if floors is not None and floors >= 2:
                floor_area = area / floors
                if floor_area < self._MULTI_DWELLING_MIN_UNIT_AREA_M2:
                    return False
                # Use the largest single-family reference (5-person house = 190 m²)
                # so the classification is stable regardless of household_size input.
                ref = max(self._STROMSPIEGEL_REF_AREA_HOUSE.values())
                if area > ref:
                    return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # DIN 18015-1 coincidence factor
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _din18015_coincidence_factor(n_units: float) -> float:
        """g(N) = N^(-0.45) for N >= 2; g(1) = 1.0 — kept for operational peak."""
        if n_units <= 1.0:
            return 1.0
        return n_units ** (-0.45)

    @classmethod
    def _din_pseff_kva(cls, n_units: float, with_ewh: bool = False) -> float:
        """DIN 18015-derived effective power via Stromnetz Berlin table + interpolation."""
        table = cls._DIN_PSEFF_WITH_EWH if with_ewh else cls._DIN_PSEFF_NO_EWH
        tail_rate = cls._DIN_TAIL_PER_DWELLING_WITH_EWH if with_ewh else cls._DIN_TAIL_PER_DWELLING_NO_EWH

        n = max(1.0, float(n_units))
        # Beyond last table point: linear tail
        last_n, last_kva = table[-1]
        if n >= last_n:
            return last_kva + (n - last_n) * tail_rate
        # Exact or interpolate
        for i in range(len(table) - 1):
            n0, kva0 = table[i]
            n1, kva1 = table[i + 1]
            if n0 <= n <= n1:
                t = (n - n0) / (n1 - n0) if n1 != n0 else 0.0
                return kva0 + t * (kva1 - kva0)
        return table[0][1]

    # ──────────────────────────────────────────────────────────────────────────
    # Scaling utilities
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _bounded_power_scale(
        ratio: float, exponent: float, min_factor: float, max_factor: float,
    ) -> float:
        if ratio <= 0:
            return min_factor
        factor = ratio ** exponent
        return max(min_factor, min(max_factor, factor))

    def _get_full_load_hours(self, f_class: str, parent: str) -> float:
        fc = self._normalize(f_class)
        flh = self._FULL_LOAD_HOURS_BY_FCLASS.get(fc)
        if flh is not None:
            return float(flh)
        return float(self._FULL_LOAD_HOURS.get(parent, self._FULL_LOAD_HOURS["default"]))

    def _get_specific_electricity(self, f_class: str, parent: str) -> float:
        """Return research-backed specific electricity demand (kWh/m²/year)."""
        fc = self._normalize(f_class)
        kwh_m2 = self._SPECIFIC_ELECTRICITY_KWH_M2.get(fc)
        if kwh_m2 is not None:
            return kwh_m2
        parent_defaults = {
            "residential": 22.0, "commercial": 40.0, "public": 35.0,
            "industrial": 80.0, "agricultural": 20.0, "infrastructure": 50.0,
        }
        return parent_defaults.get(parent, 40.0)

    def _get_peak_load_w_m2(self, f_class: str, parent: str) -> Optional[float]:
        fc = self._normalize(f_class)
        return self._PEAK_LOAD_W_M2.get(fc)

    # ──────────────────────────────────────────────────────────────────────────
    # Main estimation entry point
    # ──────────────────────────────────────────────────────────────────────────

    def estimate(
        self,
        building_type: str,
        area_m2: float,
        year_of_construction: Optional[int] = None,
        household_size: Optional[int] = None,
        num_floors: Optional[int] = None,
        renovation_year: Optional[int] = None,
        energy_label: Optional[str] = None,
        hot_water_electric: bool = False,
    ) -> Dict[str, float]:
        """
        Estimate annual electricity demand (kWh/year) and peak load (kW).

        Covers appliances, lighting, HVAC auxiliary, cooking.
        Hot water energy included only when hot_water_electric=True.
        """
        row = self._resolve_row(building_type)
        row_definition = str(row.get("definition") or self._normalize(building_type))
        parent = str(row.get("parent_category") or "commercial")
        load_method = str(row.get("load_method") or "area")
        area = max(float(area_m2 or 0.0), 1.0)

        is_residential = (parent == "residential")

        age_factor_annual = self._get_age_multiplier(
            year_of_construction, renovation_year, is_residential, for_peak=False
        )
        age_factor_peak = self._get_age_multiplier(
            year_of_construction, renovation_year, is_residential, for_peak=True
        )
        age_factor = age_factor_annual

        if renovation_year is not None and renovation_year >= 2002:
            effective_year = renovation_year
        else:
            effective_year = year_of_construction

        flh = self._get_full_load_hours(row_definition, parent)

        yearly_demand_base = 0.0
        peak_load = 0.0
        peak_connection_kva: Optional[float] = None
        household_size_used: Optional[int] = None
        estimated_households_used: Optional[float] = None

        # ── Household method (residential buildings) ──────────────────────────
        if load_method == "household":
            base_yearly = _to_float(row.get("yearly_consumption")) or 3_000.0
            base_peak_kw = _to_float(row.get("peak_load")) or self._BASE_PEAK_LOAD_KW

            if parent == "residential":
                norm_fc = self._normalize(row_definition)
                explicit_hh_size = self._normalize_household_size(household_size)
                is_multi = self._is_multi_household_residential(norm_fc, area, num_floors, explicit_hh_size)
                floors = self._normalize_num_floors(num_floors)
                per_floor_area = area / max(floors, 1) if floors is not None and floors >= 1 else area
                inferred_hh_size = self._estimate_residential_household_size(
                    "apartments" if is_multi else norm_fc,
                    per_floor_area if is_multi else area,
                )

                hh_size = explicit_hh_size or inferred_hh_size

                household_size_used = hh_size

                # Select Stromspiegel tables based on hot water type
                if hot_water_electric:
                    apartment_table = self._STROMSPIEGEL_2025_APARTMENT_EWH_KWH
                    house_table = self._STROMSPIEGEL_2025_HOUSE_EWH_KWH
                else:
                    apartment_table = self._STROMSPIEGEL_2025_APARTMENT_KWH
                    house_table = self._STROMSPIEGEL_2025_HOUSE_KWH

                if is_multi:
                    yearly_per_unit = apartment_table.get(hh_size, apartment_table[2])

                    # Use per-floor area as a proxy for per-unit area to infer occupants per dwelling.
                    inferred_hh_for_units = self._estimate_residential_household_size(
                        "apartments",
                        per_floor_area,
                    )
                    ref_area = self._STROMSPIEGEL_REF_AREA_APARTMENT.get(
                        inferred_hh_for_units, self._STROMSPIEGEL_REF_AREA_APARTMENT[2]
                    )

                    if norm_fc in self._HOUSE_LIKE_CLASSES:
                        ref_area = max(ref_area, self._MULTI_DWELLING_REF_AREA_MIN_M2)

                    area_ratio = area / max(ref_area, 1.0)
                    n_units = max(1.0, min(area_ratio, self._APARTMENT_HOUSEHOLD_COUNT_MAX))

                    if norm_fc in self._HOUSE_LIKE_CLASSES:
                        n_units = max(self._MULTI_DWELLING_MIN_HOUSEHOLDS, n_units)

                    # Each floor typically has at least one dwelling unit
                    if floors is not None and floors >= 2:
                        n_units = max(n_units, float(floors))

                    estimated_households_used = n_units
                    yearly_demand_base = yearly_per_unit * n_units * age_factor_annual

                    # Operational peak (heuristic coincidence)
                    peak_factor = self._HOUSEHOLD_PEAK_FACTOR.get(hh_size, 1.0)
                    g = self._din18015_coincidence_factor(n_units)
                    peak_load = base_peak_kw * peak_factor * n_units * g * age_factor_peak
                    # Connection peak (DIN 18015 / DSO table)
                    peak_connection_kva = self._din_pseff_kva(n_units, with_ewh=hot_water_electric)

                else:
                    yearly_per_unit = house_table.get(hh_size, house_table[2])
                    ref_area = self._STROMSPIEGEL_REF_AREA_HOUSE.get(hh_size, self._STROMSPIEGEL_REF_AREA_HOUSE[2])

                    area_ratio = area / max(ref_area, 1.0)
                    area_factor = self._bounded_power_scale(
                        area_ratio, self._RESIDENTIAL_AREA_EXPONENT,
                        self._RESIDENTIAL_AREA_FACTOR_MIN, self._RESIDENTIAL_AREA_FACTOR_MAX,
                    )
                    peak_area_factor = self._bounded_power_scale(
                        area_ratio, self._RESIDENTIAL_PEAK_AREA_EXPONENT,
                        self._RESIDENTIAL_PEAK_AREA_FACTOR_MIN, self._RESIDENTIAL_PEAK_AREA_FACTOR_MAX,
                    )

                    yearly_demand_base = yearly_per_unit * area_factor * age_factor_annual
                    peak_factor = self._HOUSEHOLD_PEAK_FACTOR.get(hh_size, 1.0)
                    peak_load = base_peak_kw * peak_factor * peak_area_factor * age_factor_peak
                    # Single dwelling connection peak
                    peak_connection_kva = self._din_pseff_kva(1.0, with_ewh=hot_water_electric)

                # Apply Stromspiegel energy class scaling (A–G)
                label_factor = self._energy_label_factor(is_multi, hh_size, energy_label, hot_water_electric)
                if label_factor != 1.0:
                    yearly_demand_base *= label_factor
                    peak_load *= label_factor

            else:
                # Non-residential row tagged as household method
                specific = self._get_specific_electricity(row_definition, parent) * age_factor_annual
                yearly_demand_base = area * specific
                peak_w_m2 = self._get_peak_load_w_m2(row_definition, parent)
                if peak_w_m2 is not None:
                    peak_load = area * peak_w_m2 / 1_000.0 * age_factor_peak
                else:
                    peak_load = yearly_demand_base / flh

        # ── Area method (non-residential and generic buildings) ───────────────
        else:
            # Prefer research-backed constants (AMEV/Bundesanzeiger) over DB config
            research_specific = self._SPECIFIC_ELECTRICITY_KWH_M2.get(
                self._normalize(row_definition)
            )
            if research_specific is not None:
                specific = research_specific
            else:
                specific = _to_float(row.get("yearly_consumption_per_m2"))
                if specific is None:
                    fallback_yearly = _to_float(row.get("yearly_consumption"))
                    if fallback_yearly is not None:
                        specific = fallback_yearly / self._DEFAULT_AREA_FOR_HOUSEHOLD
                    else:
                        specific = self._get_specific_electricity(row_definition, parent)

            specific *= age_factor_annual
            yearly_demand_base = area * specific

            # Prefer research-backed peak (AMEV) over DB config
            research_peak = self._PEAK_LOAD_W_M2.get(self._normalize(row_definition))
            if research_peak is not None:
                peak_load = area * research_peak / 1_000.0 * age_factor_peak
            else:
                peak_per_m2_config = _to_float(row.get("peak_load_per_m2"))
                if peak_per_m2_config is not None:
                    peak_load = (area * peak_per_m2_config / 1_000.0) * age_factor_peak
                else:
                    peak_w_m2 = self._get_peak_load_w_m2(row_definition, parent)
                    if peak_w_m2 is not None:
                        peak_load = area * peak_w_m2 / 1_000.0 * age_factor_peak
                    else:
                        base_peak_cfg = _to_float(row.get("peak_load"))
                        if base_peak_cfg is not None:
                            peak_load = base_peak_cfg * age_factor_peak
                        else:
                            peak_load = yearly_demand_base / flh

        yearly_demand_total = yearly_demand_base
        specific_demand = yearly_demand_total / area if area > 0 else 0.0

        return {
            "yearly_demand_kwh":           round(yearly_demand_total, 2),
            "yearly_demand_base_kwh":      round(yearly_demand_base, 2),
            "peak_load_kw":                round(peak_load, 2),
            "peak_connection_kva":         round(peak_connection_kva, 2) if peak_connection_kva is not None else None,
            "specific_demand_kwh_m2":      round(specific_demand, 2),
            "f_class":                     row_definition,
            "parent_category":             parent,
            "household_size_used":         household_size_used,
            "estimated_households_used":   round(estimated_households_used, 2) if estimated_households_used is not None else None,
            "energy_label_used":           self._normalize_energy_label(energy_label),
            "hot_water_electric":          hot_water_electric,
            "age_factor_applied":          round(age_factor_annual, 3),
            "age_factor_peak_applied":     round(age_factor_peak, 3),
            "effective_year_used":         effective_year,
            "source":                      "consumer_categories_fclass_model_v3",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience function
# ─────────────────────────────────────────────────────────────────────────────

_ESTIMATOR_INSTANCE: Optional[BuildingEnergyEstimator] = None


def _get_estimator() -> BuildingEnergyEstimator:
    global _ESTIMATOR_INSTANCE
    if _ESTIMATOR_INSTANCE is None:
        _ESTIMATOR_INSTANCE = BuildingEnergyEstimator()
    return _ESTIMATOR_INSTANCE


def estimate_building_energy(
    building_type: str,
    area_m2: float,
    year: Optional[int] = None,
    household_size: Optional[int] = None,
    num_floors: Optional[int] = None,
    renovation_year: Optional[int] = None,
    energy_label: Optional[str] = None,
    hot_water_electric: bool = False,
) -> Dict[str, float]:
    """Convenience wrapper — estimate electricity demand for a single building."""
    return _get_estimator().estimate(
        building_type=building_type,
        area_m2=area_m2,
        year_of_construction=year,
        household_size=household_size,
        num_floors=num_floors,
        renovation_year=renovation_year,
        energy_label=energy_label,
        hot_water_electric=hot_water_electric,
    )
