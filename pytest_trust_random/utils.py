Flat = float | int
InnerDictType = Flat | dict[str, "InnerDictType"]
DictType = dict[str, InnerDictType]
FlatDict = dict[str, Flat]


def flatten_dict(input_dict: DictType, prefix: str = "") -> FlatDict:
    if prefix == "":
        effective_prefix = ""
    else:
        effective_prefix = prefix + "_"
    output_dict = {}
    for k, v in input_dict.items():
        if isinstance(v, dict):
            new_dict = flatten_dict(v, prefix=effective_prefix + k)
        else:
            new_dict = {effective_prefix + k: v}
        output_dict.update(new_dict)
    return output_dict


def read_value_from_input(prompt: str, T: type):
    """Read a single value of type `T` from user's input until correct.

    Args:
        prompt (str): prompt
        T (type): value type
    """
    while True:
        try:
            s = input(f"{prompt} ({T.__name__}): ")
            return T(s)
        except ValueError:
            print("[!] Invalid type")
