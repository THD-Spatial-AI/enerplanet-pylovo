from typing import Dict, Any, Optional
import math

def calculate_hosting_capacity(
    transformer_capacity_kva: float,
    current_peak_load_kw: float,
    charger_power_kw: float = 11.0,
    simultaneity_factor: float = 0.8,
    power_factor_grid: float = 0.95,
    power_factor_ev: float = 0.99,
    # Additional parameters for enhanced analysis per paper methodology
    nominal_voltage_v: float = 400.0,  # LV nominal voltage (V)
    voltage_limit_pu: float = 0.90,    # Min voltage limit (p.u.) per EN 50160
    cable_impedance_ohm_per_km: float = 0.32,  # Typical NAYY 4x150 R (Ω/km)
    cable_length_km: float = 0.0,      # Distance from transformer (km)
    cable_max_current_a: float = 0.0   # Cable thermal limit (A), 0 = not considered
) -> Dict[str, Any]:
    """
    Calculate EV hosting capacity for a building or transformer area using the deterministic method.

    Based on: "Methods and Tools for PV and EV Hosting Capacity Determination in
    Low Voltage Distribution Networks—A Review" (Umoh et al., Energies 2023, 16, 3609)

    The paper identifies three main performance indices for EV HC (Section 4):
    1. Transformer thermal loading
    2. Voltage magnitude (undervoltage for EV charging)
    3. Cable/line thermal limits

    This implementation uses the deterministic method (Section 3.1) which:
    - Uses fixed input values for worst-case analysis
    - Evaluates multiple constraints
    - Returns the most limiting factor

    Args:
        transformer_capacity_kva: Rated capacity of the local transformer (kVA)
        current_peak_load_kw: Existing peak load of the building/area (kW)
        charger_power_kw: Rated power of the EV charger (default 11.0 kW for Level 2)
        simultaneity_factor: Coincidence factor for EV charging (0.1 - 1.0)
                            Per paper ref [143]: 46-85% of customers charging simultaneously
        power_factor_grid: Power factor for existing grid load (default 0.95)
        power_factor_ev: Power factor for EV chargers (default 0.99, near unity)
        nominal_voltage_v: Nominal LV voltage (default 400V for 3-phase)
        voltage_limit_pu: Minimum voltage limit in p.u. (default 0.90 per EN 50160)
        cable_impedance_ohm_per_km: Cable resistance (Ω/km), default for NAYY 4x150
        cable_length_km: Distance from transformer to load point (km)
        cable_max_current_a: Maximum cable current capacity (A), 0 = not considered

    Returns:
        Dict containing:
            max_chargers: Maximum number of EV chargers that can be hosted
            remaining_capacity_kva: Remaining transformer capacity
            limiting_factor: The constraint that limits HC (Transformer/Voltage/Cable)
            status: "safe" | "warning" | "critical"
            details: Detailed breakdown of each constraint
    """

    # =========================================================================
    # CONSTRAINT 1: TRANSFORMER THERMAL LIMIT (Primary constraint per paper)
    # Section 4, page 13: "thermal limits and transformer overload due to increased demand"
    # =========================================================================

    # Convert current peak load to apparent power: S = P / PF
    current_load_kva = current_peak_load_kw / power_factor_grid

    # Calculate remaining transformer capacity
    remaining_capacity_kva = transformer_capacity_kva - current_load_kva

    # Apparent power per charger: S_charger = P_charger / PF_ev
    charger_kva = charger_power_kw / power_factor_ev

    # Effective load per charger with simultaneity factor
    # Per paper Section 4: simultaneity factor accounts for not all EVs charging at once
    effective_charger_load_kva = charger_kva * simultaneity_factor

    # Max chargers from transformer constraint
    if remaining_capacity_kva <= 0:
        max_chargers_transformer = 0
    else:
        max_chargers_transformer = int(remaining_capacity_kva / effective_charger_load_kva)

    # =========================================================================
    # CONSTRAINT 2: VOLTAGE DROP LIMIT (Per paper Section 4)
    # "voltage magnitude" is a key performance index for EV HC
    # For EV charging, undervoltage is the concern (unlike PV which causes overvoltage)
    # =========================================================================

    max_chargers_voltage = float('inf')  # Default: no voltage constraint
    voltage_drop_percent = 0.0

    if cable_length_km > 0 and cable_impedance_ohm_per_km > 0:
        # Simplified voltage drop calculation for LV networks
        # ΔV ≈ (P × R) / V for predominantly resistive LV cables
        # Maximum allowable voltage drop: (1 - voltage_limit_pu) × 100%
        max_voltage_drop_v = nominal_voltage_v * (1 - voltage_limit_pu)

        # Cable resistance
        cable_resistance = cable_impedance_ohm_per_km * cable_length_km

        # Current voltage drop from existing load
        existing_current_a = (current_peak_load_kw * 1000) / (nominal_voltage_v * math.sqrt(3))
        existing_voltage_drop_v = existing_current_a * cable_resistance * math.sqrt(3)

        # Remaining voltage headroom
        remaining_voltage_headroom_v = max_voltage_drop_v - existing_voltage_drop_v

        if remaining_voltage_headroom_v > 0:
            # Current per charger (3-phase)
            charger_current_a = (charger_power_kw * 1000) / (nominal_voltage_v * math.sqrt(3) * power_factor_ev)

            # Voltage drop per charger
            voltage_drop_per_charger_v = charger_current_a * cable_resistance * math.sqrt(3) * simultaneity_factor

            if voltage_drop_per_charger_v > 0:
                max_chargers_voltage = int(remaining_voltage_headroom_v / voltage_drop_per_charger_v)

            # Calculate total voltage drop percentage for reporting
            voltage_drop_percent = (existing_voltage_drop_v / nominal_voltage_v) * 100
        else:
            max_chargers_voltage = 0
            voltage_drop_percent = (existing_voltage_drop_v / nominal_voltage_v) * 100

    # =========================================================================
    # CONSTRAINT 3: CABLE THERMAL LIMIT (Per paper Section 4)
    # "line loading" is a key performance index
    # =========================================================================

    max_chargers_cable = float('inf')  # Default: no cable constraint
    cable_loading_percent = 0.0

    if cable_max_current_a > 0:
        # Current from existing load
        existing_current_a = (current_peak_load_kw * 1000) / (nominal_voltage_v * math.sqrt(3))

        # Remaining cable capacity
        remaining_cable_capacity_a = cable_max_current_a - existing_current_a

        if remaining_cable_capacity_a > 0:
            # Current per charger
            charger_current_a = (charger_power_kw * 1000) / (nominal_voltage_v * math.sqrt(3) * power_factor_ev)
            effective_charger_current_a = charger_current_a * simultaneity_factor

            if effective_charger_current_a > 0:
                max_chargers_cable = int(remaining_cable_capacity_a / effective_charger_current_a)

            cable_loading_percent = (existing_current_a / cable_max_current_a) * 100
        else:
            max_chargers_cable = 0
            cable_loading_percent = 100.0

    # =========================================================================
    # DETERMINE LIMITING FACTOR (Per paper: HC is limited by first constraint violated)
    # =========================================================================

    constraints = {
        "Transformer Capacity": max_chargers_transformer,
        "Voltage Drop": max_chargers_voltage if max_chargers_voltage != float('inf') else None,
        "Cable Thermal": max_chargers_cable if max_chargers_cable != float('inf') else None
    }

    # Filter out None values and find minimum
    active_constraints = {k: v for k, v in constraints.items() if v is not None}

    if not active_constraints:
        max_chargers = 0
        limiting_factor = "No Valid Constraints"
    else:
        limiting_factor = min(active_constraints, key=active_constraints.get)
        max_chargers = active_constraints[limiting_factor]

    # =========================================================================
    # DETERMINE STATUS
    # Per paper Section 4, ref [143]: 6-11 chargers is typical for 13-house network
    # Using utilization-based thresholds
    # =========================================================================

    # Calculate transformer utilization after adding chargers
    if max_chargers > 0 and transformer_capacity_kva > 0:
        total_load_with_ev = current_load_kva + (max_chargers * effective_charger_load_kva)
        utilization_at_max = (total_load_with_ev / transformer_capacity_kva) * 100
    else:
        utilization_at_max = (current_load_kva / transformer_capacity_kva) * 100 if transformer_capacity_kva > 0 else 100

    # Status based on both count and utilization
    if max_chargers == 0:
        status = "critical"
    elif max_chargers <= 2 or utilization_at_max >= 95:
        status = "warning"
    else:
        status = "safe"

    # =========================================================================
    # BUILD RESPONSE
    # =========================================================================

    return {
        "max_chargers": max_chargers,
        "remaining_capacity_kva": round(max(0, remaining_capacity_kva), 2),
        "limiting_factor": limiting_factor,
        "status": status,
        "charger_power_kw": charger_power_kw,
        "simultaneity_factor": simultaneity_factor,
        "details": {
            # Transformer constraint details
            "transformer_capacity_kva": transformer_capacity_kva,
            "current_load_kva": round(current_load_kva, 2),
            "effective_load_per_charger_kva": round(effective_charger_load_kva, 2),
            "max_chargers_transformer": max_chargers_transformer,
            "transformer_utilization_percent": round((current_load_kva / transformer_capacity_kva) * 100, 1) if transformer_capacity_kva > 0 else 0,

            # Voltage constraint details (if applicable)
            "voltage_drop_percent": round(voltage_drop_percent, 2),
            "max_chargers_voltage": max_chargers_voltage if max_chargers_voltage != float('inf') else None,

            # Cable constraint details (if applicable)
            "cable_loading_percent": round(cable_loading_percent, 1),
            "max_chargers_cable": max_chargers_cable if max_chargers_cable != float('inf') else None,

            # Utilization projection
            "projected_utilization_percent": round(utilization_at_max, 1)
        }
    }
