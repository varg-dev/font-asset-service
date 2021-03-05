import os
import shutil
from typing import Optional, List
import subprocess

import json
import hashlib
import base64

from pydantic import BaseModel

from fastapi import APIRouter, Response, File, UploadFile, Depends
from fastapi import HTTPException, status
from fastapi.responses import FileResponse


router = APIRouter()


LLASSETGEN_DIRECTORY=os.environ.get('LLASSETGEN_DIRECTORY', '')
RESULT_DIR=os.environ.get('RESULT_DIR', '/data/results')


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


def make_hash_sha256(o):
    hasher = hashlib.sha256()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()


def make_hashable(o):
    if isinstance(o, (tuple, list)):
        return tuple((make_hashable(e) for e in o))

    if isinstance(o, dict):
        return tuple(sorted((k,make_hashable(v)) for k,v in o.items()))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in o))

    return o


class FontModel(BaseModel):
    identifier: Optional[str] = ''
    format: Optional[str] = ''


class AtlasAssetParameterModel(BaseModel):
    distfield: Optional[str] = 'parabola' # either 'parabola' or 'deadrec'
    packing: Optional[str] = 'shelf' # either 'shelf' or 'maxrects'
    glyph: Optional[str] = ''
    charcode: Optional[str] = ''
    ascii: Optional[bool] = True
    fontsize: Optional[int] = 128
    padding: Optional[int] = 0
    downsampling_factor: Optional[int] = 1
    downsampling: Optional[str] = 'center' # either 'center', 'average', or 'min'
    dynamicrange: Optional[List[int]] = []


# TODO: implement
# class DistanceFieldAssetParameterModel(BaseModel):
#     algorithm: Optional[str] = 'parabola' # either 'parabola' or 'deadrec'
#     dynamicrange: Optional[List[int]] = []


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
async def api_post_fonts(response: Response, font_details: Optional[FontModel] = Depends(FontModel), file: UploadFile = File(...)):
    
    filename, extension = os.path.splitext(os.path.basename(file.filename))

    if not font_details.identifier:
        font_details.identifier = filename
    
    if not font_details.format:
        font_details.format = extension
    
    path = os.path.join(fonts_dir(), font_details.identifier + font_details.format)

    if os.path.exists(path):
        response.status_code = status.HTTP_409_CONFLICT
        return {}

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

    path = os.path.join(fonts_dir(), identifier + '_assets')

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
    
    if os.path.exists(path):
        if force:
            shutil.rmtree(path, ignore_errors=True)
        else:
            response.status_code = status.HTTP_409_CONFLICT
            return {}
    
    os.mkdir(path)

    metainfo_path = os.path.join(path, 'metainfo.json')
    
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
        arguments.extend([ '--distfield', asset_parameters.distfield ])
    if asset_parameters.packing:
        arguments.extend([ '--packing', asset_parameters.packing ])
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
        arguments.extend([ '--dsalgo', asset_parameters.downsampling ])
    if asset_parameters.dynamicrange and len(asset_parameters.dynamicrange) >= 2:
        arguments.extend([ '--dynamicrange', str(asset_parameters.dynamicrange[0]), str(asset_parameters.dynamicrange[1]) ])
    arguments.extend([ distancefield_filename ])

    print(' '.join(arguments), flush=True)

    p = subprocess.run(arguments, capture_output=True, cwd=path)
    output = p.stdout.decode("utf-8")
    
    if not os.path.exists(os.path.join(path, distancefield_filename)) \
        or not os.path.exists(os.path.join(path, fontdescription_filename)):
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {}

    metainfo['assets']['distancefield'] = {
        'path': os.path.join(path, distancefield_filename),
        'identifier': distancefield_filename
    }
    metainfo['assets']['fontdescription'] = {
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
async def api_head_font_asset_download(identifier: str, asset_parameter_hash: str, asset_type: str, response: Response):

    path = os.path.join(fonts_dir(), identifier + "_assets")

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

    path = os.path.join(fonts_dir(), identifier + "_assets")

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

    return FileResponse(asset_info['path'], filename=os.path.basename(asset_info['identifier']), media_type='application/octet-stream')
