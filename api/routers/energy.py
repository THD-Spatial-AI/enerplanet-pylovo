"""Energy estimation endpoints."""
import logging

from fastapi import APIRouter, HTTPException

from models import EstimateEnergyRequest, EstimateEnergyBatchRequest
from src.ai_estimation import estimate_building_energy

logger = logging.getLogger(__name__)

router = APIRouter(tags=["energy"])


@router.post("/estimate-energy")
async def estimate_energy(payload: EstimateEnergyRequest):
    """
    Estimate energy demand for a building using AI/statistical models.
    Based on Fraunhofer ISI and TABULA research data.
    """
    try:
        result = estimate_building_energy(
            payload.building_type,
            payload.area_m2,
            payload.year_of_construction,
            payload.household_size,
            payload.num_floors,
            energy_label=payload.energy_label,
            hot_water_electric=payload.hot_water_electric,
        )
        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        logger.warning("Invalid input for energy estimation: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Energy estimation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/estimate-energy-batch")
async def estimate_energy_batch(payload: EstimateEnergyBatchRequest):
    """
    Batch estimate energy demand for multiple buildings.
    """
    results = []
    errors = []
    for i, b in enumerate(payload.buildings):
        try:
            res = estimate_building_energy(
                b.building_type,
                b.area_m2,
                b.year_of_construction,
                b.household_size,
                b.num_floors,
                energy_label=b.energy_label,
                hot_water_electric=b.hot_water_electric,
            )
            results.append(res)
        except Exception as e:
            logger.error("Batch estimation failed for building %d (type=%s, area=%s): %s",
                         i, b.building_type, b.area_m2, e)
            errors.append({"index": i, "error": str(e)})
            results.append({
                "yearly_demand_kwh": 0,
                "peak_load_kw": 0,
                "specific_demand_kwh_m2": 0,
                "confidence": 0,
                "source": "error"
            })

    return {
        "status": "partial_success" if errors else "success",
        "data": results,
        **({"errors": errors} if errors else {}),
    }
