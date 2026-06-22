Energy Technologies
===================

This document describes all energy technologies available in Enerplanet for energy system modeling and simulation.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

Enerplanet uses **Calliope** and **PyPSA** for energy system optimization. Technologies are defined with:

- **Constraints**: Capacity limits, efficiency factors, lifetime
- **Costs**: CAPEX, OPEX, interest rates
- **Technical Parameters**: Technology-specific settings

Technology Categories
^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 20 50
   :header-rows: 1

   * - Category
     - Technologies
   * - **Generation**
     - PV, Wind, Biomass, Geothermal, Hydropower
   * - **Storage**
     - Battery
   * - **Demand**
     - Household, Non-Household consumers

Technology Simulation Architecture
----------------------------------

All technology simulations in Enerplanet follow a unified architecture that integrates with the main platform through the webservice layer.

Overall System Flow
^^^^^^^^^^^^^^^^^^^

.. raw:: html

   <div style="background: #f8f9fa; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #333;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 12px;">⚡ ENERPLANET TECHNOLOGY SIMULATION</div>
   
   <!-- User Input Section -->
   <div style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #1d4ed8; font-size: 13px; margin-bottom: 12px;">USER INPUT (Frontend)</div>
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
   <div style="background: white; border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 90px;">
   <div style="font-size: 11px; font-weight: bold; color: #1d4ed8;">📍 Location</div>
   <div style="font-size: 9px; color: #666;">lat/lon</div>
   </div>
   <div style="background: white; border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 90px;">
   <div style="font-size: 11px; font-weight: bold; color: #1d4ed8;">⚙️ Technology</div>
   <div style="font-size: 9px; color: #666;">Selection</div>
   </div>
   <div style="background: white; border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 90px;">
   <div style="font-size: 11px; font-weight: bold; color: #1d4ed8;">🔧 Parameters</div>
   <div style="font-size: 9px; color: #666;">Config</div>
   </div>
   <div style="background: white; border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 90px;">
   <div style="font-size: 11px; font-weight: bold; color: #1d4ed8;">📅 Date Range</div>
   <div style="font-size: 9px; color: #666;">Selection</div>
   </div>
   <div style="background: white; border: 1px solid #3b82f6; border-radius: 6px; padding: 8px 12px; text-align: center; min-width: 90px;">
   <div style="font-size: 11px; font-weight: bold; color: #1d4ed8;">🗺️ Polygon</div>
   <div style="font-size: 9px; color: #666;">Drawing</div>
   </div>
   </div>
   </div>
   
   <div style="text-align: center; font-size: 16px; color: #333; margin: 8px 0;">▼ Model Configuration</div>
   
   <!-- Backend Section -->
   <div style="background: #d1fae5; border: 2px solid #10b981; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #065f46; font-size: 13px; margin-bottom: 12px;">BACKEND (Go + PostgreSQL)</div>
   <div style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: white; border: 1px solid #10b981; border-radius: 6px; padding: 8px 12px; text-align: center;">Model Handler<br>/api/models</div>
   <span style="color: #10b981;">→</span>
   <div style="background: white; border: 1px solid #10b981; border-radius: 6px; padding: 8px 12px; text-align: center;">Job Queue<br>(Asynq/Redis)</div>
   <span style="color: #10b981;">→</span>
   <div style="background: white; border: 1px solid #10b981; border-radius: 6px; padding: 8px 12px; text-align: center;">Webservice<br>Dispatcher</div>
   <span style="color: #10b981;">→</span>
   <div style="background: white; border: 1px solid #10b981; border-radius: 6px; padding: 8px 12px; text-align: center;">Result Store<br>(PostgreSQL)</div>
   </div>
   </div>
   
   <div style="text-align: center; font-size: 16px; color: #333; margin: 8px 0;">▼ Calculation Request</div>
   
   <!-- Webservice Section -->
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #b45309; font-size: 13px; margin-bottom: 12px;">WEBSERVICE LAYER (Python Flask)</div>
   <div style="text-align: center; font-size: 10px; color: #78350f; margin-bottom: 10px;">Technology Router (main.py)</div>
   <div style="display: flex; justify-content: center; gap: 6px; flex-wrap: wrap; font-size: 9px;">
   <div style="background: #fbbf24; border: 1px solid #f59e0b; border-radius: 4px; padding: 4px 8px;">☀️ PV</div>
   <div style="background: #22d3ee; border: 1px solid #06b6d4; border-radius: 4px; padding: 4px 8px;">💨 Wind</div>
   <div style="background: #4ade80; border: 1px solid #22c55e; border-radius: 4px; padding: 4px 8px;">🌿 Biomass</div>
   <div style="background: #f87171; border: 1px solid #ef4444; border-radius: 4px; padding: 4px 8px;">🌋 Geo</div>
   <div style="background: #60a5fa; border: 1px solid #3b82f6; border-radius: 4px; padding: 4px 8px;">💧 Hydro</div>
   <div style="background: #a78bfa; border: 1px solid #8b5cf6; border-radius: 4px; padding: 4px 8px;">🔋 Battery</div>
   <div style="background: #94a3b8; border: 1px solid #64748b; border-radius: 4px; padding: 4px 8px;">🏠 Demand</div>
   </div>
   </div>
   
   <div style="text-align: center; font-size: 16px; color: #333; margin: 8px 0;">▼</div>
   
   <!-- Simulation Engines Section -->
   <div style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #6d28d9; font-size: 13px; margin-bottom: 12px;">SIMULATION ENGINES</div>
   <div style="display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: white; border: 1px solid #8b5cf6; border-radius: 6px; padding: 8px 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9;">NREL PySAM</div>
   <div style="font-size: 9px; color: #666;">Pvwattsv8</div>
   </div>
   <div style="background: white; border: 1px solid #8b5cf6; border-radius: 6px; padding: 8px 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9;">NREL PySAM</div>
   <div style="font-size: 9px; color: #666;">Windpower</div>
   </div>
   <div style="background: white; border: 1px solid #8b5cf6; border-radius: 6px; padding: 8px 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9;">NREL PySAM</div>
   <div style="font-size: 9px; color: #666;">Biomass</div>
   </div>
   <div style="background: white; border: 1px solid #8b5cf6; border-radius: 6px; padding: 8px 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9;">NREL PySAM</div>
   <div style="font-size: 9px; color: #666;">Geothermal</div>
   </div>
   <div style="background: white; border: 1px solid #8b5cf6; border-radius: 6px; padding: 8px 12px; text-align: center;">
   <div style="font-weight: bold; color: #6d28d9;">PyLovo</div>
   <div style="font-size: 9px; color: #666;">Custom</div>
   </div>
   </div>
   </div>
   
   <div style="text-align: center; font-size: 16px; color: #333; margin: 8px 0;">▼</div>
   
   <!-- Weather Data Section -->
   <div style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0e7490; font-size: 13px; margin-bottom: 12px;">WEATHER DATA</div>
   <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; font-size: 10px;">
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; text-align: center; min-width: 130px;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">MERRA-2</div>
   <div style="font-size: 9px; color: #666;">(NASA NetCDF4)<br>Wind 10m/50m, Temp<br>Pressure, Humidity</div>
   </div>
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; text-align: center; min-width: 130px;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">Open-Meteo</div>
   <div style="font-size: 9px; color: #666;">(API Service)<br>GHI/DNI/DHI, Temp<br>Wind, Precipitation</div>
   </div>
   
   <div style="background: white; border: 1px solid #06b6d4; border-radius: 6px; padding: 10px; text-align: center; min-width: 130px;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">SAM Weather</div>
   <div style="font-size: 9px; color: #666;">(CSV Datasets)<br>Pre-processed<br>Regional TMY data</div>
   </div>
   
   </div>
   </div>
   
   <div style="text-align: center; font-size: 16px; color: #333; margin: 8px 0;">▼ Hourly Generation</div>
   
   <!-- Energy System Optimization Section -->
   <div style="background: #fce7f3; border: 2px solid #ec4899; border-radius: 8px; padding: 15px;">
   <div style="text-align: center; font-weight: bold; color: #be185d; font-size: 13px; margin-bottom: 12px;">ENERGY SYSTEM OPTIMIZATION</div>
   <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 10px;">
   
   <div style="background: white; border: 2px solid #ec4899; border-radius: 6px; padding: 12px; text-align: center; min-width: 180px;">
   <div style="font-weight: bold; color: #be185d; font-size: 12px; margin-bottom: 6px;">CALLIOPE</div>
   <div style="font-size: 9px; color: #666; text-align: left;">
   • Technology constraints<br>
   • Cost optimization<br>
   • Capacity planning<br>
   • Time series dispatch
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #ec4899; border-radius: 6px; padding: 12px; text-align: center; min-width: 180px;">
   <div style="font-weight: bold; color: #be185d; font-size: 12px; margin-bottom: 6px;">PyPSA</div>
   <div style="font-size: 9px; color: #666; text-align: left;">
   • Optimal power flow<br>
   • Network analysis<br>
   • Renewable integration<br>
   • Storage optimization
   </div>
   </div>
   
   </div>
   </div>
   
   </div>


