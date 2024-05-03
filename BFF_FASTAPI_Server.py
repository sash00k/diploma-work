from fastapi import FastAPI, Request
from random import randint
from bokeh.layouts import column, row
from bokeh.models.widgets import DataTable, TableColumn, Select
from bokeh.models import ColumnDataSource, CustomJS, Div, TextInput, Button
from bokeh.models.widgets import PreText, FileInput
from bokeh.models import CustomJS, Div
from bokeh.embed import components, json_item
from fastapi.responses import HTMLResponse
from pybase64 import b64decode
from PydanticModels import *
from dotenv import load_dotenv

import json
import os
import io
import uvicorn
import requests

load_dotenv()

app = FastAPI()

lhost = os.getenv('HOST_IP')

file_input = FileInput(name='file_input_bokeh')
button_run = Button(label='Run', button_type='success')
button_modify = Button(label='modify', button_type='success')
select_out = Select(title='Files:', value='', options=[], name='select_file_bokeh')

text_input_key = TextInput(value='', title='key:')
text_input_val = TextInput(value='', title='N:')

g_loc_file = None
g_loc_file_run = None

template = lambda gscripts, gdivs: str('''
    <!DOCTYPE html>
    <html lang='en'>
        <head>
            <script type='text/javascript' src='https://cdn.bokeh.org/bokeh/release/bokeh-3.4.0.min.js'></script>
            <script type='text/javascript' src='https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.4.0.min.js'></script>
            <script type='text/javascript' src='https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.4.0.min.js'></script>
            <script>
                var curFileName = ''
                var cur_key = ''
                var cur_val = ''
            </script>
            ''' + str(gscripts) + '''
        </head>
        <body>
            ''' + str(gdivs) + '''
            <div id='myplot'></div><p>
        </body>
    </html>
''')


bokeh_print_template = '''
    const printFile = async () => {
        const a = await put_file();
        var div = document.getElementById('myplot');
            while(div.firstChild){
                div.removeChild(div.firstChild);
            }
        Bokeh.embed.embed_item(a)
};
    printFile()
'''

callback = CustomJS(args=dict(file_input=file_input), code='''
    const val1 = file_input.filename;
    const val2 = file_input.value;

    async function put_file(){
     return await fetch('/post_content', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 'fileName': val1, 'fileContent': val2, })
        }).then((response) => response.json())
    }
''' + bokeh_print_template + 'window.location.reload();')

callback_button_run = CustomJS(code='''
    async function put_file(){
        return await fetch('/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then((response) => response.json())
    }
''' + bokeh_print_template)


callback_button_modify = CustomJS(code='''
    async function put_file(){
    console.log(cur_key, cur_val);
    
                var obj = {};
                obj[3] = 'N';
                
     return await fetch('/modify_file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ 'fileName': curFileName,  'N' :Number(cur_val), 'repl_keys' : obj })
    }).then((response) => response.json())

    }
''' + bokeh_print_template)


callback_select = CustomJS(code='''
    curFileName = this.value;
    console.log('select: value=' + this.value + ' = ', curFileName)
    async function put_file(){
     return await fetch('/get_content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 'fileName': curFileName })
        }).then((response) => response.json())
    }
''' + bokeh_print_template)

callback_text_key = CustomJS(code='cur_key = this.value')
callback_text_val = CustomJS(code='cur_val = this.value')

def decode_data(in_dat):
    decoded = b64decode(in_dat)
    f = io.BytesIO(decoded)
    text_obj = io.TextIOWrapper(f, encoding='utf-8')
    res_out = text_obj.read()
    return res_out


def call_rpc(method: str, rpc_params: BaseModel):

    url = f'http://{lhost}:8001/api/v1/jsonrpc'
    headers = {'content-type': 'application/json'}

    loc_json_rpc = {'jsonrpc': '2.0',
                    'id': '0',
                    'method': method,
                    'params': {}
                    }
    if (rpc_params is not None):
        loc_json_rpc['params'] = {'in_params' : rpc_params.dict() }
    try:
        response = requests.post(url, data=json.dumps(loc_json_rpc), headers=headers, timeout=0.5)
    except Exception as err:
        return {'error': 'error connection'}

    if response.status_code == 200:
        response = response.json()
        if 'result' in response:
            return response['result']
        else:
            return {'error': response['error']}
    else:
        return {'error': response['error']}


def merge(dicts):
    return {
        k: [d[k] for d in dicts]
        for k in dicts[0].keys()
    }

def update_template_list()->List[str]:
    ret=[]
    res = call_rpc('get_template_list', None)
    print(res)
    if ('error' not in res):
        for it in res:
            ret.append(it['fileName'])
    return ret

def build_select_ui():
    files_name = update_template_list()
    select_out.options = files_name

@app.get('/run_rpc')
async def run_rpc() -> ProcessOutputModel:
    global g_loc_file_run
    print('run', g_loc_file_run)
    if (g_loc_file_run is None):
        error_txt = PreText(text=str('current file is not exist'), width=500, height=100)  # <pre> file_content</pre>
        return json.dumps(json_item(error_txt, 'myplot'))
    ret = call_rpc('run_pioner', g_loc_file_run)
    if ('error' in ret):
        error = PreText(text=str(ret['error']), width=500, height=100)  # <pre> file_content</pre>
        return {'error': error}
    displacements = ret['displacements']
    stress = ret['stress']
    return ret

