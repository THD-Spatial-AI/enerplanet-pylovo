import yaml
import os
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from typing import Union

# Type alias for postal codes - supports both numeric (Germany: 12345) 
# and alphanumeric (Netherlands: 1234 AB) formats
PostalCode = Union[str, int]

# Centralized country code mapping for all European countries
COUNTRY_CODE_MAP = {
    # Western Europe
    "germany": "DE",
    "netherlands": "NL",
    "belgium": "BE",
    "luxembourg": "LU",
    "france": "FR",
    "switzerland": "CH",
    "austria": "AT",
    "liechtenstein": "LI",
    "monaco": "MC",
    # Northern Europe
    "denmark": "DK",
    "sweden": "SE",
    "norway": "NO",
    "finland": "FI",
    "iceland": "IS",
    "ireland": "IE",
    "united_kingdom": "GB",
    # Southern Europe
    "italy": "IT",
    "spain": "ES",
    "portugal": "PT",
    "greece": "GR",
    "malta": "MT",
    "cyprus": "CY",
    "andorra": "AD",
    "san_marino": "SM",
    "vatican_city": "VA",
    # Eastern Europe
    "poland": "PL",
    "czech_republic": "CZ",
    "slovakia": "SK",
    "hungary": "HU",
    "romania": "RO",
    "bulgaria": "BG",
    "slovenia": "SI",
    "croatia": "HR",
    "bosnia_and_herzegovina": "BA",
    "serbia": "RS",
    "montenegro": "ME",
    "north_macedonia": "MK",
    "albania": "AL",
    "kosovo": "XK",
    # Baltic States
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    # Other
    "ukraine": "UA",
    "moldova": "MD",
    "belarus": "BY",
}

def get_country_code(country_name: str) -> str:
    """Get ISO country code from country name. Falls back to first 2 chars uppercase."""
    return COUNTRY_CODE_MAP.get(country_name.lower(), country_name[:2].upper())

