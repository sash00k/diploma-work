from os import listdir
from os.path import isfile, join
from PydanticModels import *
from dotenv import load_dotenv, find_dotenv

import asyncio
import sys
import uvicorn
import subprocess
import os
import re
import shutil

load_dotenv(find_dotenv(), override=True)
RPC_HOST = os.getenv('RPC_HOST')

app = jsonrpc.API()
api_v1 = jsonrpc.Entrypoint('/api/v1/jsonrpc')

PROCESS = None


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
                print(e)
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
        print(error)
        raise Error(
            data={'details': f"JSON-RPC server error while reading '{folder}' folder:\n{error}", 'status_code': 502})


async def check_file(file_name, status_code):
    if not os.path.exists(file_name):
        raise Error(data={'details': f"The file '{file_name}' was not found", 'status_code': status_code})
    return True


async def get_process_ready_results() -> ProcessOutputModel:
    displacements_data = await process_files_in_folder('Displacements', Displacements)
    stress_data = await process_files_in_folder('Stress', Stress)
    return ProcessOutputModel(displacements=displacements_data,stress=stress_data,status='finished')


async def get_process_status() -> str:
    global PROCESS
    if PROCESS is None:
        return 'not started'
    elif PROCESS.poll() is None:
        return 'running'
    else:
        return 'finished'
    

async def get_process_results() -> ProcessOutputModel:
    if (status := await get_process_status()) == 'finished':
        return await get_process_ready_results()
    else:
        return ProcessOutputModel(status=status)


class FakeProcess:
    def __init__(self, duration):
        self.duration = duration
        self._returncode = None

    async def run(self):
        await asyncio.sleep(self.duration)
        self._returncode = 0

    def poll(self):
        return self._returncode


async def run_fc_2022initstrss(background: bool = False, executable_file: str = 'FC_2022initStrss_real.exe'):
    global PROCESS
    if sys.platform.startswith('win'):
        await remove_files_and_folders()
        if background:
            PROCESS = subprocess.Popen([executable_file])
        else:
            PROCESS = subprocess.run([executable_file])
    else:
        # затычка, которая просто "думает", если не может запустить процесс
        PROCESS = FakeProcess(1)
        if background: 
            asyncio.create_task(PROCESS.run())
        else:
            await PROCESS.run()


async def run_pioner_exe(background: bool = False) -> ProcessOutputModel:
    if await check_file('input.txt', 500):
        try:
            await run_fc_2022initstrss(background=background)
            return await get_process_results()
        except subprocess.CalledProcessError as e:
            print(e)
            raise Error(data={'details': f'Error while executing the process: {e}', 'status_code': 501})
        except Exception as e:
            print(e)
            raise Error(data={'details': f'JSON-RPC server error: {e}', 'status_code': 505})


async def run_selected_template(in_file: InputTemplateModel = None, background: bool = False) -> ProcessOutputModel:
    if in_file:
        if not in_file.file_content:
            local_file = in_file.file_name
            if await check_file(f'InputTemplates/{local_file}', 401):
                with open(f'InputTemplates/{local_file}', 'r') as input_file:
                    in_file.file_content = input_file.read()
        in_file.modify_params()
        with open('input.txt', 'w') as output_file:
            output_file.write(in_file.file_content)
        
    return await run_pioner_exe(background=background)


def get_template_files() -> List[str]:
    file_path = f'InputTemplates'
    onlyfiles = [f for f in listdir(file_path) if isfile(join(file_path, f))]
    return onlyfiles


@api_v1.method(errors=[Error])
async def save_input_template(in_params: InputTemplateModel) -> bool:
    print(f'/save_input_template/ route called')
    file_path = f'InputTemplates/{in_params.file_name}'
    result = {}
    try:
        with open(file_path, 'w') as file:
            file.write(in_params.file_content)
        result['result'] = True
    except Exception as e:
        print(e)
        raise Error(data={'details': f'JSON-RPC server error: {e}', 'status_code': 508})
    return True


@api_v1.method(errors=[Error])
async def get_template_list() -> List[InputTemplateModel]:
    print(f'/get_template_list/ route called')
    result = []
    files = get_template_files()
    for file in files:
        result.append(InputTemplateModel(file_name=file))
    return result


@api_v1.method(errors=[Error])
async def run_pioner(in_params: InputTemplateModel = None) -> ProcessOutputModel:
    print(f'/run_pioneer/ route called')
    return await run_selected_template(in_params)


@api_v1.method(errors=[Error])
async def run_pioner_bg(in_params: InputTemplateModel = None) -> ProcessOutputModel:
    print(f'/run_pioner_bg/ route called')
    return await run_selected_template(in_params, background=True)


@api_v1.method(errors=[Error])
async def get_bg_process_results() -> ProcessOutputModel:
    print(f'/get_bg_process_results/ route called')
    return await get_process_results()


@api_v1.method(errors=[Error])
async def clear_bg_process_results() -> ProcessOutputModel:
    print(f'/clear_bg_process_results/ route called')
    global PROCESS
    PROCESS = None
    return {'status': 'cleared'}


@api_v1.method(errors=[Error])
async def get_content_by_name(in_params: InputTemplateModel) -> InputTemplateModel:
    print(f'/get_content_by_name/ route called')
    if await check_file(f'InputTemplates/{in_params.file_name}', 401):
        try:
            with open(f'InputTemplates/{in_params.file_name}', 'r') as file:
                content = file.read()
        except Exception as e:
            print(e)
            raise Error(data={'details': f'JSON-RPC get_content_by_name error: {e}', 'status_code': 509})
    return InputTemplateModel(file_name=in_params.file_name, file_content=content)


app.bind_entrypoint(api_v1)

if __name__ == '__main__':

    uvicorn.run('JSON_RPC_Server:app', host=RPC_HOST, port=8001, access_log=True, reload=True)