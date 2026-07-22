import hashlib
import logging
import time
from pathlib import Path
from zipfile import ZipFile

import urllib3
from threedi_api_client.api import ThreediApi
from threedi_api_client.files import upload_file
from threedi_api_client.openapi import Revision

UPLOAD_TIMEOUT = urllib3.Timeout(connect=60, read=600)
API_CLIENT_TIMEOUT = 10

__all__ = ["upload_schematisation"]


def md5(fname: str | Path) -> str:
    """
    Computes the MD5 checksum of a file.

    Parameters:
    - fname (str | Path): Path to the file.

    Returns:
    - str: The MD5 checksum as a hexadecimal string.
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def upload_sqlite(
    threedi_api: ThreediApi,
    schematisation_id: int,
    revision_id: int,
    sqlite_path: str | Path,
) -> None:
    sqlite_path = Path(sqlite_path)
    sqlite_zip_path = sqlite_path.with_suffix(".zip")
    ZipFile(sqlite_zip_path, mode="w").write(
        str(sqlite_path), arcname=str(sqlite_path.name)
    )
    upload = threedi_api.schematisations_revisions_sqlite_upload(
        id=revision_id,
        schematisation_pk=schematisation_id,
        data={"filename": str(sqlite_zip_path.name)},
        _request_timeout=API_CLIENT_TIMEOUT,
    )
    if upload.put_url is None:
        logging.info(f"Sqlite '{sqlite_path.name}' already existed, skipping upload.")
    else:
        logging.info(f"Uploading '{str(sqlite_path.name)}'...")
        upload_file(upload.put_url, sqlite_zip_path, timeout=UPLOAD_TIMEOUT)


def upload_raster(
    threedi_api: ThreediApi,
    rev_id: int,
    schema_id: int,
    raster_type: str,
    raster_path: str | Path,
) -> None:
    logging.info(f"Creating '{raster_type}' raster...")
    raster_path = Path(raster_path)
    md5sum = md5(str(raster_path))
    data = {"name": raster_path.name, "type": raster_type, "md5sum": md5sum}
    raster_create = threedi_api.schematisations_revisions_rasters_create(
        rev_id, schema_id, data, _request_timeout=API_CLIENT_TIMEOUT
    )
    if raster_create.file and raster_create.file.state == "uploaded":
        logging.info(f"Raster '{raster_path}' already exists, skipping upload.")
        return

    logging.info(f"Uploading '{raster_path}'...")
    data = {"filename": raster_path.name}
    upload = threedi_api.schematisations_revisions_rasters_upload(
        raster_create.id, rev_id, schema_id, data, _request_timeout=API_CLIENT_TIMEOUT
    )

    upload_file(upload.put_url, raster_path, timeout=UPLOAD_TIMEOUT)


def commit_revision(
    threedi_api: ThreediApi, rev_id: int, schema_id: int, commit_message: str
) -> Revision:
    # First wait for all files to have turned to 'uploaded'
    for wait_time in [0.5, 1.0, 2.0, 10.0, 30.0, 60.0, 120.0, 300.0]:
        revision = threedi_api.schematisations_revisions_read(
            rev_id, schema_id, _request_timeout=API_CLIENT_TIMEOUT
        )
        states = [revision.sqlite.file.state]
        states.extend([raster.file.state for raster in revision.rasters])

        if all(state == "uploaded" for state in states):
            break
        elif any(state == "created" for state in states):
            logging.info(
                f"Sleeping {wait_time} seconds to wait for the files to become 'uploaded'..."
            )
            time.sleep(wait_time)
            continue
        else:
            raise RuntimeError("One or more rasters have an unexpected state")
    else:
        raise RuntimeError("Some files are still in 'created' state")

    schematisation_revision: Revision = threedi_api.schematisations_revisions_commit(
        rev_id,
        schema_id,
        {"commit_message": commit_message},
        _request_timeout=API_CLIENT_TIMEOUT,
    )

    logging.info(f"Committed revision {revision.number}.")
    return schematisation_revision


def upload_schematisation(
    threedi_api: ThreediApi,
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
        raise RuntimeError("The geopackages failed to generate")

    # Nieuwe (lege) revisie aanmaken
    revision: Revision = threedi_api.schematisations_revisions_create(
        schematisation_id, data={"empty": True}, _request_timeout=API_CLIENT_TIMEOUT
    )
    revision_id: int = revision.id  # type: ignore

    # Data uploaden
    # # Spatialite
    upload_sqlite(
        threedi_api=threedi_api,
        schematisation_id=schematisation_id,
        revision_id=revision_id,
        sqlite_path=sqlite_path,
    )

    # # Rasters
    rasters = {
        "dem.tif": "dem_file",
        "infiltration.tif": "infiltration_rate_file",
        "friction.tif": "frict_coef_file",
    }

    for raster_file, raster_type in rasters.items():
        raster_path = local_dir / raster_file
        if not raster_path.exists():
            continue
        upload_raster(
            threedi_api=threedi_api,
            rev_id=revision_id,
            schema_id=schematisation_id,
            raster_type=raster_type,
            raster_path=raster_path,
        )

    # Commit revision
    commit_revision(
        threedi_api=threedi_api,
        rev_id=revision_id,
        schema_id=schematisation_id,
        commit_message=commit_message or "Created schematisation",
    )
