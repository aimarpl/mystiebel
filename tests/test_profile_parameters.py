"""Tests for product-specific parameter profiles."""

import importlib.util
from pathlib import Path


_MODULE_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "mystiebel"
    / "parameters.py"
)
_SPEC = importlib.util.spec_from_file_location("mystiebel_parameters", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_PARAMETERS_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARAMETERS_MODULE)
load_parameters = _PARAMETERS_MODULE.load_parameters


def test_loads_central_ventilation_profile_parameters():
    loaded = load_parameters("en", profile_type="central_ventilation_wifi")

    parameters = loaded["parameters"]
    assert set(parameters) == {
        2553,
        2554,
        2555,
        2556,
        2557,
        2558,
        2559,
        2560,
        2561,
        2562,
        2563,
        2564,
        2565,
        65553,
        65554,
        65555,
        65556,
        65557,
        65558,
        65593,
        65594,
    }
    assert parameters[2553]["display_name"] == "Extract air humidity"
    assert parameters[2553]["unit"] == "humidity"
    assert parameters[2554]["display_name"] == "Extract air temperature"
    assert parameters[2554]["unit"] == "degree_celsius"
    assert parameters[2555]["choices"] == {"0": "Closed", "1": "Open"}
    assert parameters[2564]["choices"]["4"] == "Time program"
    assert parameters[2565]["access"] == ["read"]
    assert parameters[2553]["enabled_default"] is True
    assert parameters[2556]["enabled_default"] is False


def test_unknown_profile_falls_back_to_default_parameters():
    loaded = load_parameters("en", profile_type="unknown_profile")

    assert 2378 in loaded["parameters"]
    assert 2553 not in loaded["parameters"]


def test_extracts_profile_type_from_installation_data():
    extractor = getattr(_PARAMETERS_MODULE, "profile_type_from_installation", None)
    assert extractor is not None
    assert (
        extractor({"profile": {"typeName": "central_ventilation_wifi"}})
        == "central_ventilation_wifi"
    )
    assert (
        extractor({"profile": {"type_name": "central_ventilation_wifi"}})
        == "central_ventilation_wifi"
    )
    assert extractor({"profile": {}}) is None
    assert extractor({}) is None


def test_loads_parameters_for_installation_profile():
    loader = getattr(_PARAMETERS_MODULE, "load_parameters_for_installation", None)
    assert loader is not None

    loaded = loader(
        {"profile": {"typeName": "central_ventilation_wifi"}},
        language="pl",
    )

    assert 2553 in loaded["parameters"]
    assert loaded["parameters"][2553]["display_name"] == (
        "Wilgotność powietrza wywiewanego"
    )
    assert 2378 not in loaded["parameters"]


def test_selects_only_supported_auxiliary_sensors():
    selector = getattr(_PARAMETERS_MODULE, "supported_auxiliary_sensors", None)
    assert selector is not None
    fields = load_parameters(
        "en", profile_type="central_ventilation_wifi"
    )["all_fields"]

    assert selector(fields) == {"product_pid", "gateway_pid"}
    assert selector([]) == set()


def test_central_ventilation_loader_enforces_read_only(monkeypatch):
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "central_ventilation_read_write.json"
    )
    monkeypatch.setitem(
        _PARAMETERS_MODULE.PROFILE_PARAMETER_FILES,
        "central_ventilation_wifi",
        profile_path,
    )

    loaded = load_parameters("en", profile_type="central_ventilation_wifi")

    assert loaded["parameters"][1]["access"] == ["read"]
