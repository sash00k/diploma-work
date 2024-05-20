import fastapi_jsonrpc as jsonrpc

from typing import List, Dict, Optional, Union
from fastapi import Body
from pydantic import BaseModel
from typing import List


class Error(jsonrpc.BaseError):
    CODE = 5000
    MESSAGE = 'Server Error'

    class DataModel(BaseModel):
        details: str
        status_code: int


class BaseModelWithFileParsing(BaseModel):
    @classmethod
    def parse_file(cls, file_path: str, **kwargs) -> List['BaseModelWithFileParsing']:

        data = []

        try:
            with open(file_path, 'r') as file:
                next(file) 

                for line in file:
                    values = [[float(val)] for val in line.split()]
                    model_instance = cls(**dict(zip(cls.__annotations__, values)))
                    data.append(model_instance)

            return data

        except Exception as error:
            raise Error(data={'details': f"JSON-RPC server error while parsing '{file_path}' file:\n{error}", 'status_code': 503})


class Displacements(BaseModelWithFileParsing):
    node: List[int]
    x: List[float]
    y: List[float]
    u: List[float]
    v: List[float]


class Stress(BaseModelWithFileParsing):
    element: List[int]
    int_point: List[int]
    x: List[float]
    y: List[float]
    sigma_xx: List[float]
    sigma_yy: List[float]
    sigma_xy: List[float]
    sigma_zz: List[float]
    max_stress: List[float]
    interm_stress: List[float]
    min_stress: List[float]
    time: List[float]


class Failure(BaseModelWithFileParsing):
    element: int
    int_point: int
    x: float
    y: float
    ind_failure: int
    maximal_principal_stress_direction: float


class ProcessOutputModel(BaseModel):
    status: str
    displacements: Dict[str, List[Displacements]] = None
    stress: Dict[str, List[Stress]] = None
    stress_rotated: Union[Dict[str, List[Stress]], None] = None
    failure: Union[Dict[str, List[Failure]], None] = None


class InputTemplateModel(BaseModel):
    file_name: str = Body(..., examples=['new_template.txt'])
    file_content: Optional[str] = None
    N: Optional[Union[int, str, float]] = None 
    repl_keys: Optional[Dict[str,str]] = None

    def modify_params(self):
        if self.repl_keys and self.file_content:
            for key, attr_name in self.repl_keys.items():
                if key:
                    value = getattr(self, attr_name, None)
                    if value is not None:
                        self.file_content = self.file_content.replace(key, str(value)) 