def load_yaml_config(filepath: str):
    """Loads a YAML configuration file."""
    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filepath)
    
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Config file not found: {abs_path}")
    
    with open(abs_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def get_required_env_var(var_name: str, description: str) -> str:
    """Get required environment variable with clear error message if missing."""
    value = os.getenv(var_name)
    if value is None:
        print("=" * 80)
        print("[ERROR] MISSING DATABASE CONFIGURATION")
        print("=" * 80)
        print(f"Environment variable '{var_name}' is not set.")
        print(f"Description: {description}")
        print()
        print("📋 SETUP REQUIRED:")
        print("1. Create a .env file in the project root directory")
        print("2. Copy one of the examples from config/config_database.yaml")
        print("3. Update the values with your actual database credentials")
        print()
        print("=" * 80)
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value

# =============================================================================
# PROJECT ROOT AND CONFIG LOADING
# =============================================================================
# Load Project Root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load all configurations with correct paths
CONFIG_DATABASE = load_yaml_config("../config/config_database.yaml")
CONFIG_GENERATION = load_yaml_config("../config/config_generation.yaml")
CONFIG_ANALYSIS = load_yaml_config("../config/config_analysis.yaml")
CONFIG_CLASSIFICATION = load_yaml_config("../config/config_classification.yaml")
CONFIG_CLUSTERING = load_yaml_config("../config/config_clustering.yaml")
CONFIG_PLOTTING = load_yaml_config("../config/config_plotting.yaml")

# =============================================================================
# DATABASE CONFIGURATION (from .env file)
# =============================================================================
# Load database connection configuration from .env file
# Keep real environment variables (e.g., docker-compose service env) as source of truth.
# `.env` should only provide defaults when variables are not already set.
load_dotenv(find_dotenv(), override=False)

# Primary database connection (required)
DBNAME = get_required_env_var("DBNAME", "Database name for Pylovo")
DBUSER = get_required_env_var("DBUSER", "Database username")
HOST = get_required_env_var("HOST", "Database host address")
PORT = get_required_env_var("PORT", "Database port number")
PASSWORD = get_required_env_var("PASSWORD", "Database password")
TARGET_SCHEMA = get_required_env_var("TARGET_SCHEMA", "Target schema name")

# INFDB (external database) connection (recommended)
USE_INFDB = CONFIG_DATABASE["USE_INFDB"]
if USE_INFDB:
    INFDB_DBNAME = DBNAME
    INFDB_USER = DBUSER
    INFDB_HOST = HOST
    INFDB_PORT = PORT
    INFDB_PASSWORD = PASSWORD
    INFDB_SOURCE_SCHEMA = os.getenv("INFDB_SOURCE_SCHEMA", "pylovo_input")
else:
    INFDB_DBNAME = None
    INFDB_USER = None
    INFDB_HOST = None
    INFDB_PORT = None
    INFDB_PASSWORD = None
    INFDB_SOURCE_SCHEMA = None

# =============================================================================
# REGIONAL CONFIGURATION (from CONFIG_GENERATION)
# =============================================================================
PLZ = CONFIG_GENERATION.get("PLZ")
AGS = CONFIG_GENERATION.get("AGS")

# Auto-detect regional scale based on which parameter is provided
if PLZ is not None and AGS is not None:
    raise ValueError("Both PLZ and AGS cannot be specified. Please specify either PLZ or AGS.")
elif PLZ is not None:
    REGIONAL_SCALE = "postcode"
    if isinstance(PLZ, list):
        EXECUTION_MODE = "multiple_plz"
    else:
        EXECUTION_MODE = "single_plz"
elif AGS is not None:
    REGIONAL_SCALE = "municipality"
    if isinstance(AGS, list):
        EXECUTION_MODE = "multiple_ags"
    else:
        EXECUTION_MODE = "single_ags"
else:
    raise ValueError("Either PLZ or AGS must be specified in the configuration.")

# =============================================================================
# EXECUTION CONFIGURATION (from CONFIG_GENERATION)
# =============================================================================
ANALYZE_GRIDS = CONFIG_GENERATION["ANALYZE_GRIDS"]
SAVE_GRID_FOLDER = CONFIG_GENERATION["SAVE_GRID_FOLDER"]
LOG_LEVEL = CONFIG_GENERATION["LOG_LEVEL"]
TESTING = CONFIG_GENERATION.get("TESTING", False)

# Parallel execution configuration
N_JOBS_PERCENT = CONFIG_GENERATION.get("N_JOBS_PERCENT", 50)
AVAILABLE_CORES = os.cpu_count() or 1
N_JOBS = max(1, round(AVAILABLE_CORES * N_JOBS_PERCENT / 100))

# Result directory configuration
RESULT_DIR = os.path.join(os.getcwd(), CONFIG_GENERATION.get("RESULT_DIR", "results"))

# Electrical backend configuration
ELECTRICAL_BACKEND = CONFIG_GENERATION.get("ELECTRICAL_BACKEND", "pandapower")

# =============================================================================
# GRID GENERATION CONFIGURATION (from CONFIG_GENERATION)
# =============================================================================
# Version information
VERSION_ID = CONFIG_GENERATION["VERSION_ID"]
VERSION_COMMENT = CONFIG_GENERATION["VERSION_COMMENT"]

# Load calculation parameters
PEAK_LOAD_HOUSEHOLD = CONFIG_GENERATION["PEAK_LOAD_HOUSEHOLD"]
SIM_FACTOR = CONFIG_GENERATION["SIM_FACTOR"]
DEFAULT_POWER_FACTOR = CONFIG_GENERATION["DEFAULT_POWER_FACTOR"]
AUTO_REGISTER_MISSING_F_CLASSES = CONFIG_GENERATION.get("AUTO_REGISTER_MISSING_F_CLASSES", True)
F_CLASS_AUDIT_WARN_THRESHOLD = CONFIG_GENERATION.get("F_CLASS_AUDIT_WARN_THRESHOLD", 0.001)
F_CLASS_AUDIT_FAIL_THRESHOLD = CONFIG_GENERATION.get("F_CLASS_AUDIT_FAIL_THRESHOLD", 0.01)
F_CLASS_AUDIT_TOP_N = CONFIG_GENERATION.get("F_CLASS_AUDIT_TOP_N", 25)

# Consumer categories for load calculation
CONSUMER_CATEGORIES = pd.DataFrame(CONFIG_GENERATION["CONSUMER_CATEGORIES"])
# Patch: replace string placeholder references (e.g. 'PEAK_LOAD_HOUSEHOLD') with actual numeric value
if not CONSUMER_CATEGORIES.empty and "peak_load" in CONSUMER_CATEGORIES.columns:
    def _resolve_peak_load(val):
        if isinstance(val, str) and val.strip() == "PEAK_LOAD_HOUSEHOLD":
            return PEAK_LOAD_HOUSEHOLD
        return val
    CONSUMER_CATEGORIES["peak_load"] = CONSUMER_CATEGORIES["peak_load"].apply(_resolve_peak_load)
    # enforce numeric (None / null stay as NaN for categories using per m2 metrics)
    CONSUMER_CATEGORIES["peak_load"] = pd.to_numeric(CONSUMER_CATEGORIES["peak_load"], errors="coerce")

# Equipment data
EQUIPMENT_DATA = pd.DataFrame(CONFIG_GENERATION["EQUIPMENT_DATA"])

# Normalize cost semantics:
# - cost_eur remains the legacy/effective field consumed by older code paths
# - equipment_only_cost_eur stores bare equipment cost
# - installed_cost_eur stores installed CAPEX when available
if not EQUIPMENT_DATA.empty:
    if "equipment_only_cost_eur" not in EQUIPMENT_DATA.columns:
        EQUIPMENT_DATA["equipment_only_cost_eur"] = EQUIPMENT_DATA.get("cost_eur")
    else:
        EQUIPMENT_DATA["equipment_only_cost_eur"] = EQUIPMENT_DATA["equipment_only_cost_eur"].where(
            EQUIPMENT_DATA["equipment_only_cost_eur"].notna(),
            EQUIPMENT_DATA.get("cost_eur"),
        )
    if "installed_cost_eur" not in EQUIPMENT_DATA.columns:
        EQUIPMENT_DATA["installed_cost_eur"] = None

# Create CABLE_COST_DICT from equipment data for API use
CABLE_COST_DICT = {
    row["name"]: (
        row["installed_cost_eur"]
        if pd.notna(row.get("installed_cost_eur"))
        else (
            row["cost_eur"]
            if pd.notna(row.get("cost_eur"))
            else row["equipment_only_cost_eur"]
        )
    )
    for _, row in EQUIPMENT_DATA[EQUIPMENT_DATA["typ"] == "Cable"].iterrows()
}

# =============================================================================
# VOLTAGE PROPERTIES (from CONFIG_GENERATION)
# =============================================================================
VN = CONFIG_GENERATION["VN"]
V_BAND_LOW = CONFIG_GENERATION["V_BAND_LOW"]
V_BAND_HIGH = CONFIG_GENERATION["V_BAND_HIGH"]

# =============================================================================
# CABLE DIMENSIONING PARAMETERS (from CONFIG_GENERATION)
# =============================================================================
# Calculate maximum cable current from equipment data (largest available cable)
# This ensures the current limit is always based on the actual largest cable in the equipment list
MAX_CABLE_CURRENT_KA = EQUIPMENT_DATA[EQUIPMENT_DATA["typ"] == "Cable"]["max_i_a"].max() / 1000  # Convert A to kA

# Load thresholds for different voltage drop limits
SMALL_LOAD_THRESHOLD_KW = CONFIG_GENERATION["SMALL_LOAD_THRESHOLD_KW"]

# Voltage drop limits for consumer connections (as percentage of nominal voltage per km)
VOLTAGE_DROP_SMALL_LOAD_PERCENT_PER_KM = CONFIG_GENERATION["VOLTAGE_DROP_SMALL_LOAD_PERCENT_PER_KM"]
VOLTAGE_DROP_LARGE_LOAD_PERCENT_PER_KM = CONFIG_GENERATION["VOLTAGE_DROP_LARGE_LOAD_PERCENT_PER_KM"]

# Voltage drop limit for feeder cables (total voltage drop as percentage of nominal voltage)
VOLTAGE_DROP_DISTRIBUTION_PERCENT = CONFIG_GENERATION["VOLTAGE_DROP_DISTRIBUTION_PERCENT"]
TRANSFORMER_LOADING_MARGIN = float(CONFIG_GENERATION.get("TRANSFORMER_LOADING_MARGIN", 1.10))

# Cables available for consumer connections (from feeder to buildings)
CONSUMER_CONNECTION_AVAILABLE_CABLES = CONFIG_GENERATION["CONSUMER_CONNECTION_AVAILABLE_CABLES"]

# =============================================================================
# SETTLEMENT TYPE THRESHOLDS (from CONFIG_GENERATION)
# =============================================================================
RURAL_MAX_HOUSEHOLDS = CONFIG_GENERATION["RURAL_MAX_HOUSEHOLDS"]
URBAN_MIN_HOUSEHOLDS = CONFIG_GENERATION["URBAN_MIN_HOUSEHOLDS"]
RURAL_MIN_BUILDING_DISTANCE = CONFIG_GENERATION["RURAL_MIN_BUILDING_DISTANCE"]
URBAN_MAX_BUILDING_DISTANCE = CONFIG_GENERATION["URBAN_MAX_BUILDING_DISTANCE"]
SETTLEMENT_TYPE_SCORE_DEADBAND = float(CONFIG_GENERATION.get("SETTLEMENT_TYPE_SCORE_DEADBAND", 0.05))

# Transformer mapping: Settlement Type -> Allowed Transformer Capacities (s_max_kva)
TRANSFORMER_MAPPING = CONFIG_GENERATION.get("TRANSFORMER_MAPPING", {
    1: [100, 160, 250],
    2: [160, 250, 400, 630],
    3: [400, 630, 800, 1000, 1250, 1600, 2000, 2500]
})

# =============================================================================
# GRID GENERATION PARAMETERS (from CONFIG_GENERATION)
# =============================================================================
MAX_BROWNFIELD_TRAFO_DISTANCE = CONFIG_GENERATION["MAX_BROWNFIELD_TRAFO_DISTANCE"]
WAYS_BOUNDARY_BUFFER_M = float(CONFIG_GENERATION.get("WAYS_BOUNDARY_BUFFER_M", 50.0))
LARGE_COMPONENT_LOWER_BOUND = CONFIG_GENERATION["LARGE_COMPONENT_LOWER_BOUND"]
LARGE_COMPONENT_DIVIDER = CONFIG_GENERATION["LARGE_COMPONENT_DIVIDER"]
K_MEANS_SEED = CONFIG_GENERATION["K_MEANS_SEED"]
SMALL_COMPONENT_MERGE_ENABLED = CONFIG_GENERATION.get("SMALL_COMPONENT_MERGE_ENABLED", True)
SMALL_COMPONENT_MERGE_MAX_BUILDINGS = int(CONFIG_GENERATION.get("SMALL_COMPONENT_MERGE_MAX_BUILDINGS", 1))
SMALL_COMPONENT_MERGE_MAX_DISTANCE_M = float(CONFIG_GENERATION.get("SMALL_COMPONENT_MERGE_MAX_DISTANCE_M", 120.0))
SMALL_COMPONENT_MERGE_BRIDGE_CLAZZ = int(CONFIG_GENERATION.get("SMALL_COMPONENT_MERGE_BRIDGE_CLAZZ", -99))
KCID_QA_GATES_ENABLED = CONFIG_GENERATION.get("KCID_QA_GATES_ENABLED", True)
KCID_QA_MAX_SINGLETON_RATIO = float(CONFIG_GENERATION.get("KCID_QA_MAX_SINGLETON_RATIO", 0.75))
KCID_QA_MAX_UNASSIGNED_CONSUMERS = int(CONFIG_GENERATION.get("KCID_QA_MAX_UNASSIGNED_CONSUMERS", 0))
KCID_QA_RAISE_ON_FAILURE = CONFIG_GENERATION.get("KCID_QA_RAISE_ON_FAILURE", False)

# =============================================================================
# ANALYSIS CONFIGURATION (from CONFIG_ANALYSIS)
# =============================================================================
MUNICIPAL_REGISTER = CONFIG_ANALYSIS["MUNICIPAL_REGISTER"]
PLOT_COLOR_DICT = CONFIG_ANALYSIS["PLOT_COLOR_DICT"]

# =============================================================================
# CLASSIFICATION CONFIGURATION (from CONFIG_CLASSIFICATION)
# =============================================================================
CLASSIFICATION_VERSION = CONFIG_CLASSIFICATION["CLASSIFICATION_VERSION"]
CLASSIFICATION_VERSION_COMMENT = CONFIG_CLASSIFICATION["CLASSIFICATION_VERSION_COMMENT"]
CLASSIFICATION_REGION = CONFIG_CLASSIFICATION["CLASSIFICATION_REGION"]
NO_OF_CLUSTERS_ALLOWED = CONFIG_CLASSIFICATION["NO_OF_CLUSTERS_ALLOWED"]
N_SAMPLES = CONFIG_CLASSIFICATION["N_SAMPLES"]
REGION_DICT = CONFIG_CLASSIFICATION["REGION_DICT"]
REGIOSTAR7_DICT = CONFIG_CLASSIFICATION["REGIOSTAR7_DICT"]
REGIO7_REGIO5_GEM_DICT = CONFIG_CLASSIFICATION["REGIO7_REGIO5_GEM_DICT"]

# =============================================================================
# CLUSTERING CONFIGURATION (from CONFIG_CLUSTERING)
# =============================================================================
CLUSTERING_PARAMETERS = CONFIG_CLUSTERING["CLUSTERING_PARAMETERS"]
LIST_OF_CLUSTERING_PARAMETERS = CONFIG_CLUSTERING["LIST_OF_CLUSTERING_PARAMETERS"]
N_CLUSTERS_KMEDOID = CONFIG_CLUSTERING["N_CLUSTERS_KMEDOID"]
N_CLUSTERS_KMEANS = CONFIG_CLUSTERING["N_CLUSTERS_KMEANS"]
N_CLUSTERS_GMM = CONFIG_CLUSTERING["N_CLUSTERS_GMM"]

# Clustering thresholds
THRESHOLD_MAX_TRAFO_DIS = CONFIG_CLUSTERING["THRESHOLD_MAX_TRAFO_DIS"]
THRESHOLD_HOUSEHOLDS_PER_BUILDING = CONFIG_CLUSTERING["THRESHOLD_HOUSEHOLDS_PER_BUILDING"]
THRESHOLD_AVG_TRAFO_DIS = CONFIG_CLUSTERING["THRESHOLD_AVG_TRAFO_DIS"]
THRESHOLD_NO_HOUSE_CONNECTIONS = CONFIG_CLUSTERING["THRESHOLD_NO_HOUSE_CONNECTIONS"]
THRESHOLD_VSW_PER_BRANCH = CONFIG_CLUSTERING["THRESHOLD_VSW_PER_BRANCH"]
THRESHOLD_NO_HOUSEHOLDS = CONFIG_CLUSTERING["THRESHOLD_NO_HOUSEHOLDS"]

# =============================================================================
# DATA IMPORT CONFIGURATION (only relevant without InfDB)
# =============================================================================
CSV_FILE_LIST = [
    {"path": os.path.join("raw_data", "postcode.csv"), "table_name": "postcode"},
]

# =============================================================================
# PLOTTING CONFIGURATION (from CONFIG_PLOTTING)
# =============================================================================
# Plotly configuration
ACCESS_TOKEN_PLOTLY = CONFIG_PLOTTING["PLOTLY"]["ACCESS_TOKEN"]

# TUM Color definitions
TUMBlue = CONFIG_PLOTTING["COLORS"]["TUMBlue"]
TUMGreen = CONFIG_PLOTTING["COLORS"]["TUMGreen"]
TUMOrange = CONFIG_PLOTTING["COLORS"]["TUMOrange"]
TUMIvory = CONFIG_PLOTTING["COLORS"]["TUMIvory"]
TUMBlue4 = CONFIG_PLOTTING["COLORS"]["TUMBlue4"]
TUMBlue2 = CONFIG_PLOTTING["COLORS"]["TUMBlue2"]
TUMGray2 = CONFIG_PLOTTING["COLORS"]["TUMGray2"]

# TUM Color palettes
TUMPalette = CONFIG_PLOTTING["PALETTES"]["TUMPalette"]
TUMPalette1 = CONFIG_PLOTTING["PALETTES"]["TUMPalette1"]
TUMPalette2 = CONFIG_PLOTTING["PALETTES"]["TUMPalette2"]
TUMPalette3 = CONFIG_PLOTTING["PALETTES"]["TUMPalette3"]

# Network visualization colors
NODE_COLOR_TRAFO = CONFIG_PLOTTING["NETWORK_COLORS"]["NODE_COLOR_TRAFO"]
NODE_COLOR_CONSUMER = CONFIG_PLOTTING["NETWORK_COLORS"]["NODE_COLOR_CONSUMER"]
NODE_COLOR_CONNECTION_BUS = CONFIG_PLOTTING["NETWORK_COLORS"]["NODE_COLOR_CONNECTION_BUS"]

# Plot style defaults
DEFAULT_FIGURE_SIZE = tuple(CONFIG_PLOTTING["PLOT_DEFAULTS"]["FIGURE_SIZE"])
DEFAULT_DPI = CONFIG_PLOTTING["PLOT_DEFAULTS"]["DPI"]
DEFAULT_FONT_SIZE = CONFIG_PLOTTING["PLOT_DEFAULTS"]["FONT_SIZE"]
DEFAULT_TITLE_FONT_SIZE = CONFIG_PLOTTING["PLOT_DEFAULTS"]["TITLE_FONT_SIZE"]
DEFAULT_GRID_ALPHA = CONFIG_PLOTTING["PLOT_DEFAULTS"]["GRID_ALPHA"]

# Setup seaborn palette
try:
    import seaborn as sns
    sns.set_palette(sns.color_palette(TUMPalette))
except ImportError:
    pass  # seaborn not installed, skip palette setup
