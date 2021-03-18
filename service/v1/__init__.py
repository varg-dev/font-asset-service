import os
import shutil
from typing import Optional, List
import subprocess
from enum import Enum

import json

from pydantic import BaseModel

from fastapi import APIRouter, Response, File, UploadFile, Depends
from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from ..helpers import *


router = APIRouter()


LLASSETGEN_DIRECTORY=os.environ.get('LLASSETGEN_DIRECTORY', '')


# TODO: handle system fonts
# system_fonts_parsed = False
# parsed_system_fonts = []

# def system_fonts():
#     global system_fonts_parsed
#     global parsed_system_fonts
# 
#     if not system_fonts_parsed:
#         system_fonts_parsed = True
#         
#         p = subprocess.run(["fc-list"], capture_output=True)
#         font_list = p.stdout.decode("utf-8")
# 
#         print(font_list, flush=True)
# 
#     return parsed_system_fonts

class FontModel(BaseModel):
    identifier: Optional[str] = ''
    format: Optional[str] = ''


class DistanceFieldAlgorithm(str, Enum):
    parabola = 'parabola'
    deadrec = 'deadrec'


class PackingAlgorithm(str, Enum):
    shelf = 'shelf'
    maxrects = 'maxrects'


class DownSamplingAlgorithm(str, Enum):
    center = 'center'
    average = 'average'
    min = 'min'


class AssetType(str, Enum):
    distancefield = 'distancefield'
    fontdescription = 'fontdescription'


class AtlasAssetParameterModel(BaseModel):
    distfield: Optional[DistanceFieldAlgorithm] = DistanceFieldAlgorithm.parabola
    packing: Optional[PackingAlgorithm] = PackingAlgorithm.shelf
    glyph: Optional[str] = ''
    charcode: Optional[str] = ''
    ascii: Optional[bool] = True
    fontsize: Optional[int] = 128
    padding: Optional[int] = 0
    downsampling_factor: Optional[int] = 1
    downsampling: Optional[DownSamplingAlgorithm] = DownSamplingAlgorithm.center
    dynamicrange: Optional[List[int]] = []


# TODO: implement
# class DistanceFieldAssetParameterModel(BaseModel):
#     algorithm: Optional[DistanceFieldAlgorithm] = DistanceFieldAlgorithm.parabola
#     dynamicrange: Optional[List[int]] = []


# ROOT

@router.get("/", tags=[""])
async def api_get_root():
    return {}


@router.head("/", tags=[""])
async def api_head_root(response: Response):
    response.status_code = status.HTTP_200_OK


@router.post("/generate_parameter_hash", tags=["tooling"])
async def api_post_generate_parameter_hash(asset_parameters: AtlasAssetParameterModel, response: Response):
    return {'hash': make_hash_sha256(asset_parameters.dict()) }


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
async def api_post_fonts(response: Response, font_details: Optional[FontModel] = Depends(FontModel), file: UploadFile = File(...)):
    
    filename, extension = os.path.splitext(os.path.basename(file.filename))

    if not font_details.identifier:
        font_details.identifier = filename
    
    if not font_details.format:
        font_details.format = extension
    
    path = os.path.join(fonts_dir(), font_details.identifier + font_details.format)

    if os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Font already created.',
        )

    with open(path, 'w+b') as f:
        shutil.copyfileobj(file.file, f)

    response.status_code = status.HTTP_201_CREATED
    return {
        'identifier': font_details.identifier + font_details.format,
        'format': font_details.format,
        'assets': {},
        'url': f'/fonts/{font_details.identifier + font_details.format}'
    }


@router.head("/fonts/{identifier}", tags=["fonts"])
async def api_head_font(identifier: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Font not found.',
        )
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}", tags=["fonts"])
async def api_get_font(identifier: str, response: Response):

    path = os.path.join(fonts_dir(), identifier)

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Font not found.',
        )
    
    response.status_code = status.HTTP_200_OK

    filename, extension = os.path.splitext(os.path.basename(path))

    result = []
    assets_path = path + '_assets'
    if os.path.exists(assets_path):
        for entry in os.scandir(assets_path):
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

    path = os.path.join(fonts_dir(), identifier + '_assets')

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}/{asset_parameter_hash}", tags=["assets"])
async def api_get_font_asset(identifier: str, asset_parameter_hash: str, response: Response):

    path = os.path.join(fonts_dir(), identifier + '_assets')

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Assets not found.',
        )
    
    assets_info = metainfo['assets']
    
    response.status_code = status.HTTP_200_OK

    result = []

    for asset_type in assets_info:
        result.append({
            'type': asset_type,
            'url': f'/fonts/{identifier}/{asset_parameter_hash}/{asset_type}',
        })

    return {
        'url': f'/fonts/{identifier}/{asset_parameter_hash}',
        'hash': asset_parameter_hash,
        'arguments': metainfo['arguments'],
        'assets': result
    }


