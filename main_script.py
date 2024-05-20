import os
import numpy as np
import json
import time
import requests

from PydanticModels import *
from scipy.optimize import minimize
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


SLEEP_TIME = 1
MAX_RUNNING_TIME = 60
RPC_HOST = os.getenv('RPC_HOST')
TARGET_DIAPLACEMENT = 0.1
INITIAL_STRESS = -573.2


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


def get_target_displacement(result: dict, target_node_id: int = 33):
	displacements = result['displacements']
	last_displacements = displacements[max(
		result['displacements'],
		key=lambda x: int(x.split('.')[1])
	)]
	for node_data in last_displacements:
		if node_data['node'] == [target_node_id]:
			return node_data['v'][0]


def background_calc(stress_value: float, sleep_time: int = SLEEP_TIME, max_running_time: int = MAX_RUNNING_TIME):
	print(f'Calculation for stress = {stress_value} started')
	t0 = time.time()

	process_status = call_rpc(
		'run_pioner_bg', 
		InputTemplateModel(
			file_name='sample_template.txt', 
			repl_keys={'key1': 'N'},
			N = format_value(stress_value), 
		)
	)['status']
	print(f'  {process_status} – {round(time.time() - t0, 2)} s.')

	while True:
		if time.time() - t0 > max_running_time:
			print('  Process timeout')
			break
		time.sleep(sleep_time)
		result = call_rpc('get_bg_process_results')
		process_status = result['status']
		print(f'  {process_status} – {round(time.time() - t0, 2)} s.')
		if process_status == 'finished':
			break
	call_rpc('clear_bg_process_results')

	diplacement_value = get_target_displacement(result, target_node_id=4)
	print(f'Calculation for stress = {stress_value} finished with displacement = {round(diplacement_value, 3)}')
	
	with open('culculations_cache.txt', 'a') as f:
		f.write(f'{stress_value} {diplacement_value}\n')

	return diplacement_value

def gradient_descent(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * error
    return current_stress


def gradient_descent_v2(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * error * 0.9  # Slightly different learning rate adjustment
    return current_stress


def adam_optimizer(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100, beta1=0.9, beta2=0.999, epsilon=1e-8):
    current_stress = initial_stress
    m, v = 0, 0
    for t in range(1, max_iterations + 1):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        g = error
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * (g ** 2)
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        current_stress -= learning_rate * m_hat / (np.sqrt(v_hat) + epsilon)
    return current_stress


def nelder_mead(target, initial_stress, tolerance=1e-5, max_iterations=100):
    def objective(stress):
        return abs(background_calc(stress) - target)

    result = minimize(objective, initial_stress, method='Nelder-Mead', options={'xatol': tolerance, 'maxiter': max_iterations})
    return result.x[0]


def simple_iteration(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * np.sign(error)
    return current_stress


if __name__ == '__main__':
    optimal_stress_gd1 = gradient_descent(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_gd2 = gradient_descent_v2(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_adam = adam_optimizer(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_nm = nelder_mead(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_si = simple_iteration(TARGET_DIAPLACEMENT, INITIAL_STRESS)
	
    print(f'Optimal stress (Gradient Descent 1): {optimal_stress_gd1}')
    print(f'Optimal stress (Gradient Descent 2): {optimal_stress_gd2}')
    print(f'Optimal stress (Adam): {optimal_stress_adam}')
    print(f'Optimal stress (Nelder-Mead): {optimal_stress_nm}')
    print(f'Optimal stress (Simple Iteration): {optimal_stress_si}')
