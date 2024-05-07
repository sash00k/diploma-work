import os
import json
import requests

from PydanticModels import *
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)
rpc_host = os.getenv('RPC_HOST')


def call_rpc(method: str, rpc_params: BaseModel):
    url = f'http://{rpc_host}:8000/api/v1/jsonrpc'
    headers = {'content-type': 'application/json'}

    loc_json_rpc = {'jsonrpc': '2.0',
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
            return {'error OK': response['error']}
    else:
        return {'error': response['error']}



class mPioner:
    def __init__(self):
        self.getFile('big_input.txt')

    def getFile(self, name: str):
        self.loc_file = InputTemplateModel(fileName=name)
        self.loc_file = call_rpc('get_content_rpc', self.loc_file)

    def print_all_files(self):
        files = call_rpc('get_file_list', None)
        for it in files:
            print(it['fileName'])

    def print_file(self):
        print(self.loc_file)

    def modify_file(self, in_N):
        self.loc_file = InputTemplateModel(fileName=self.loc_file['fileName'], N=in_N)
        self.loc_file = call_rpc('modify_file_rpc', self.loc_file)


    def mRun(self) -> ProcessOutputModel:
        ret = call_rpc('run_rpc', None)
        print(ret)
        return ret


loc_obj = mPioner()
loc_obj.print_all_files()
loc_obj.print_file()
loc_obj.getFile('big_input_3.txt')
loc_obj.modify_file(10)
loc_obj.print_file()
loc_obj.modify_file(200)
loc_obj.print_file()

