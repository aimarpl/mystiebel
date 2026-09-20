"""Parameter loading and translation utilities for Stiebel Eltron integration."""

import json
import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
data_path = Path(__file__).resolve().parent / "data"
json_path = data_path / "parameters.json"
PROFILE_PARAMETER_FILES = {
    "central_ventilation_wifi": data_path / "central_ventilation_wifi.json",
}
READ_ONLY_PROFILE_TYPES = {"central_ventilation_wifi"}
PROFILE_TYPES_BY_GUID = {
    "d7a4be01-4f17-4e34-9033-888f70dbac70": "central_ventilation_wifi",
}
CENTRAL_VENTILATION_PROFILE_NAMES = {"lwzx80", "lwxx80"}
AUXILIARY_SENSOR_REGISTERS = {
    "controller_sw_version": {65535, 65536, 65537, 65560},
    "wifi_adapter_sw_version": {65523, 65524, 65525, 65559},
    "product_pid": {65556, 65557, 65558, 65594},
    "gateway_pid": {65553, 65554, 65555, 65593},
    "runtime_compressor": {2449, 555},
    "runtime_heating": {2450, 558},
    "available_baths": {2395},
    "available_shower_time": {2395},
}


def supported_auxiliary_sensors(fields):
    """Return auxiliary sensors whose source registers exist in the profile."""
    available_fields = set(fields)
    return {
        name
        for name, required_fields in AUXILIARY_SENSOR_REGISTERS.items()
        if required_fields <= available_fields
    }


def profile_type_from_installation(device_data):
    """Return the profile type used by the MyStiebel installation."""
    profile = device_data.get("profile", {}) if device_data else {}
    profile_type = profile.get("typeName") or profile.get("type_name")
    if profile_type:
        return profile_type

    profile_guid = str(profile.get("guid", "")).lower()
    if profile_guid in PROFILE_TYPES_BY_GUID:
        return PROFILE_TYPES_BY_GUID[profile_guid]

    profile_name = str(profile.get("name", "")).strip().casefold()
    if profile_name in CENTRAL_VENTILATION_PROFILE_NAMES:
        return "central_ventilation_wifi"

    return None


def convert_value(value_str, scale_str):
    if value_str is None or scale_str is None:
        return None
    try:
        value_float = float(value_str)
        scale_int = int(scale_str)
        converted = value_float * (10**scale_int)
        if converted == int(converted):
            return int(converted)
        return converted
    except (ValueError, TypeError):
        return value_str


def load_parameters(language="en", json_file_path=None, profile_type=None):
    selected_path = (
        Path(json_file_path)
        if json_file_path is not None
        else PROFILE_PARAMETER_FILES.get(profile_type, json_path)
    )
    with selected_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    all_translations = {
        key: value.get(language, value.get("en", key))
        for key, value in data.get("texts", {}).items()
        if isinstance(value, dict)
    }
    choice_list_map = {}
    for cl in data.get("choice_lists", []):
        translated_choices = {
            str(choice["value"]): all_translations.get(choice["text"], choice["text"])
            for choice in cl["choices"]
        }
        choice_list_map[cl["id"]] = translated_choices

    parameter_to_group_map = {}
    user_friendly_fields = []

    def process_group(group):
        group_id = group.get("id")
        if group_id == "MY_STIEBEL":
            user_friendly_fields.extend(group.get("parameters", []))
        for param_number in group.get("parameters", []):
            parameter_to_group_map[param_number] = group_id
        for subgroup_number in group.get("subgroups", []):
            subgroup_data = next(
                (
                    g
                    for g in data.get("groups", [])
                    if g.get("number") == subgroup_number
                ),
                None,
            )
            if subgroup_data:
                process_group(subgroup_data)

    for group in data.get("groups", []):
        process_group(group)

    parameter_map = {}
    for param in data.get("parameters", []):
        param_number = param.get("number")
        name_key, scale_factor, choicelist_id = (
            param.get("name"),
            param.get("scale"),
            param.get("choicelist_id"),
        )
        translated_name = all_translations.get(name_key, name_key)
        access = list(
            dict.fromkeys(
                permission["access"]
                for permission in param.get("access_permissions", [])
            )
        )
        if profile_type in READ_ONLY_PROFILE_TYPES and access:
            access = ["read"]
        entry = {
            "id": param.get("id"),
            "name": name_key,
            "translated_name": translated_name,
            "display_name": translated_name,
            "data_type": param.get("data_type"),
            "unit": param.get("unit"),
            "scale": scale_factor,
            "access": access,
            "choicelist_id": choicelist_id,
            "choices": choice_list_map.get(choicelist_id, {}) if choicelist_id else {},
            "min": convert_value(param.get("min_value"), scale_factor),
            "max": convert_value(param.get("max_value"), scale_factor),
            "group_id": parameter_to_group_map.get(param_number),
            "enabled_default": bool(param.get("enabled_default", False)),
        }
        parameter_map[param_number] = entry

    alarm_map = {
        alarm.get("code"): all_translations.get(alarm.get("name"), alarm.get("name"))
        for alarm in data.get("alarms", [])
    }

    return {
        "parameters": parameter_map,
        "alarms": alarm_map,
        "user_fields": user_friendly_fields,
        "all_fields": list(parameter_map.keys()),
    }


def load_parameters_for_installation(device_data, language="en"):
    """Load the parameter profile matching a MyStiebel installation."""
    return load_parameters(
        language,
        profile_type=profile_type_from_installation(device_data),
    )