@router.post("/fonts/{identifier}", tags=["assets"])
async def api_post_font_assets(identifier: str, asset_parameters: AtlasAssetParameterModel, response: Response, force: Optional[bool] = False):

    asset_parameter_hash = make_hash_sha256(asset_parameters.dict())

    font_path = os.path.join(fonts_dir(), identifier)
    path = os.path.join(fonts_dir(), identifier + '_assets')

    if not os.path.exists(path):
        os.mkdir(path)
    
    path = os.path.join(path, asset_parameter_hash)
    
    metainfo_path = os.path.join(path, 'metainfo.json')
    
    if os.path.exists(path) and os.path.exists(metainfo_path):
        if force:
            shutil.rmtree(path, ignore_errors=True)
        else:
            metainfo = {}
            with open(metainfo_path, 'r') as f:
                metainfo = json.load(f)
            
            if not 'assets' in metainfo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Assets not found.',
                )
            
            assets_info = metainfo['assets']
            
            response.status_code = status.HTTP_409_CONFLICT

            result = []

            for asset_type in assets_info:
                result.append({
                    'type': asset_type,
                    'url': f'/fonts/{identifier}/{asset_parameter_hash}/{asset_type}',
                })

            return {
                'url': f'/fonts/{identifier}/{asset_parameter_hash}',
                'hash': asset_parameter_hash,
                'arguments': metainfo['arguments'],
                'assets': result
            }
    
    os.mkdir(path)

    metainfo = {
        'arguments': asset_parameters.dict(),
        'assets': {}
    }

    # Call llassetgen

    distancefield_filename = "distancefield.png"
    fontdescription_filename = "distancefield.fnt"

    llassetgen_binary = '/opt/font-assets/openll-asset-generator/build/llassetgen-cmd'
    arguments = [ llassetgen_binary, "atlas", "--fontpath", font_path, "--fnt" ]
    if asset_parameters.distfield:
        arguments.extend([ '--distfield', asset_parameters.distfield.value ])
    if asset_parameters.packing:
        arguments.extend([ '--packing', asset_parameters.packing.value ])
    if asset_parameters.glyph:
        arguments.extend([ '--glyph', asset_parameters.glyph ])
    if asset_parameters.charcode:
        arguments.extend([ '--charcode', asset_parameters.charcode ])
    if asset_parameters.ascii:
        arguments.extend([ '--ascii' ])
    if asset_parameters.fontsize:
        arguments.extend([ '--fontsize', str(asset_parameters.fontsize) ])
    if asset_parameters.padding:
        arguments.extend([ '--padding', str(asset_parameters.padding) ])
    if asset_parameters.downsampling_factor and asset_parameters.downsampling_factor > 1:
        arguments.extend([ '--downsampling', str(asset_parameters.downsampling_factor) ])
    if asset_parameters.downsampling:
        arguments.extend([ '--dsalgo', asset_parameters.downsampling.value ])
    if asset_parameters.dynamicrange and len(asset_parameters.dynamicrange) >= 2:
        arguments.extend([ '--dynamicrange', str(asset_parameters.dynamicrange[0]), str(asset_parameters.dynamicrange[1]) ])
    arguments.extend([ distancefield_filename ])

    try:
        print(' '.join(arguments), flush=True)
        p = subprocess.run(arguments, capture_output=True, check=True, cwd=path)
    except:
        print(p.stdout.decode("utf-8"), flush=True)
        print(p.stderr.decode("utf-8"), flush=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=p.stderr.decode("utf-8"),
        )
    
    if not os.path.exists(os.path.join(path, distancefield_filename)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Distance field file not created.',
        )

    if not os.path.exists(os.path.join(path, fontdescription_filename)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Font file not created.',
        )
    
    metainfo['assets'][AssetType.distancefield.value] = {
        'path': os.path.join(path, distancefield_filename),
        'identifier': distancefield_filename
    }
    metainfo['assets'][AssetType.fontdescription.value] = {
        'path': os.path.join(path, fontdescription_filename),
        'identifier': fontdescription_filename
    }

    with open(metainfo_path, 'w') as f:
        json.dump(metainfo, f)
    
    response.status_code = status.HTTP_201_CREATED

    result = []
    for asset_type in metainfo['assets']:
        result.append({
            'type': asset_type,
            'url': f'/fonts/{identifier}/{asset_parameter_hash}/{asset_type}',
        })

    return {
        'url': f'/fonts/{identifier}/{asset_parameter_hash}',
        'hash': asset_parameter_hash,
        'arguments': metainfo['arguments'],
        'assets': result
    }


# ASSETS DOWNLOAD

@router.head("/fonts/{identifier}/{asset_parameter_hash}/{asset_type}", tags=["assets"])
async def api_head_font_asset_download(identifier: str, asset_parameter_hash: str, asset_type: AssetType, response: Response):

    path = os.path.join(fonts_dir(), identifier + "_assets")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    if not asset_type.value in metainfo['assets']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    response.status_code = status.HTTP_200_OK


@router.get("/fonts/{identifier}/{asset_parameter_hash}/{asset_type}", tags=["assets"])
async def api_get_font_asset_download(identifier: str, asset_parameter_hash: str, asset_type: AssetType, response: Response):

    path = os.path.join(fonts_dir(), identifier + "_assets")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    path = os.path.join(path, asset_parameter_hash)
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    path = os.path.join(path, 'metainfo.json')
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    metainfo = {}
    with open(path, 'r') as f:
        metainfo = json.load(f)
    
    if not 'assets' in metainfo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    if not asset_type.value in metainfo['assets']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Asset not found.',
        )
    
    asset_info = metainfo['assets'][asset_type.value]
    
    response.status_code = status.HTTP_200_OK

    return FileResponse(asset_info['path'], filename=os.path.basename(asset_info['identifier']), media_type='application/octet-stream')
