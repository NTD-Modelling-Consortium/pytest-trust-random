import dis
import io
from contextlib import redirect_stdout
from inspect import signature
from typing import Callable, Dict, Generic, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, create_model

from .base_models import (
    BaseOutputData,
    BaseSettingsModel,
    BaseTestDimension,
    PytestConfig,
)


def snake_to_camel_case(string: str) -> str:
    string_elems = string.split("_")
    new_elems = [i.title() for i in string_elems]
    return "".join(new_elems)


def get_func_info(func) -> str:
    with redirect_stdout(io.StringIO()) as f:
        dis.dis(func)
    return f.getvalue()


FuncReturn = TypeVar(
    "FuncReturn",
    bound=BaseModel,
)


class SetupFuncBenchmarker(Generic[FuncReturn]):
    parameters: Dict[str, type]
    func: Callable[..., FuncReturn]
    return_type: FuncReturn
    func_name: str
    camel_name: str
    pytest_config: PytestConfig
    _settings_model: Optional[Type[BaseSettingsModel]]
    _output_data: Optional[Type[BaseOutputData]]

    def __init__(
        self, func: Callable[..., FuncReturn], est_base_time: float = 0.015
    ) -> None:
        sig = signature(func)
        return_type: FuncReturn = sig.return_annotation
        if not issubclass(
            return_type, BaseModel  # type:ignore BaseModel incompatible with *?
        ):
            raise ValueError("Function return must inherit from BaseModel")
        parameters = {v.name: v.annotation for _, v in sig.parameters.items()}
        self.parameters = parameters
        self.func = func
        self.return_type = return_type
        self.func_name = func.__name__
        self.camel_name = snake_to_camel_case(self.func_name)

        self._settings_model = None
        self._output_data = None
        self._test_model = None
        self.est_base_time = est_base_time
        self.func_info = (
            get_func_info(self.func)
            + str(self.parameters)
            + str(self.return_type.schema())
        )

    def __str__(self) -> str:
        return self.func_info.replace("\n", "")

    def _generate_settings_model(self) -> Type[BaseSettingsModel]:
        attributes: Dict[str, Tuple[type, ellipsis]] = {
            k: (BaseTestDimension[t], ...)  # type:ignore
            for k, t in self.parameters.items()
        }
        return create_model(
            self.camel_name + "Settings", **attributes, __base__=BaseSettingsModel
        )

    @property
    def settings_model(self) -> Type[BaseSettingsModel]:
        if self._settings_model is None:
            self._settings_model = self._generate_settings_model()
        return self._settings_model

    def generate_settings_instance(self) -> BaseSettingsModel:
        model = self.settings_model
        attr_dict = {}
        for k, t in self.parameters.items():
            print(f"Attributes for {k}:")
            while True:
                constraints = input(
                    f"Enter (minimum: {str(t.__name__)}, maximum: {str(t.__name__)}, steps: int): "
                )
                items = constraints.split(",")
                if len(items) == 3:
                    try:
                        minimum = t(items[0])
                        maximum = t(items[1])
                        steps = int(items[2])
                        if maximum < minimum:
                            print("max less than min")
                            continue
                        break
                    except ValueError:
                        print("invalid type")
                        continue
                else:
                    print("incorrect number of args")
                    continue
            attr_dict[k] = BaseTestDimension[t](  # type:ignore
                minimum=minimum, maximum=maximum, steps=steps
            )
        while True:
            try:
                max_product_string = input("max_product: float: ")
                max_product = float(max_product_string)
                break
            except ValueError:
                print("invalid type")
                continue
        attr_dict["max_product"] = max_product

        while True:
            try:
                benchmark_iters_string = input("benchmark_iters: int: ")
                benchmark_iters = int(benchmark_iters_string)
                break
            except ValueError:
                print("invalid type")
                continue
        attr_dict["benchmark_iters"] = benchmark_iters

        settings = model.parse_obj(attr_dict)
        return settings

    def _generate_output_model(self) -> Type[BaseOutputData]:
        attributes: Dict[str, Tuple[type, ellipsis]] = {
            k: (t, ...) for k, t in self.parameters.items()
        }
        return create_model(
            self.camel_name + "Settings", **attributes, __base__=BaseOutputData
        )

    @property
    def output_model(self) -> Type[BaseOutputData]:
        if self._output_data is None:
            self._output_data = self._generate_output_model()
        return self._output_data