Individual Technology Architectures
-----------------------------------

PV System Architecture
^^^^^^^^^^^^^^^^^^^^^^

Photovoltaic simulation using NREL PySAM Pvwattsv8 module.

.. raw:: html

   <div style="background: #fffbeb; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #fbbf24;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #92400e; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #fbbf24; padding-bottom: 12px;">☀️ PHOTOVOLTAIC SIMULATION</div>
   
   <!-- Input Row -->
   <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 15px;">
   
   <div style="background: white; border: 2px solid #fbbf24; border-radius: 8px; padding: 15px; min-width: 180px; text-align: center;">
   <div style="font-weight: bold; color: #92400e; font-size: 13px; margin-bottom: 8px;">MERRA-2 Data</div>
   <div style="font-size: 11px; color: #666;">
   • GHI, DNI, DHI<br>
   • Temperature<br>
   • Wind Speed
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #fbbf24; border-radius: 8px; padding: 15px; min-width: 180px; text-align: center;">
   <div style="font-weight: bold; color: #92400e; font-size: 13px; margin-bottom: 8px;">User Config</div>
   <div style="font-size: 11px; color: #666;">
   • System kW<br>
   • Azimuth<br>
   • Tilt Angle
   </div>
   </div>
   
   </div>
   
   <div style="text-align: center; color: #92400e; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Location Processing -->
   <div style="background: white; border: 2px solid #fbbf24; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #92400e; font-size: 13px; margin-bottom: 8px;">📍 Location Processing</div>
   <div style="font-size: 11px; color: #555; text-align: center;">
   <code>find_nearest_file(lat, lon, merra_directory)</code><br>
   Haversine distance calculation • Select closest weather dataset
   </div>
   </div>
   
   <div style="text-align: center; color: #92400e; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- PySAM Module -->
   <div style="background: white; border: 2px solid #fbbf24; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #92400e; font-size: 13px; margin-bottom: 10px;">⚡ NREL PySAM Pvwattsv8</div>
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 4px; padding: 8px 12px;">system_capacity: Peak DC (kW)</div>
   <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 4px; padding: 8px 12px;">azimuth: 180° (South)</div>
   <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 4px; padding: 8px 12px;">tilt: 35°</div>
   <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 4px; padding: 8px 12px;">inv_eff: 96%</div>
   <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 4px; padding: 8px 12px;">dc_ac_ratio: 1.1</div>
   </div>
   </div>
   
   <div style="text-align: center; color: #92400e; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Output -->
   <div style="background: #fef3c7; border: 2px solid #fbbf24; border-radius: 8px; padding: 15px; text-align: center;">
   <div style="font-weight: bold; color: #92400e; font-size: 13px; margin-bottom: 8px;">📊 Hourly Output</div>
   <div style="font-size: 11px; color: #555;">
   <code>pv_{lat}_{lon}.csv</code> — 8760 hourly electricity values (kWh)
   </div>
   </div>
   
   </div>


