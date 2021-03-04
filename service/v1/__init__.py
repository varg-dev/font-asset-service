import os
import shutil
from datetime import timedelta
from typing import Optional

import json

from pydantic import BaseModel
from typing import List

from fastapi import APIRouter, Response, BackgroundTasks, File, UploadFile
from fastapi import HTTPException, status, Depends
from fastapi.responses import FileResponse, StreamingResponse


router = APIRouter()

LLASSETGEN_DIRECTORY=os.environ.get('LLASSETGEN_DIRECTORY', '')
RESULT_DIR=os.environ.get('RESULT_DIR', '/data/results')

def results_dir():
    directory = RESULT_DIR

    if not os.path.exists(directory):
        os.mkdir(directory)
    
    return directory


def fonts_dir():
    directory = os.path.join(results_dir(), 'fonts')

    if not os.path.exists(directory):
        os.mkdir(directory)
    
    return directory


class FontModel(BaseModel):
    identifier: str = ''
    format: str = ''


# ROOT

@router.get("/", tags=[""])
async def api_get_root():
    return {}


@router.head("/", tags=[""])
async def api_head_root(response: Response):
    response.status_code = status.HTTP_200_OK


# FONTS

@router.get("/fonts", tags=["fonts"])
async def api_get_fonts(response: Response):

    directory = fonts_dir()

    result = []
    for entry in os.scandir(directory):
        if entry.is_file():
            filename, extension = os.path.splitext(os.path.basename(entry.path))
            result.append({
                'identifier': filename+extension,
                'format': extension,
                'url': f'/fonts/{filename+extension}'
            })
    
    response.status_code = status.HTTP_200_OK
    
    return result


@router.head("/fonts", tags=["fonts"])
async def api_head_fonts(response: Response):
    
    response.status_code = status.HTTP_200_OK


@router.post("/fonts", tags=["fonts"])
async def api_post_fonts(response: Response, font: FontModel = Depends(FontModel), file: UploadFile = File(...)):
    
    filename, extension = os.path.splitext(os.path.basename(file.filename))

    if not font.identifier:
        font.identifier = filename
    
    if not font.format:
        font.format = extension
    
    path = os.path.join(fonts_dir(), font.identifier + font.format)

    if os.path.exists(path):
        response.status_code = status.HTTP_409_CONFLICT
        return {}

    with open(path, 'w+b') as f:
        shutil.copyfileobj(file.file, f)

    response.status_code = status.HTTP_201_CREATED
    return {}


@router.head("/fonts/{identifier}", tags=["fonts"])
async def api_head_font(identifier: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}", tags=["fonts"])
async def api_get_font(identifier: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    response.status_code = status.HTTP_200_OK

    filename, extension = os.path.splitext(os.path.basename(path))

    result = []
    for entry in os.scandir(path):
        if entry.is_dir():
            basename = os.path.basename(entry.path)
            result.append({
                'identifier': basename,
                'url': f'/fonts/{identifier}/{basename}'
            })
    
    response.status_code = status.HTTP_200_OK
    
    return {
        'identifier': filename+extension,
        'format': extension,
        'assets': result,
        'url': f'/fonts/{identifier}'
    }


# ASSETS

@router.head("/fonts/{identifier}/{asset_parameter_hash}", tags=["assets"])
async def api_head_font_asset(identifier: str, asset_parameter_hash: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        response.status_code = status.HTTP_409_CONFLICT
        return {}
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}/{asset_parameter_hash}", tags=["assets"])
async def api_get_font_asset(identifier: str, asset_parameter_hash: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        response.status_code = status.HTTP_409_CONFLICT
        return {}
    
    assets_info = metainfo['assets']
    
    response.status_code = status.HTTP_200_OK

    result = []

    for asset_type in assets_info:
        asset_info = assets_info[asset_type]
        result.append({
            'type': asset_type,
            'arguments': asset_info['arguments'],
            'url': f'/fonts/{identifier}/{asset_parameter_hash}/{asset_type}',
        })

    return result


# ASSETS DOWNLOAD

@router.head("/fonts/{identifier}/{asset_parameter_hash}/{asset_type}", tags=["assets"])
async def api_head_font_asset_download(identifier: str, asset_parameter_hash: str, asset_type: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        response.status_code = status.HTTP_409_CONFLICT
        return {}
    
    if not asset_type in metainfo['assets']:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}/{asset_parameter_hash}/{asset_type}", tags=["assets"])
async def api_get_font_asset_download(identifier: str, asset_parameter_hash: str, asset_type: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        response.status_code = status.HTTP_409_CONFLICT
        return {}
    
    if not asset_type in metainfo['assets']:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    asset_info = metainfo['assets'][asset_type]
    
    response.status_code = status.HTTP_200_OK

    return FileResponse(asset_info.path, filename=os.path.basename(asset_info.identifier), media_type='application/octet-stream')
