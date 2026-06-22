"""Pipeline management endpoints."""
import subprocess
import threading
import traceback
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.config_loader import VERSION_ID, get_country_code
from src.database.database_client import DatabaseClient

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Pipeline job storage
pipeline_jobs = {}
MAX_LOGS = 500  # Maximum log lines to keep per job


class PipelineRunRequest(BaseModel):
    country: str
    state: str
    step: str  # 'datapipeline', 'constructor', 'grid', 'all'
    workers: Optional[int] = 10
    no_cache: Optional[bool] = True


class PipelineJob:
    def __init__(self, job_id: str, country: str, state: str, step: str):
        self.job_id = job_id
        self.country = country
        self.state = state
        self.step = step
        self.status = 'pending'
        self.progress = 0
        self.logs = deque(maxlen=MAX_LOGS)
        self.started_at = datetime.now().isoformat()
        self.completed_at = None
        self.error = None
        self.process = None


def run_pipeline_step(job: PipelineJob, command: list, step_name: str):
    """Run a single pipeline step and update job status."""
    try:
        job.logs.append(f"[{step_name}] Starting: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent)  # pylovo root
        )
        job.process = process
        
        for line in process.stdout:
            line = line.strip()
            if line:
                job.logs.append(f"[{step_name}] {line}")
                # Parse progress from log output
                if '% processed' in line.lower() or '% finished' in line.lower():
                    try:
                        pct = int(line.split('%')[0].split()[-1])
                        job.progress = min(pct, 100)
                    except:
                        pass
        
        process.wait()
        
        if process.returncode != 0:
            raise Exception(f"{step_name} failed with exit code {process.returncode}")
        
        job.logs.append(f"[{step_name}] Completed successfully")
        return True
        
    except Exception as e:
        job.logs.append(f"[{step_name}] ERROR: {str(e)}")
        raise


def run_pipeline_async(job: PipelineJob, workers: int, no_cache: bool):
    """Run the pipeline asynchronously."""
    try:
        job.status = 'running'
        steps_to_run = []
        
        if job.step == 'datapipeline' or job.step == 'all':
            cmd = ['python', '-m', 'datapipeline.main', '--country', job.country, '--state', job.state]
            if no_cache:
                cmd.append('--no-cache')
            steps_to_run.append(('datapipeline', cmd))
        
        if job.step == 'constructor' or job.step == 'all':
            cmd = ['python', 'runme/main_constructor.py', '--datapipeline', '--country', job.country, '--state', job.state]
            steps_to_run.append(('constructor', cmd))
        
        if job.step == 'grid' or job.step == 'all':
            cmd = ['python', 'runme/create/generate_grid.py', job.country, job.state, '--worker', str(workers)]
            steps_to_run.append(('grid', cmd))
        
        total_steps = len(steps_to_run)
        for i, (step_name, cmd) in enumerate(steps_to_run):
            job.progress = int((i / total_steps) * 100)
            run_pipeline_step(job, cmd, step_name)
        
        job.status = 'completed'
        job.progress = 100
        job.completed_at = datetime.now().isoformat()
        job.logs.append("Pipeline completed successfully!")
        
    except Exception as e:
        job.status = 'failed'
        job.error = str(e)
        job.completed_at = datetime.now().isoformat()
        job.logs.append(f"Pipeline failed: {str(e)}")
        traceback.print_exc()


@router.post("/run")
def run_pipeline(request: PipelineRunRequest):
    """Start a pipeline job."""
    try:
        # Validate step
        valid_steps = ['datapipeline', 'constructor', 'grid', 'all']
        if request.step not in valid_steps:
            raise HTTPException(status_code=400, detail=f"Invalid step. Must be one of: {valid_steps}")
        
        # Create job
        job_id = str(uuid.uuid4())
        job = PipelineJob(job_id, request.country, request.state, request.step)
        pipeline_jobs[job_id] = job
        
        # Start pipeline in background thread
        thread = threading.Thread(
            target=run_pipeline_async,
            args=(job, request.workers or 10, request.no_cache or True)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": f"Pipeline '{request.step}' started for {request.country}/{request.state}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
def get_pipeline_status(job_id: str):
    """Get the status of a pipeline job."""
    job = pipeline_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "step": job.step,
        "progress": job.progress,
        "logs": list(job.logs)[-100:],  # Return last 100 logs
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error
    }