Wind Turbine Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^

Wind power simulation using NREL PySAM Windpower module with power curve interpolation.

.. raw:: html

   <div style="background: #ecfeff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #06b6d4;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #0e7490; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #06b6d4; padding-bottom: 12px;">💨 WIND POWER SIMULATION</div>
   
   <!-- Input Row -->
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 15px;">
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 12px; margin-bottom: 6px;">MERRA-2 Data</div>
   <div style="font-size: 10px; color: #666;">
   • U10M, V10M<br>
   • U50M, V50M<br>
   • Temperature<br>
   • Pressure
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 12px; margin-bottom: 6px;">Turbine CSV DB</div>
   <div style="font-size: 10px; color: #666;">
   • turbine_id<br>
   • power_curve<br>
   • hub_heights<br>
   • rotor_dia
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; min-width: 140px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 12px; margin-bottom: 6px;">User Config</div>
   <div style="font-size: 10px; color: #666;">
   • Turbine ID<br>
   • Hub Height<br>
   • Rotor Diameter
   </div>
   </div>
   
   </div>
   
   <div style="text-align: center; color: #0e7490; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Wind Profile Power Law -->
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0e7490; font-size: 13px; margin-bottom: 8px;">📐 Wind Profile Power Law</div>
   <div style="font-size: 12px; color: #333; text-align: center; font-family: monospace; background: #cffafe; padding: 10px; border-radius: 6px;">
   V<sub>hub</sub> = V<sub>50m</sub> × (H<sub>hub</sub> / 50)<sup>α</sup><br>
   <span style="font-size: 10px; color: #666;">Where α = ln(V₅₀/V₁₀) / ln(50/10) — Wind shear exponent</span>
   </div>
   </div>
   
   <div style="text-align: center; color: #0e7490; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- PySAM Windpower -->
   <div style="background: white; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #0e7490; font-size: 13px; margin-bottom: 10px;">🌀 NREL PySAM Windpower</div>
   
   <!-- Power Curve Visual -->
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 6px; padding: 12px; margin-bottom: 12px;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px; margin-bottom: 8px; text-align: center;">Power Curve Interpolation</div>
   <div style="display: flex; justify-content: space-around; font-size: 10px; color: #555;">
   <span>Cut-in: 3-4 m/s</span>
   <span>Rated: 12-15 m/s</span>
   <span>Cut-out: 25 m/s</span>
   </div>
   </div>
   
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 4px; padding: 6px 10px;">hub_ht: Height (m)</div>
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 4px; padding: 6px 10px;">rotor_diameter (m)</div>
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 4px; padding: 6px 10px;">system_capacity (kW)</div>
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 4px; padding: 6px 10px;">wake_model: 0</div>
   </div>
   </div>
   
   <div style="text-align: center; color: #0e7490; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Output -->
   <div style="background: #cffafe; border: 2px solid #06b6d4; border-radius: 8px; padding: 15px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 13px; margin-bottom: 8px;">📊 Capacity Factor Output</div>
   <div style="font-size: 11px; color: #555;">
   <code>wind_{lat}_{lon}.csv</code><br>
   electricity = capacity_factor × system_capacity
   </div>
   </div>
   
   </div>


