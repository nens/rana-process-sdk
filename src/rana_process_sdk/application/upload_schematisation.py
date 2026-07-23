import hashlib
import logging
import time
from pathlib import Path
from zipfile import ZipFile

import urllib3
from threedi_api_client.files import upload_file
from threedi_api_client.openapi import (
    Revision,
    RevisionRaster,
    Upload,
    V3Api,
)

UPLOAD_TIMEOUT = urllib3.Timeout(connect=60, read=600)
API_CLIENT_TIMEOUT = 10

__all__ = ["upload_schematisation"]

# Make a mapping from HCC API raster types to the expected file names.
# Some types have multiple expected file names for backwards compatibility, so we use a list of names for each type.
ALLOWED_RASTER_TYPES = [
    "dem_file",
    "equilibrium_infiltration_rate_file",
    "frict_coef_file",
    "initial_groundwater_level_file",
    "initial_waterlevel_file",
    "groundwater_hydro_connectivity_file",
    "groundwater_impervious_layer_level_file",
    "infiltration_decay_period_file",
    "initial_infiltration_rate_file",
    "leakage_file",
    "phreatic_storage_capacity_file",
    "hydraulic_conductivity_file",
    "porosity_file",
    "infiltration_rate_file",
    "max_infiltration_capacity_file",
    "interception_file",
    "vegetation_height_file",
    "vegetation_drag_coefficient_file",
    "vegetation_stem_count_file",
    "vegetation_stem_diameter_file",
    "initial_groundwater_concentration_file",
]
RASTER_FILE_NAMES = {x: [x[:-5] + ".tif"] for x in ALLOWED_RASTER_TYPES}
RASTER_FILE_NAMES["frict_coef_file"].append("friction.tif")
RASTER_FILE_NAMES["infiltration_rate_file"].append("infiltration.tif")


def md5(fname: Path) -> str:
    """
    Computes the MD5 checksum of a file.

    Parameters:
    - fname (Path): Path to the file.

    Returns:
    - str: The MD5 checksum as a hexadecimal string.
    """
    hash_md5 = hashlib.md5()
    with fname.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def upload_sqlite(
    threedi_api: V3Api,
    schematisation_id: int,
    revision_id: int,
    sqlite_path: Path,
) -> None:
    sqlite_zip_path = sqlite_path.with_suffix(".zip")
    with ZipFile(sqlite_zip_path, mode="w") as f:
        f.write(sqlite_path, arcname=sqlite_path.name)
    upload: Upload = threedi_api.schematisations_revisions_sqlite_upload(
        id=revision_id,
        schematisation_pk=schematisation_id,
        data={"filename": sqlite_zip_path.name},
        _request_timeout=API_CLIENT_TIMEOUT,
    )
    assert upload.put_url, "Upload URL should not be None"
    upload_file(upload.put_url, sqlite_zip_path, timeout=UPLOAD_TIMEOUT)


def upload_raster(
    threedi_api: V3Api,
    revision_id: int,
    schematisation_id: int,
    raster_type: str,
    raster_path: Path,
) -> None:
    md5sum = md5(raster_path)
    data = {"name": raster_path.name, "type": raster_type, "md5sum": md5sum}
    raster_create: RevisionRaster = (
        threedi_api.schematisations_revisions_rasters_create(
            revision_id, schematisation_id, data, _request_timeout=API_CLIENT_TIMEOUT
        )
    )
    if raster_create.file and raster_create.file.state == "uploaded":
        return

    data = {"filename": raster_path.name}
    upload: Upload = threedi_api.schematisations_revisions_rasters_upload(
        raster_create.id,
        revision_id,
        schematisation_id,
        data,
        _request_timeout=API_CLIENT_TIMEOUT,
    )
    assert upload.put_url, "Upload URL should not be None"

    upload_file(upload.put_url, raster_path, timeout=UPLOAD_TIMEOUT)


def commit_revision(
    threedi_api: V3Api, revision_id: int, schematisation_id: int, commit_message: str
) -> None:
    # First wait for all files to have turned to 'uploaded'
    for wait_time in [0.5, 1.0, 2.0, 10.0, 30.0, 60.0, 120.0, 300.0]:
        revision: Revision = threedi_api.schematisations_revisions_read(
            revision_id, schematisation_id, _request_timeout=API_CLIENT_TIMEOUT
        )
        states = [revision.sqlite.file.state]
        states.extend([raster.file.state for raster in revision.rasters])

        if all(state == "uploaded" for state in states):
            break
        elif any(state == "created" for state in states):
            time.sleep(wait_time)
            continue
        else:
            raise RuntimeError("One or more rasters have an unexpected state")
    else:
        raise RuntimeError("Some files are still in 'created' state")

    threedi_api.schematisations_revisions_commit(
        revision_id,
        schematisation_id,
        {"commit_message": commit_message},
        _request_timeout=API_CLIENT_TIMEOUT,
    )


def upload_schematisation(
    threedi_api: V3Api,
    schematisation_id: int,
    local_dir: Path,
    commit_message: str | None = None,
) -> None:
    # Find the first path in the root with .gpkg, that is the sqlite file
    sqlite_path = next(
        (local_dir / f for f in local_dir.iterdir() if f.suffix.lower() == ".gpkg"),
        None,
    )
    if sqlite_path is None:
        raise RuntimeError("The geopackage failed to generate")

    # Nieuwe (lege) revisie aanmaken
    revision_id = threedi_api.schematisations_revisions_create(
        schematisation_id, data={"empty": True}, _request_timeout=API_CLIENT_TIMEOUT
    ).id

    # Data uploaden
    # # Spatialite
    logging.info(f"Saving '{sqlite_path.name}'...")
    upload_sqlite(
        threedi_api=threedi_api,
        schematisation_id=schematisation_id,
        revision_id=revision_id,
        sqlite_path=sqlite_path,
    )

    # # Rasters
    for raster_type, raster_file_name_options in RASTER_FILE_NAMES.items():
        for raster_file_name in raster_file_name_options:
            raster_path = local_dir / raster_file_name
            if raster_path.exists():
                break
        else:
            continue  # No raster file found for this type, skip to the next type
        logging.info(f"Saving '{raster_path.name}'...")
        upload_raster(
            threedi_api=threedi_api,
            revision_id=revision_id,
            schematisation_id=schematisation_id,
            raster_type=raster_type,
            raster_path=raster_path,
        )

    # Commit revision
    commit_revision(
        threedi_api=threedi_api,
        revision_id=revision_id,
        schematisation_id=schematisation_id,
        commit_message=commit_message or "Created schematisation",
    )