@app.get('/run_rpc', response_class=HTMLResponse)
async def run_rpc()->ProcessOutputModel:
    global g_loc_file_run
    print('run', g_loc_file_run)
    if (g_loc_file_run is None):
        error_txt = PreText(text=str('current file is not exist'), width=500, height=100)  # <pre> file_content</pre>
        return json.dumps(json_item(error_txt, 'myplot'))
    ret = call_rpc('run_pioner', g_loc_file_run)
    if ('error' in ret):
        error = PreText(text=str(ret['error']), width=500, height=100)  # <pre> file_content</pre>
        return json.dumps(json_item(error, 'myplot'))
    displacements = ret['displacements']
    stress = ret['stress']
    return ret

@app.post('/run', response_class=HTMLResponse)
async def run():
    global g_loc_file_run
    print('run', g_loc_file_run)
    if (g_loc_file_run is None):
        error_txt = PreText(text=str('current file is not exist'), width=500, height=100)  # <pre> file_content</pre>
        return json.dumps(json_item(error_txt, 'myplot'))
    ret = call_rpc('run_pioner', g_loc_file_run)
    if ('error' in ret):
        error = PreText(text=str(ret['error']), width=500, height=100)  # <pre> file_content</pre>
        return json.dumps(json_item(error, 'myplot'))
    displacements = ret['displacements']
    stress = ret['stress']

    displacements_pre = PreText(text=str(displacements), width=500, height=100)  # <pre> file_content</pre>
    stress_pre = PreText(text=str(stress), width=500, height=100)  # <pre> file_content</pre>

    data_tables = []
    for it in ret['displacements'].keys():
        datas_loc = merge(displacements[it])
        columns = [
            TableColumn(field='node', title='Node'),
            TableColumn(field='x', title='x'),
            TableColumn(field='y', title='y'),
            TableColumn(field='u', title='u'),
            TableColumn(field='v', title='v')
        ]
        source = ColumnDataSource(datas_loc)
        data_table = DataTable(source=source, columns=columns, width=400, height=280, editable=True)  # <tabledata>

        mdiv = Div(text=str(it),
                  width=200, height=100)
        data_tables.append(mdiv)
        data_tables.append(data_table)

    return json.dumps(json_item(column(displacements_pre, stress_pre, *data_tables), 'myplot'))


@app.post('/modify_file', response_class=HTMLResponse)
async def modify_file(in_file: InputTemplateModel):
    global g_loc_file, g_loc_file_run

    g_loc_file_run = g_loc_file.model_copy()
    g_loc_file_run.N = in_file.N
    g_loc_file_run.repl_keys = in_file.repl_keys
    g_loc_file_run.modify_params()

    ret_text = PreText(text=str(g_loc_file_run.fileContent), width=500, height=100)  # <pre> file_content</pre>

    return json.dumps(json_item(ret_text, 'myplot'))

@app.post('/get_content', response_class=HTMLResponse)
async def get_content(in_file: InputTemplateModel):

    global g_loc_file,g_loc_file_run
    ret = call_rpc('get_content_by_name', in_file)
    in_file.fileContent = ret['fileContent']
    g_loc_file = in_file.model_copy()
    g_loc_file_run = in_file.model_copy()


    ret_text = PreText(text=g_loc_file.fileContent, width=500, height=100)  # <pre> file_content</pre>
    return json.dumps(json_item(ret_text, 'myplot'))


@app.post('/post_content', response_class=HTMLResponse)
async def post_content(in_file: InputTemplateModel):
    file_content = decode_data(in_file.fileContent)
    in_file.fileContent = file_content

    ret = call_rpc('save_input_template', in_file)
    ncontent = PreText(text=str(ret), width=500, height=100)  # <pre> file_content</pre>
    return json.dumps(json_item( ncontent, 'myplot'))


@app.get('/', response_class=HTMLResponse)
async def read_root(request: Request, inline: bool = True):
    global file_input
    global button_run
    global button_modify
    global text_input_key
    global text_input_val
    global select_out

    file_input.js_on_change('filename', callback)
    button_run.js_on_event('button_click', callback_button_run)
    select_out.js_on_change('value', callback_select)
    button_modify.js_on_event('button_click', callback_button_modify)

    text_input_key.js_on_change('value', callback_text_key)
    text_input_val.js_on_change('value', callback_text_val)

    build_select_ui()

    script3, div3 = components(button_modify)
    script4, div4 = components(text_input_key)
    script5, div5 = components(text_input_val)

    script1, div1 = components(select_out)
    script0, div0 = components(button_run)
    script, div = components(file_input)

    return HTMLResponse(template(script+script1+script0+script3+script4+script5, div+div1+div0+div3+div4+div5))

if __name__ == '__main__':
    uvicorn.run(app, host=lhost, port=8000, access_log=True)