Biomass System Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Biomass power plant simulation using NREL PySAM Biomass module.

.. raw:: html

   <div style="background: #f0fdf4; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #22c55e;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #166534; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #22c55e; padding-bottom: 12px;">🌿 BIOMASS POWER SIMULATION</div>
   
   <!-- Input Row -->
   <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 15px;">
   
   <div style="background: white; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; min-width: 160px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 12px; margin-bottom: 6px;">SAM Weather</div>
   <div style="font-size: 10px; color: #666;">
   weather_{lat}_{lon}.csv<br>
   • Temperature<br>
   • Humidity
   </div>
   </div>
   
   <div style="background: white; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; min-width: 200px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 12px; margin-bottom: 6px;">User Configuration</div>
   <div style="font-size: 10px; color: #666; text-align: left;">
   • Feedstock (tonnes/year)<br>
   • HHV (MJ/kg)<br>
   • Boiler efficiency<br>
   • Combustor type<br>
   • Steam grade (psig)<br>
   • Number of boilers<br>
   • Flue gas temp<br>
   • Parasitic load
   </div>
   </div>
   
   </div>
   
   <div style="text-align: center; color: #166534; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- PySAM Biomass -->
   <div style="background: white; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #166534; font-size: 13px; margin-bottom: 10px;">🏭 NREL PySAM Biomass (BiopowerNone)</div>
   
   <!-- Energy Balance Flow -->
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 6px; padding: 12px; margin-bottom: 12px;">
   <div style="font-weight: bold; color: #166534; font-size: 11px; margin-bottom: 8px; text-align: center;">Energy Balance Flow</div>
   <div style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 10px; color: #333;">
   <span style="background: white; padding: 4px 8px; border-radius: 4px;">Feedstock</span>
   <span>→</span>
   <span style="background: white; padding: 4px 8px; border-radius: 4px;">Combustion</span>
   <span>→</span>
   <span style="background: white; padding: 4px 8px; border-radius: 4px;">Steam</span>
   <span>→</span>
   <span style="background: white; padding: 4px 8px; border-radius: 4px;">Turbine</span>
   <span>→</span>
   <span style="background: white; padding: 4px 8px; border-radius: 4px;">Generator</span>
   </div>
   </div>
   
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 6px 10px;">feedstock_total</div>
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 6px 10px;">total_hhv</div>
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 6px 10px;">rated_eff</div>
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 6px 10px;">combustor_type</div>
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 6px 10px;">steam_pressure</div>
   </div>
   </div>
   
   <div style="text-align: center; color: #166534; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Output -->
   <div style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 15px; text-align: center;">
   <div style="font-weight: bold; color: #166534; font-size: 13px; margin-bottom: 8px;">📊 Hourly Output</div>
   <div style="font-size: 11px; color: #555;">
   <code>biomass_{lat}_{lon}.csv</code> — 8760 hourly electricity values (kWh)
   </div>
   </div>
   
   </div>


