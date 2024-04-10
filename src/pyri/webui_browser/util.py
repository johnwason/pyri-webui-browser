from copy import copy
import traceback
from pyodide.ffi import to_js
import js

def device_status_name(devices_states, local_device_name):
    try:
        if devices_states.devices_states[local_device_name].ready:
            status = "ready"
        elif devices_states.devices_states[local_device_name].error:
            status = "error"
        elif devices_states.devices_states[local_device_name].connected:
            status = "connected"
        else:
            status = "disconnected"
        return status
    except:
        return "internal_error"

def device_state_flags(devices_states, local_name):
    if devices_states is None:
        return ""
    
    state_flags = []
    try:
        typed_device_states = devices_states.devices_states[local_name].state
    except KeyError:
        traceback.print_exc()
        return ""

    if typed_device_states is None:
        return ""

    for v in typed_device_states:
        f = v.display_flags
        if f is not None:
            state_flags.extend(f)

    return " ".join(state_flags)

def get_devices_with_type(core, device_types):
    if isinstance(device_types,str):
        device_types = [device_types]
    robot_device_names = []

    for local_name in core.active_device_names:
        
        try:
            device_infos = core.device_infos[local_name]
        except KeyError:
            continue
        try:                
            root_object_type = device_infos["device_info"].root_object_type
            if root_object_type in device_types:
                robot_device_names.append(local_name)
                continue
            root_object_implements = device_infos["device_info"].root_object_implements
            if not set(device_types).isdisjoint(set(root_object_implements)):
                robot_device_names.append(local_name)
                continue           
        except AttributeError:
            traceback.print_exc()
            continue
        except KeyError:
            traceback.print_exc()
            continue

    return robot_device_names

def device_names_to_dropdown_options(names):
    return [{"value": n, "text": n} for n in names]
    
def to_js2(val):
    return to_js(val,dict_converter=js.Object.fromEntries)
