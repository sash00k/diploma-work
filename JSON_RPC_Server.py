from fastapi import FastAPI, Request
from datetime import date
from random import randint
from pybase64 import b64decode
from os import listdir
from os.path import isfile, join
from PydanticModels import *
from dotenv import load_dotenv, find_dotenv

import io
import numpy as np
import json
import asyncio
import uvicorn
import subprocess
import os
import re
import shutil

load_dotenv(find_dotenv(), override=True)
rpc_host = os.getenv('RPC_HOST')

app = jsonrpc.API()
api_v1 = jsonrpc.Entrypoint('/api/v1/jsonrpc')

async def remove_files_and_folders():
    items_to_remove = [
        'iteration_statistic.txt',
        'echo_output.txt',
        'StressRotated',
        'Stress',
        'Patran',
        'Failure',
        'Displacements'
    ]

    for item_name in items_to_remove:
        if os.path.exists(item_name):
            try:
                if os.path.isfile(item_name):
                    os.remove(item_name)
                else:
                    shutil.rmtree(item_name)
            except Exception as e:
                pass
        else:
            pass

async def process_files_in_folder(folder: str, model_class: type) -> Dict[str, List[BaseModelWithFileParsing]]:
    data = {}
    try:
        files = sorted(os.listdir(folder), key=lambda x: int(re.search(r'\d+', x).group()))
        for file_number, filename in enumerate(files, start=1):
            if filename.startswith(f'{model_class.__name__}.'):
                file_path = os.path.join(folder, filename)
                data[f'{model_class.__name__}.{file_number}'] = model_class.parse_file(file_path)
        return data
    except Exception as error:
        raise Error(
            data={'details': f"JSON-RPC server error while reading '{folder}' folder:\n{error}", 'status_code': 502})


async def run_fc_2022initstrss():
    await remove_files_and_folders()
    subprocess.run(['FC_2022initStrss.exe'], check=True)


async def check_file(fileName, status_code):
    if not os.path.exists(fileName):
        raise Error(data={'details': f"The file '{fileName}' was not found", 'status_code': status_code})
    return True

async def run_pioner_exe() -> ProcessOutputModel:
    if await check_file('input.txt', 500):
        try:
            await run_fc_2022initstrss()
            displacements_data = await process_files_in_folder('Displacements', Displacements)
            stress_data = await process_files_in_folder('Stress', Stress)
            result = ProcessOutputModel(displacements=displacements_data,stress=stress_data)
            return result
        except subprocess.CalledProcessError as e:
            raise Error(data={'details': f'Error while executing the process: {e}', 'status_code': 501})
        except Exception as e:
            raise Error(data={'details': f'JSON-RPC server error: {e}', 'status_code': 505})

async def run_selected_template(in_file: InputTemplateModel) -> ProcessOutputModel:
    content = in_file.fileContent
    with open('input.txt', 'w') as output_file:
        output_file.write(content)
    return await run_pioner_exe()

def get_template_files() -> List[str]:
    file_path = f'InputTemplates'
    onlyfiles = [f for f in listdir(file_path) if isfile(join(file_path, f))]
    return onlyfiles

@api_v1.method(errors=[Error])
async def save_input_template(in_params: InputTemplateModel) -> bool:
    file_path = f'InputTemplates/{in_params.fileName}'
    ret = {}
    try:
        pass
        with open(file_path, 'w') as file:
            file.write(in_params.fileContent)
        ret['result'] = True
    except Exception as e:
        raise Error(data={'details': f'JSON-RPC server error: {e}', 'status_code': 508})
    return True

@api_v1.method(errors=[Error])
async def get_template_list() -> List[InputTemplateModel]:
    ret = []
    files = get_template_files()
    for it in files:
        ret.append(InputTemplateModel(fileName=it))
    return ret

@api_v1.method(errors=[Error])
async def run_pioner(in_params: InputTemplateModel) -> ProcessOutputModel:
    print('run', in_params.dict())
    return await run_selected_template(in_params)


@api_v1.method(errors=[Error])
async def get_content_by_name(in_params: InputTemplateModel) -> InputTemplateModel:
    if await check_file(f'InputTemplates/{in_params.fileName}', 401):
        try:
            with open(f'InputTemplates/{in_params.fileName}', 'r') as file:
                content = file.read()
        except Exception as e:
            raise Error(data={'details': f'JSON-RPC get_content_by_name error: {e}', 'status_code': 509})
    return InputTemplateModel(fileName=in_params.fileName, fileContent=content)


app.bind_entrypoint(api_v1)

if __name__ == '__main__':

    uvicorn.run(app, host=rpc_host, port=8001, access_log=True)