Geothermal System Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Geothermal power generation using NREL PySAM Geothermal module.

.. raw:: html

   <div style="background: #fef2f2; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #ef4444;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #b91c1c; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #ef4444; padding-bottom: 12px;">🌋 GEOTHERMAL POWER SIMULATION</div>
   
   <!-- Ground Level Indicator -->
   <div style="background: #7c2d12; color: white; text-align: center; padding: 8px; font-size: 12px; font-weight: bold; margin-bottom: 15px; border-radius: 4px;">═══ Ground Level ═══</div>
   
   <!-- User Configuration -->
   <div style="background: white; border: 2px solid #ef4444; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #b91c1c; font-size: 13px; margin-bottom: 10px;">🔧 User Configuration</div>
   <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; font-size: 10px;">
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px 10px;">num_wells</div>
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px 10px;">resource_depth (m)</div>
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px 10px;">well_flow_rate (l/s)</div>
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px 10px;">plant_efficiency (%)</div>
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 6px 10px;">pump_efficiency (%)</div>
   </div>
   </div>
   
   <div style="text-align: center; color: #b91c1c; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- PySAM Geothermal -->
   <div style="background: white; border: 2px solid #ef4444; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
   <div style="text-align: center; font-weight: bold; color: #b91c1c; font-size: 13px; margin-bottom: 12px;">⚡ NREL PySAM Geothermal</div>
   
   <!-- Resource Types -->
   <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;">
   
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 11px;">Shallow</div>
   <div style="font-size: 9px; color: #666;">1-2m depth<br>Horizontal collectors<br>COP: 3-4</div>
   </div>
   
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 11px;">Borehole</div>
   <div style="font-size: 9px; color: #666;">50-200m depth<br>Vertical probes<br>COP: 4-5</div>
   </div>
   
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 6px; padding: 10px; min-width: 120px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 11px;">Deep</div>
   <div style="font-size: 9px; color: #666;">>400m depth<br>District heating<br>Direct use</div>
   </div>
   
   </div>
   
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 6px; padding: 10px; text-align: center; font-size: 10px; color: #555;">
   Temperature gradient: ~3°C per 100m depth | Ground temp (constant): 10-12°C
   </div>
   </div>
   
   <div style="text-align: center; color: #b91c1c; font-size: 20px; margin: 10px 0;">▼</div>
   
   <!-- Output -->
   <div style="background: #fecaca; border: 2px solid #ef4444; border-radius: 8px; padding: 15px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 13px; margin-bottom: 8px;">📊 Hourly Output</div>
   <div style="font-size: 11px; color: #555;">
   <code>geothermal_{lat}_{lon}.csv</code><br>
   Heat/Power output based on resource temperature
   </div>
   </div>
   
   </div>


Data Flow Architecture
----------------------

