import os
import json
import time
import requests

from PydanticModels import *
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


SLEEP_TIME = 1
MAX_RUNNING_TIME = 20 * 60
RPC_HOST = os.getenv('RPC_HOST')
TARGET_DIAPLACEMENT = 0.1


def format_value(float_value: float, required_length: int = 9):
	return f'{f"{float_value:.3f}":>{required_length}}'


def call_rpc(method: str, rpc_params: BaseModel = None):
	url = f'http://{RPC_HOST}:8001/api/v1/jsonrpc'
	headers = {'content-type': 'application/json'}

	loc_json_rpc = {
		'jsonrpc': '2.0',
		'id': '0',
		'method': method,
		'params': {}
	}
	if rpc_params is not None:
		loc_json_rpc['params'] = {'in_params' : rpc_params.model_dump()}
	try:
		response = requests.post(url, data=json.dumps(loc_json_rpc), headers=headers)
	except Exception as err:
		return {'error': err}

	if response.status_code == 200:
		response = response.json()
		if 'result' in response:
			return response['result']
		else:
			return {'error': response['error']}
	else:
		return {'error': response['error']}


def get_target_displacement(result: dict, target_node_id: int = 1):
	displacements = result['displacements']
	last_displacements = displacements[max(
		result['displacements'],
		key=lambda x: int(x.split('.')[1])
	)]
	for node_data in last_displacements:
		if node_data['node'] == [target_node_id]:
			return node_data['v'][0]


def background_calc(stress_value: float, input_postfix: str = 'defalut', sleep_time: int = SLEEP_TIME, max_running_time: int = MAX_RUNNING_TIME):
	print(f'\nCalculation for stress = {stress_value} started, file: bochkarev_{input_postfix}.txt')
	t0 = time.time()

	result = call_rpc(
		'run_pioner_bg', 
		InputTemplateModel(
			file_name=f'bochkarev_{input_postfix}.txt', 
			repl_keys={'key1': 'N'},
			N = format_value(stress_value), 
		)
	)
	process_status = result['status']
	print(f'  {process_status} – {round(time.time() - t0, 2)} s.')

	while True:
		if time.time() - t0 > max_running_time:
			print('  Process timeout')
			break
		time.sleep(sleep_time)
		taken_time = time.time() - t0
		result = call_rpc('get_bg_process_results')
		process_status = result.get('status', 'error')
		print(f'  {process_status} – {round(time.time() - t0, 2)} s.')
		if process_status in ('finished', 'error'):
			break
	call_rpc('clear_bg_process_results')

	if process_status == 'finished':
		diplacement_value = get_target_displacement(result, target_node_id=4)
		print(f'Calculation for stress = {stress_value} finished with displacement = {round(diplacement_value, 3)}')
	else:
		diplacement_value = None
		print(f'Calculation for stress = {stress_value} finished with error')
	
	with open(f'culculations_cache/{input_postfix}.txt', 'a') as f:
		f.write(f'{stress_value}\t{diplacement_value}\t{taken_time}\n')

	return diplacement_value


if __name__ == '__main__':
	for stress in range(0, -1200, -20):
		background_calc(stress, input_postfix='default')