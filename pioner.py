import os
import json
import requests

from PydanticModels import *
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)
RPC_HOST = os.getenv('RPC_HOST')


def call_rpc(method: str, rpc_params: BaseModel):
    url = f'http://{RPC_HOST}:8000/api/v1/jsonrpc'
    headers = {'content-type': 'application/json'}

    loc_json_rpc = {
        'jsonrpc': '2.0',
        'id': '0',
        'method': method,
        'params': {}
    }

    if (rpc_params is not None):
        loc_json_rpc['params'] = {'in_params': rpc_params.dict()}
    try:
        response = requests.post(url, data=json.dumps(loc_json_rpc), headers=headers, timeout=1.0)
    except Exception as err:
        return {'Exception': err}

    if response.status_code == 200:
        response = response.json()
        if 'result' in response:
            return response['result']
        else:
            return {'error': response['error']}
    else:
        return {'error': response['error']}


class mPioner:
    def __init__(self, name: str = 'big_input.txt'):
        self.set_file(name)

    def set_file(self, name: str):
        self.loc_file = InputTemplateModel(file_name=name)
        self.loc_file = call_rpc('get_content_rpc', self.loc_file)

    def print_all_files(self):
        files = call_rpc('get_file_list', None)
        for it in files:
            print(it['file_name'])

    def print_file(self, outfile):
        print(self.loc_file, file=outfile)

    def modify_file(self, in_N):
        self.loc_file = InputTemplateModel(file_name=self.loc_file['file_name'], N=in_N)
        self.loc_file = call_rpc('modify_file_rpc', self.loc_file)

    def run_solver(self) -> ProcessOutputModel:
        result = call_rpc('run_rpc_background', None)
        print(result)

if __name__ == '__main__':
    with open('output.txt', 'w') as out:
        loc_obj = mPioner()
        # loc_obj.print_file(out)
        loc_obj.set_file('bochkarev_template.txt')
        loc_obj.modify_file(f'{f"{-512.2:.3f}":>9}')
        # loc_obj.print_file(out)
        # loc_obj.modify_file(200)
        loc_obj.print_file(out)
        loc_obj.run_solver()