.. raw:: html

   <div style="background: #faf5ff; padding: 25px; border-radius: 12px; margin: 20px 0; border: 2px solid #a855f7;">
   
   <!-- Title -->
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #a855f7; padding-bottom: 12px;">📊 COMPLETE DATA FLOW ARCHITECTURE</div>
   
   <!-- Top Components Row -->
   <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-bottom: 20px;">
   
   <div style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 12px 20px; text-align: center;">
   <div style="font-weight: bold; color: #1d4ed8; font-size: 12px;">Frontend UI</div>
   <div style="font-size: 10px; color: #666;">React + Vite</div>
   </div>
   
   <div style="background: #d1fae5; border: 2px solid #10b981; border-radius: 8px; padding: 12px 20px; text-align: center;">
   <div style="font-weight: bold; color: #065f46; font-size: 12px;">Backend API</div>
   <div style="font-size: 10px; color: #666;">Go + Chi</div>
   </div>
   
   <div style="background: #fed7aa; border: 2px solid #f97316; border-radius: 8px; padding: 12px 20px; text-align: center;">
   <div style="font-weight: bold; color: #c2410c; font-size: 12px;">PostgreSQL</div>
   <div style="font-size: 10px; color: #666;">Database</div>
   </div>
   
   </div>
   
   <!-- Flow Steps -->
   <div style="display: flex; flex-direction: column; gap: 10px;">
   
   <!-- Step 1-2: Create & Store -->
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; align-items: center;">
   <div style="background: #ede9fe; border: 1px solid #a855f7; border-radius: 6px; padding: 8px 12px; font-size: 10px;">
   <strong>1.</strong> POST /api/models → Create Model
   </div>
   <span style="color: #7c3aed;">→</span>
   <div style="background: #ede9fe; border: 1px solid #a855f7; border-radius: 6px; padding: 8px 12px; font-size: 10px;">
   <strong>2.</strong> Store in PostgreSQL
   </div>
   </div>
   
   <!-- Step 3: Start Calculation -->
   <div style="display: flex; justify-content: center;">
   <div style="background: #ede9fe; border: 1px solid #a855f7; border-radius: 6px; padding: 8px 12px; font-size: 10px;">
   <strong>3.</strong> POST /calculation/start/{id} → Start Calculation
   </div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 4: Queue -->
   <div style="background: #fecaca; border: 2px solid #ef4444; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #b91c1c; font-size: 11px;">4. Queue Job (Asynq)</div>
   <div style="font-size: 10px; color: #666;">Redis Task Queue</div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 5: Webservice -->
   <div style="background: white; border: 2px solid #a855f7; border-radius: 8px; padding: 15px;">
   <div style="text-align: center; font-weight: bold; color: #7c3aed; font-size: 12px; margin-bottom: 10px;">5. Webservice (Python Flask)</div>
   <div style="font-size: 10px; color: #666; text-align: center; margin-bottom: 10px;">POST /simulation/start</div>
   <div style="display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; font-size: 9px;">
   <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 4px; padding: 4px 8px;">☀️ PvSystemModel</div>
   <div style="background: #cffafe; border: 1px solid #06b6d4; border-radius: 4px; padding: 4px 8px;">💨 WindPowerGen</div>
   <div style="background: #dcfce7; border: 1px solid #22c55e; border-radius: 4px; padding: 4px 8px;">🌿 BiomassModel</div>
   <div style="background: #fecaca; border: 1px solid #ef4444; border-radius: 4px; padding: 4px 8px;">🌋 GeothermalModel</div>
   </div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 6: Weather -->
   <div style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #0e7490; font-size: 11px;">6. Weather Data Processing</div>
   <div style="font-size: 10px; color: #666;">MERRA-2 / Open-Meteo → Find grid point → Extract hourly</div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 7: PySAM -->
   <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #b45309; font-size: 11px;">7. NREL PySAM Simulation</div>
   <div style="font-size: 10px; color: #666;">model.execute() → 8760 hourly values</div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 8: Optimization -->
   <div style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 12px; text-align: center;">
   <div style="font-weight: bold; color: #1d4ed8; font-size: 11px;">8. Calliope / PyPSA</div>
   <div style="font-size: 10px; color: #666;">Build energy model → Run optimization → Calculate costs</div>
   </div>
   
   <div style="text-align: center; color: #7c3aed; font-size: 16px;">▼</div>
   
   <!-- Step 9-12: Results -->
   <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
   <div style="background: #d1fae5; border: 2px solid #10b981; border-radius: 8px; padding: 10px; text-align: center; font-size: 10px;">
   <strong>9.</strong> Store Results<br>in PostgreSQL
   </div>
   <div style="background: #ede9fe; border: 2px solid #a855f7; border-radius: 8px; padding: 10px; text-align: center; font-size: 10px;">
   <strong>10.</strong> Poll Status<br>GET /api/models/{id}
   </div>
   <div style="background: #ede9fe; border: 2px solid #a855f7; border-radius: 8px; padding: 10px; text-align: center; font-size: 10px;">
   <strong>11-12.</strong> Get Results<br>status: completed
   </div>
   </div>
   
   </div>
   
   </div>