@router.get("/regions")
def get_pipeline_regions():
    """Get available regions for the pipeline - All European countries."""
    return {
        "countries": [
            {
                "code": "austria",
                "name": "Austria",
                "states": [
                    {"code": "burgenland", "name": "Burgenland"},
                    {"code": "carinthia", "name": "Carinthia (Kärnten)"},
                    {"code": "lower-austria", "name": "Lower Austria (Niederösterreich)"},
                    {"code": "upper-austria", "name": "Upper Austria (Oberösterreich)"},
                    {"code": "salzburg", "name": "Salzburg"},
                    {"code": "styria", "name": "Styria (Steiermark)"},
                    {"code": "tyrol", "name": "Tyrol (Tirol)"},
                    {"code": "vorarlberg", "name": "Vorarlberg"},
                    {"code": "vienna", "name": "Vienna (Wien)"},
                ]
            },
            {
                "code": "belgium",
                "name": "Belgium",
                "states": [
                    {"code": "antwerp", "name": "Antwerp"},
                    {"code": "brussels", "name": "Brussels"},
                    {"code": "east-flanders", "name": "East Flanders"},
                    {"code": "flemish-brabant", "name": "Flemish Brabant"},
                    {"code": "hainaut", "name": "Hainaut"},
                    {"code": "liege", "name": "Liège"},
                    {"code": "limburg", "name": "Limburg"},
                    {"code": "luxembourg", "name": "Luxembourg"},
                    {"code": "namur", "name": "Namur"},
                    {"code": "walloon-brabant", "name": "Walloon Brabant"},
                    {"code": "west-flanders", "name": "West Flanders"},
                ]
            },
            {
                "code": "czech-republic",
                "name": "Czech Republic",
                "states": [
                    {"code": "prague", "name": "Prague"},
                    {"code": "central-bohemia", "name": "Central Bohemian"},
                    {"code": "south-bohemia", "name": "South Bohemian"},
                    {"code": "plzen", "name": "Plzeň"},
                    {"code": "karlovy-vary", "name": "Karlovy Vary"},
                    {"code": "usti-nad-labem", "name": "Ústí nad Labem"},
                    {"code": "liberec", "name": "Liberec"},
                    {"code": "hradec-kralove", "name": "Hradec Králové"},
                    {"code": "pardubice", "name": "Pardubice"},
                    {"code": "olomouc", "name": "Olomouc"},
                    {"code": "moravian-silesian", "name": "Moravian-Silesian"},
                    {"code": "south-moravian", "name": "South Moravian"},
                    {"code": "zlin", "name": "Zlín"},
                    {"code": "vysocina", "name": "Vysočina"},
                ]
            },
            {
                "code": "denmark",
                "name": "Denmark",
                "states": [
                    {"code": "capital", "name": "Capital Region"},
                    {"code": "central-jutland", "name": "Central Denmark"},
                    {"code": "north-jutland", "name": "North Denmark"},
                    {"code": "zealand", "name": "Region Zealand"},
                    {"code": "southern-denmark", "name": "Southern Denmark"},
                ]
            },
            {
                "code": "finland",
                "name": "Finland",
                "states": [
                    {"code": "uusimaa", "name": "Uusimaa"},
                    {"code": "southwest-finland", "name": "Southwest Finland"},
                    {"code": "pirkanmaa", "name": "Pirkanmaa"},
                    {"code": "central-finland", "name": "Central Finland"},
                    {"code": "north-ostrobothnia", "name": "North Ostrobothnia"},
                    {"code": "lapland", "name": "Lapland"},
                ]
            },
            {
                "code": "france",
                "name": "France",
                "states": [
                    {"code": "auvergne-rhone-alpes", "name": "Auvergne-Rhône-Alpes"},
                    {"code": "bourgogne-franche-comte", "name": "Bourgogne-Franche-Comté"},
                    {"code": "brittany", "name": "Brittany"},
                    {"code": "centre-val-de-loire", "name": "Centre-Val de Loire"},
                    {"code": "grand-est", "name": "Grand Est"},
                    {"code": "hauts-de-france", "name": "Hauts-de-France"},
                    {"code": "ile-de-france", "name": "Île-de-France"},
                    {"code": "normandy", "name": "Normandy"},
                    {"code": "nouvelle-aquitaine", "name": "Nouvelle-Aquitaine"},
                    {"code": "occitanie", "name": "Occitanie"},
                    {"code": "pays-de-la-loire", "name": "Pays de la Loire"},
                    {"code": "provence-alpes-cote-dazur", "name": "Provence-Alpes-Côte d'Azur"},
                ]
            },
            {
                "code": "germany",
                "name": "Germany",
                "states": [
                    {"code": "baden-wuerttemberg", "name": "Baden-Württemberg"},
                    {"code": "bayern", "name": "Bayern"},
                    {"code": "berlin", "name": "Berlin"},
                    {"code": "brandenburg", "name": "Brandenburg"},
                    {"code": "bremen", "name": "Bremen"},
                    {"code": "hamburg", "name": "Hamburg"},
                    {"code": "hessen", "name": "Hessen"},
                    {"code": "mecklenburg-vorpommern", "name": "Mecklenburg-Vorpommern"},
                    {"code": "niedersachsen", "name": "Niedersachsen"},
                    {"code": "nordrhein-westfalen", "name": "Nordrhein-Westfalen"},
                    {"code": "rheinland-pfalz", "name": "Rheinland-Pfalz"},
                    {"code": "saarland", "name": "Saarland"},
                    {"code": "sachsen", "name": "Sachsen"},
                    {"code": "sachsen-anhalt", "name": "Sachsen-Anhalt"},
                    {"code": "schleswig-holstein", "name": "Schleswig-Holstein"},
                    {"code": "thueringen", "name": "Thüringen"},
                ]
            },
            {
                "code": "greece",
                "name": "Greece",
                "states": [
                    {"code": "attica", "name": "Attica"},
                    {"code": "central-greece", "name": "Central Greece"},
                    {"code": "central-macedonia", "name": "Central Macedonia"},
                    {"code": "crete", "name": "Crete"},
                    {"code": "peloponnese", "name": "Peloponnese"},
                    {"code": "thessaly", "name": "Thessaly"},
                ]
            },
            {
                "code": "hungary",
                "name": "Hungary",
                "states": [
                    {"code": "budapest", "name": "Budapest"},
                    {"code": "pest", "name": "Pest"},
                    {"code": "bacs-kiskun", "name": "Bács-Kiskun"},
                    {"code": "gyor-moson-sopron", "name": "Győr-Moson-Sopron"},
                    {"code": "hajdu-bihar", "name": "Hajdú-Bihar"},
                ]
            },
            {
                "code": "ireland",
                "name": "Ireland",
                "states": [
                    {"code": "connacht", "name": "Connacht"},
                    {"code": "leinster", "name": "Leinster"},
                    {"code": "munster", "name": "Munster"},
                    {"code": "ulster", "name": "Ulster"},
                ]
            },
            {
                "code": "italy",
                "name": "Italy",
                "states": [
                    {"code": "lombardy", "name": "Lombardy"},
                    {"code": "lazio", "name": "Lazio"},
                    {"code": "campania", "name": "Campania"},
                    {"code": "sicily", "name": "Sicily"},
                    {"code": "veneto", "name": "Veneto"},
                    {"code": "emilia-romagna", "name": "Emilia-Romagna"},
                    {"code": "piedmont", "name": "Piedmont"},
                    {"code": "tuscany", "name": "Tuscany"},
                ]
            },
            {
                "code": "luxembourg",
                "name": "Luxembourg",
                "states": [
                    {"code": "diekirch", "name": "Diekirch"},
                    {"code": "grevenmacher", "name": "Grevenmacher"},
                    {"code": "luxembourg", "name": "Luxembourg"},
                ]
            },
            {
                "code": "netherlands",
                "name": "Netherlands",
                "states": [
                    {"code": "drenthe", "name": "Drenthe"},
                    {"code": "flevoland", "name": "Flevoland"},
                    {"code": "friesland", "name": "Friesland"},
                    {"code": "gelderland", "name": "Gelderland"},
                    {"code": "groningen", "name": "Groningen"},
                    {"code": "limburg", "name": "Limburg"},
                    {"code": "noord-brabant", "name": "Noord-Brabant"},
                    {"code": "noord-holland", "name": "Noord-Holland"},
                    {"code": "overijssel", "name": "Overijssel"},
                    {"code": "utrecht", "name": "Utrecht"},
                    {"code": "zeeland", "name": "Zeeland"},
                    {"code": "zuid-holland", "name": "Zuid-Holland"},
                ]
            },
            {
                "code": "norway",
                "name": "Norway",
                "states": [
                    {"code": "oslo", "name": "Oslo"},
                    {"code": "rogaland", "name": "Rogaland"},
                    {"code": "vestland", "name": "Vestland"},
                    {"code": "trondelag", "name": "Trøndelag"},
                    {"code": "viken", "name": "Viken"},
                ]
            },
            {
                "code": "poland",
                "name": "Poland",
                "states": [
                    {"code": "masovian", "name": "Masovian"},
                    {"code": "greater-poland", "name": "Greater Poland"},
                    {"code": "lesser-poland", "name": "Lesser Poland"},
                    {"code": "silesian", "name": "Silesian"},
                    {"code": "lower-silesian", "name": "Lower Silesian"},
                    {"code": "pomeranian", "name": "Pomeranian"},
                ]
            },
            {
                "code": "portugal",
                "name": "Portugal",
                "states": [
                    {"code": "lisbon", "name": "Lisbon"},
                    {"code": "norte", "name": "Norte"},
                    {"code": "centro", "name": "Centro"},
                    {"code": "alentejo", "name": "Alentejo"},
                    {"code": "algarve", "name": "Algarve"},
                ]
            },
            {
                "code": "romania",
                "name": "Romania",
                "states": [
                    {"code": "bucharest", "name": "Bucharest"},
                    {"code": "center", "name": "Center"},
                    {"code": "north-west", "name": "North-West"},
                    {"code": "west", "name": "West"},
                ]
            },
            {
                "code": "slovakia",
                "name": "Slovakia",
                "states": [
                    {"code": "bratislava", "name": "Bratislava"},
                    {"code": "trnava", "name": "Trnava"},
                    {"code": "kosice", "name": "Košice"},
                ]
            },
            {
                "code": "slovenia",
                "name": "Slovenia",
                "states": [
                    {"code": "central-slovenia", "name": "Central Slovenia"},
                    {"code": "drava", "name": "Drava"},
                    {"code": "coastal-karst", "name": "Coastal-Karst"},
                ]
            },
            {
                "code": "spain",
                "name": "Spain",
                "states": [
                    {"code": "andalusia", "name": "Andalusia"},
                    {"code": "catalonia", "name": "Catalonia"},
                    {"code": "madrid", "name": "Madrid"},
                    {"code": "valencian-community", "name": "Valencian Community"},
                    {"code": "galicia", "name": "Galicia"},
                    {"code": "basque-country", "name": "Basque Country"},
                    {"code": "castile-and-leon", "name": "Castile and León"},
                ]
            },
            {
                "code": "sweden",
                "name": "Sweden",
                "states": [
                    {"code": "stockholm", "name": "Stockholm"},
                    {"code": "vastra-gotaland", "name": "Västra Götaland"},
                    {"code": "skane", "name": "Skåne"},
                    {"code": "ostergotland", "name": "Östergötland"},
                    {"code": "uppsala", "name": "Uppsala"},
                ]
            },
            {
                "code": "switzerland",
                "name": "Switzerland",
                "states": [
                    {"code": "zurich", "name": "Zürich"},
                    {"code": "bern", "name": "Bern"},
                    {"code": "geneva", "name": "Geneva"},
                    {"code": "basel-stadt", "name": "Basel-Stadt"},
                    {"code": "vaud", "name": "Vaud"},
                    {"code": "ticino", "name": "Ticino"},
                ]
            },
            {
                "code": "united-kingdom",
                "name": "United Kingdom",
                "states": [
                    {"code": "england", "name": "England"},
                    {"code": "scotland", "name": "Scotland"},
                    {"code": "wales", "name": "Wales"},
                    {"code": "northern-ireland", "name": "Northern Ireland"},
                ]
            }
        ]
    }


