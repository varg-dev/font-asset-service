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


@router.head("/fonts/{identifier}", tags=["fonts"])
async def api_head_font(identifier: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    
    response.status_code = status.HTTP_200_OK

    filename, extension = os.path.splitext(os.path.basename(path))
    
    return {
        'identifier': filename+extension,
        'format': extension,
        'url': f'/fonts/{filename+extension}'
    }


# ASSETS