Generation Technologies
-----------------------

Photovoltaic (PV) Supply
^^^^^^^^^^^^^^^^^^^^^^^^

Solar photovoltaic energy generation system.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>pv_supply</code></span>
   <span style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> ☀️</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 20 25 10 10 35
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``system_capacity``
     - PV Panel Peak Capacity
     - 6
     - kW
     - Peak DC capacity of PV array
   * - ``azimuth``
     - PV Panel Orientation
     - 180
     - deg
     - Panel azimuth (180° = South)
   * - ``tilt``
     - PV Panel Tilt
     - 35
     - deg
     - Panel tilt angle from horizontal
   * - ``inv_eff``
     - Inverter Efficiency
     - 0.96
     - %
     - DC to AC conversion efficiency
   * - ``losses``
     - PV System Loss
     - 0.001
     - %
     - Cable, soiling, mismatch losses
   * - ``dc_ac_ratio``
     - DC/AC Ratio
     - 1.1
     - ratio
     - Oversizing of DC array vs inverter

**Capacity Constraints:**

.. list-table::
   :widths: 30 15 15
   :header-rows: 1

   * - Parameter
     - Default
     - Unit
   * - ``cont_energy_cap_max``
     - 1,200
     - kW
   * - ``cont_energy_cap_min``
     - 0
     - kW
   * - ``cont_energy_eff``
     - 0.9
     - %
   * - ``cont_lifetime``
     - 25
     - years

**Cost Parameters:**

.. list-table::
   :widths: 30 15 15
   :header-rows: 1

   * - Parameter
     - Default
     - Unit
   * - ``cost_energy_cap``
     - 1,050
     - EUR/kW
   * - ``cost_om_annual``
     - 10.5
     - EUR/kW
   * - ``cost_interest_rate``
     - 0.02
     - %


Wind Turbine Supply
^^^^^^^^^^^^^^^^^^^

Onshore wind turbine energy generation using NREL PySAM Windpower module.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>wind_onshore</code></span>
   <span style="background: #ecfeff; border: 2px solid #06b6d4; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> 💨</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 20 25 10 10 35
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``hub_height``
     - Hub Height
     - 100
     - m
     - Height of turbine hub above ground
   * - ``rotor_diameter``
     - Rotor Diameter
     - 80
     - m
     - Diameter of rotor blades

.. note::

   Wind turbine power curves are loaded from CSV database containing:
   
   - ``turbine_id``: Unique turbine identifier
   - ``nominal_power``: Rated power output (kW)
   - ``wind_speeds``: Wind speed values for power curve (m/s)
   - ``power_output``: Power output at each wind speed (kW)
   - ``hub_height``: Available hub heights (m)


Battery Storage
^^^^^^^^^^^^^^^

Battery energy storage system.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>battery_storage</code></span>
   <span style="background: #ede9fe; border: 2px solid #8b5cf6; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> 🔋</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 20 25 10 10 35
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``storage_capacity``
     - Storage Capacity
     - 10
     - kWh
     - Total energy storage capacity
   * - ``charge_rate``
     - Charge Rate
     - 0.5
     - C
     - Maximum charge rate (C-rate)
   * - ``discharge_rate``
     - Discharge Rate
     - 0.5
     - C
     - Maximum discharge rate
   * - ``round_trip_eff``
     - Round-trip Efficiency
     - 0.9
     - %
     - Charge-discharge efficiency
   * - ``depth_of_discharge``
     - Depth of Discharge
     - 0.8
     - %
     - Maximum DOD allowed
   * - ``cycle_life``
     - Cycle Life
     - 6000
     - cycles
     - Expected cycle lifetime


Biomass Supply
^^^^^^^^^^^^^^

