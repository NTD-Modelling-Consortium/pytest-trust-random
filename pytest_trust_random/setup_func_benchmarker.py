import dis
import io
from inspect import signature
from typing import Callable, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, create_model

from pytest_trust_random.utils import read_value_from_input

from .base_models import (
    BaseOutputData,
    BaseSettingsModel,
    BaseTestDimension,
    TrustRandomConfig,
)
from .utils import read_value_from_input


def snake_to_camel_case(string: str) -> str:
    string_elems = string.split("_")
    new_elems = [i.title() for i in string_elems]
    return "".join(new_elems)


def get_func_info(func) -> str:
    with io.StringIO() as buffer:
        dis.dis(func, file=buffer)
        return buffer.getvalue()


FuncReturn = TypeVar("FuncReturn", bound=BaseModel)


class SetupFuncBenchmarker(Generic[FuncReturn]):
    parameters: dict[str, type]
    func: Callable[..., FuncReturn]
    return_type: FuncReturn
    func_name: str
    camel_name: str
    trust_random_config: TrustRandomConfig
    _settings_model: Optional[Type[BaseSettingsModel]]
    _output_data: Optional[Type[BaseOutputData]]

    def __init__(
        self, func: Callable[..., FuncReturn], est_base_time: float = 0.015
    ) -> None:
        # TODO: est_base_time is a bit useless, unless we come up with a way to actually estimate it.
        sig = signature(func)
        return_type: FuncReturn = sig.return_annotation
        assert issubclass(
            return_type, BaseModel  # type: ignore
        ), "Function return must inherit from BaseModel"
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
        attributes: dict[str, tuple[type, ellipsis]] = {
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
        def read_parameter_dimension(k: str, T: type):
            while True:
                constraints = input(
                    f"Enter attributes for `{k}` (minimum: {T.__name__}, maximum: {T.__name__}, steps: int): "
                )
                items = constraints.split(",")
                if len(items) == 3:
                    try:
                        return BaseTestDimension[T](  # type:ignore
                            minimum=T(items[0]),
                            maximum=T(items[1]),
                            steps=int(items[2]),
                        )
                    except ValueError:
                        print("[!] Invalid type or maximum is less than minimum")
                else:
                    print("[!] Incorrect number of args")

        attrs = {}
        for k, T in self.parameters.items():
            attrs[k] = read_parameter_dimension(k, T)

        if len(self.parameters) == 1:
            # If there's only one parameter, use its maximum value
            dimensions = next(iter(attrs.values()))
            max_product = dimensions.maximum
        else:
            max_product = read_value_from_input("max_product", float)
        attrs["max_product"] = max_product

        attrs["benchmark_iters"] = read_value_from_input("benchmark_iters", int)

        print()

        settings = self.settings_model.parse_obj(attrs)
        return settings

    def _generate_output_model(self) -> Type[BaseOutputData]:
        attributes: dict[str, tuple[type, ellipsis]] = {
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