@router.get("/history")
def get_pipeline_history(limit: Optional[int] = 10):
    """Get the history of pipeline jobs."""
    jobs_list = list(pipeline_jobs.values())
    # Sort by started_at descending
    jobs_list.sort(key=lambda x: x.started_at or '', reverse=True)
    
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "country": job.country,
                "state": job.state,
                "step": job.step,
                "status": job.status,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error": job.error
            }
            for job in jobs_list[:limit]
        ]
    }


@router.get("/states/{country}")
def get_country_states(country: str, version_id: Optional[str] = None):
    """
    Return DB-backed state stats for a country, including grid counts.

    `country` can be a country name (e.g. `netherlands`) or ISO code (`NL`).
    """
    try:
        country_code = get_country_code(country.lower())
        target_version = version_id or VERSION_ID
        with DatabaseClient() as dbc:
            states = dbc.get_state_grid_stats(country=country_code, version_id=target_version)
        return {
            "country_code": country_code,
            "version_id": target_version,
            "states": states,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load states for {country}: {str(e)}")


@router.delete("/states/{country}/{state}")
def delete_state_data(
        country: str,
        state: str,
        dry_run: bool = Query(
            True,
            description="If true, only preview impacted rows. Set to false to execute deletion."
        ),
        drop_state_row: bool = Query(
            True,
            description="If true, also remove the state registry row from state table."
        ),
):
    """
    Delete one state scope across raw and generated tables.

    Deletion scope is country+state and includes postcode-linked grid data.
    """
    try:
        country_code = get_country_code(country.lower())
        with DatabaseClient() as dbc:
            result = dbc.delete_state_data(
                country=country_code,
                state_code=state,
                dry_run=dry_run,
                drop_state_row=drop_state_row,
            )
        return {
            "status": "dry_run" if dry_run else "deleted",
            **result,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete state {country}/{state}: {str(e)}")