Biomass-based power and heat generation using NREL PySAM BiopowerNone module.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>biomass_supply</code></span>
   <span style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> 🌿</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 22 25 12 10 31
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``feedstock_total``
     - Annual Feedstock
     - 10000
     - tonnes
     - Annual biomass feedstock input
   * - ``total_hhv``
     - Higher Heating Value
     - 18.5
     - MJ/kg
     - Energy content of fuel
   * - ``boiler_efficiency``
     - Boiler Efficiency
     - 0.85
     - ratio
     - Thermal conversion efficiency
   * - ``combustor_type``
     - Combustor Type
     - 0
     - -
     - 0=stoker, 1=fluidized bed
   * - ``steam_grade_psig``
     - Steam Pressure
     - 600
     - psig
     - Boiler steam pressure grade
   * - ``boiler_numbers``
     - Number of Boilers
     - 1
     - -
     - Number of boiler units
   * - ``flue_gas_temperature``
     - Flue Gas Temp
     - 350
     - °F
     - Exhaust gas temperature
   * - ``parasitic_load``
     - Parasitic Load
     - 0.05
     - ratio
     - Internal power consumption


Geothermal Supply
^^^^^^^^^^^^^^^^^

Geothermal power generation using NREL PySAM GeothermalPowerSingleOwner module.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>geothermal_supply</code></span>
   <span style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> 🌋</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 22 25 10 10 33
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``num_wells``
     - Number of Wells
     - 1
     - -
     - Number of production wells
   * - ``resource_depth``
     - Resource Depth
     - 150
     - m
     - Depth of geothermal resource
   * - ``well_flow_rate``
     - Well Flow Rate
     - 10
     - l/s
     - Geothermal fluid flow rate
   * - ``plant_efficiency_input``
     - Plant Efficiency
     - 0.15
     - ratio
     - Overall plant conversion efficiency
   * - ``pump_efficiency``
     - Pump Efficiency
     - 0.75
     - ratio
     - Circulation pump efficiency


Hydropower Supply
^^^^^^^^^^^^^^^^^

Run-of-river and small hydropower.

.. raw:: html

   <div style="display: inline-flex; align-items: center; gap: 15px; margin-bottom: 15px;">
   <span style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Key:</strong> <code>water_supply</code></span>
   <span style="background: #dbeafe; border: 2px solid #3b82f6; border-radius: 8px; padding: 8px 12px; font-size: 12px;"><strong>Icon:</strong> 💧</span>
   </div>

**Technical Parameters:**

.. list-table::
   :widths: 20 25 10 10 35
   :header-rows: 1

   * - Parameter
     - Alias
     - Default
     - Unit
     - Description
   * - ``capacity``
     - Installed Capacity
     - 500
     - kW
     - Rated power output
   * - ``head``
     - Head Height
     - 20
     - m
     - Vertical drop height
   * - ``flow_rate``
     - Design Flow Rate
     - 5
     - m³/s
     - Design water flow rate
   * - ``turbine_efficiency``
     - Turbine Efficiency
     - 0.88
     - %
     - Hydraulic-to-mechanical efficiency

**Power Calculation:**

::

    P = η × ρ × g × Q × H

    Where:
      P = Power output (W)
      η = Overall efficiency (0.85-0.93)
      ρ = Water density (1000 kg/m³)
      g = Gravity (9.81 m/s²)
      Q = Flow rate (m³/s)
      H = Head height (m)


Calliope Integration
--------------------

Technology constraints are mapped to Calliope model structure:

.. code-block:: yaml

    techs:
      pv_supply:
        essentials:
          name: 'Photovoltaic'
          color: '#FFD700'
          parent: supply
          carrier: electricity
        constraints:
          resource: file=pv_resource.csv
          energy_cap_max: 1200
          energy_eff: 0.9
          lifetime: 25
        costs:
          monetary:
            energy_cap: 1050
            om_annual: 10.5
            interest_rate: 0.02

Weather Data Requirements
-------------------------

Each technology requires specific weather variables from MERRA-2 or SAM weather files:

.. list-table::
   :widths: 20 40
   :header-rows: 1

   * - Technology
     - Weather Variables
   * - PV
     - GHI (SWGDN), Temperature (T2M), Wind Speed 2m (U2M, V2M)
   * - Wind
     - Wind Speed 10m (U10M, V10M), Wind Speed 50m (U50M, V50M), Temperature (T2M), Pressure (PS)
   * - Biomass
     - SAM weather file (temperature, humidity)
   * - Geothermal
     - SAM weather file (temperature conditions)
