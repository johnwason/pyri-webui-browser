from typing import List, Dict, Callable, Any
import importlib_resources
import js
import traceback
from RobotRaconteurCompanion.Util.IdentifierUtil import IdentifierUtil
from RobotRaconteur.RobotRaconteurPythonUtil import SplitQualifiedName

from RobotRaconteur.Client import *
from .. import util
from ..util import to_js2

from ..pyri_vue import PyriVue, VueComponent, vue_register_component, vue_data, vue_method

import asyncio

@VueComponent
class PyriDevicesComponent(PyriVue):

    vue_template = importlib_resources.read_text(__package__,"devices_component.html")

    vue_components = {
        "BootstrapTable": js.window.BootstrapTable
    }

    active_device_names = vue_data(lambda: [])
    detected_devices = vue_data(lambda: [])
    selected_device_info = vue_data(lambda: [])
    device_list_columns = vue_data(lambda vue: 
        [
            {
                "field": "select",
                "checkbox": True
            },
            {
                "title": "Local Name",
                "field": "local_name"
            },
            {
                "title": "Device Name",
                "field": "device_name",
            },
            {
                "title": "Device Types",
                "field": "types"
            },
            {
                "title": "Status",
                "field": "status",
                "formatter": lambda value,row,index,field: f"<span class=\"{'device_status_text_' + value}\"></span>"
            },
            {
                "title": "State Flags",
                "field": "state_flags"
            },
            {
                "title": "Action",
                "field": "actions",
                "searchable": False,                  
                "formatter": lambda a,b,c,d: """<a class="device_list_info" title="Device Info" @click=""><i class="fas fa-2x fa-info-circle"></i></a>&nbsp;
                                                <a class="device_list_remove" title="Remove Device" @click="device_remove(local_name)"><i class="fas fa-2x fa-trash"></i></a>""",
                "events":
                {
                    "click .device_list_info": js.Function.new("vue_this", "return (function (e, value, row, d) { vue_this.device_info(row.local_name); })")(vue),
                    "click .device_list_remove": js.Function.new("vue_this", "return (function (e, value, row, d) { vue_this.device_remove(row.local_name); })")(vue)
                }
            }
        ])

    device_list_options = vue_data(lambda: 
        {
            "search": False,
            "showColumns": False,
            "showToggle": True,
            "search": True,
            "showSearchClearButton": True,
            "showRefresh": False,
            "cardView": True,
            "toolbar": "#device_list_toolbar"
        }
    )

    device_list = vue_data(lambda: [])
    add_device_columns = vue_data(lambda vue:
        [
            {
                "title": "Device",
                "field": "device"
            },
            {
                "title": "Parent Device",
                "field": "parent_device",                    
            },
            {
                "title": "Manufacturer",
                "field": "manufacturer"
            },
            {
                "title": "Model",
                "field": "model"
            },
            {
                "title": "Serial Number",
                "field": "serial_number"
            },
            {
                "title": "User Description",
                "field": "user_description"
            },
            {
                "title": "Service Name",
                "field": "service_name"
            },
            {
                "title": "URLs",
                "field": "urls"
            },
            {
                "title": "Root Object Type",
                "field": "root_object_type"                    
            },
            {
                "title": "Root Object Implements",
                "field": "root_object_implements"
            },
            {
                "title": "Action",
                "field": "action",
                "formatter": lambda a,b,c,d: '<a href="javascript:" class="device_panel_add_device"><i class="fas fs-4x fa-plus-circle"></i></a>',
                "events":
                {
                    "click .device_panel_add_device": js.Function.new("vue_this", "return (function (e, value, row, d) { vue_this.add_device_selected(row.device); })")(vue)
                }
                
            }
        ]
    )

    selected_device_info_columns = vue_data(lambda:
        [
            {
                "title": "Device",
                "field": "device"
            },
            {
                "title": "Parent Device",
                "field": "parent_device",                    
            },
            {
                "title": "Manufacturer",
                "field": "manufacturer"
            },
            {
                "title": "Model",
                "field": "model"
            },
            {
                "title": "Serial Number",
                "field": "serial_number"
            },
            {
                "title": "User Description",
                "field": "user_description"
            },
            {
                "title": "Service Name",
                "field": "service_name"
            },
            {
                "title": "URLs",
                "field": "urls"
            },
            {
                "title": "Root Object Type",
                "field": "root_object_type"                    
            },
            {
                "title": "Root Object Implements",
                "field": "root_object_implements"
            }
        ]
    )

    add_device_options = vue_data(lambda:
        {
            "search": True,
            "showSearchClearButton": True,
            "showToggle": True,
            "showColumns": False,
            "cardView": True,
            "showRefresh": False,
            "toolbar": "#add_device_toolbar"
        }
    )

    selected_device_options = vue_data(lambda: 
        {
            "search": True,
            "showSearchClearButton": True,
            "showToggle": True,
            "showColumns": False,
            "cardView": True,
            "showRefresh": False
        }
    )


    def __init__(self):
        super().__init__()

    @vue_method
    async def refresh_device_add(self, *args):
        try:
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            detected_devices = await dev_manager.async_getf_detected_devices(None)
            vue_devs = []
            ident_util = IdentifierUtil(client_obj=dev_manager)
            for d in detected_devices:
                d2 = {
                    "device": ident_util.IdentifierToString(d.device),
                    "parent_device": ident_util.IdentifierToString(d.parent_device),
                    "manufacturer": ident_util.IdentifierToString(d.manufacturer),
                    "model": ident_util.IdentifierToString(d.model),
                    "serial_number": d.serial_number,
                    "user_description": d.user_description,
                    "service_name": d.service_name,
                    "urls": "<br>".join(d.urls),
                    "root_object_type": d.root_object_type,
                    "root_object_implements": "<br>".join(d.root_object_implements)
                }
                vue_devs.append(d2)

            self.detected_devices = to_js2(vue_devs)
        except:            
            traceback.print_exc()
            js.alert(f"Refresh add device failed:\n\n{traceback.format_exc()}")

    @vue_method
    def device_add(self, evt):
        self.bv_modal.show("add-device-modal")        
        self.core.create_task(self.refresh_device_add())

    async def do_add_device_selected(self,selected_device,local_dev_name):
        try:
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            ident_util = IdentifierUtil(client_obj=dev_manager)
            dev = ident_util.StringToIdentifier(selected_device)
            await dev_manager.async_add_device(dev,local_dev_name,[],None)

        except:            
            traceback.print_exc()
            js.alert(f"Add device failed:\n\n{traceback.format_exc()}")

    @vue_method
    async def add_device_selected(self, selected_device):
        try:
            self.bv_modal.hide("add-device-modal")
            local_dev_name = js.prompt("Enter local device name")
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            ident_util = IdentifierUtil(client_obj=dev_manager)
            dev = ident_util.StringToIdentifier(selected_device)
            await dev_manager.async_add_device(dev,local_dev_name,[],None)
        except:            
            traceback.print_exc()
            js.alert(f"Add device failed:\n\n{traceback.format_exc()}")

    @vue_method
    async def device_info(self, dev_name):
        try:
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            d = await dev_manager.async_getf_device_info(dev_name,None)
            vue_devs = []
            ident_util = IdentifierUtil(client_obj=dev_manager)
            
            d2 = {
                "device": ident_util.IdentifierToString(d.device),
                "parent_device": ident_util.IdentifierToString(d.parent_device),
                "manufacturer": ident_util.IdentifierToString(d.manufacturer),
                "model": ident_util.IdentifierToString(d.model),
                "serial_number": d.serial_number,
                "user_description": d.user_description,
                "service_name": d.service_name,
                "urls": "<br>".join(d.urls),
                "root_object_type": d.root_object_type,
                "root_object_implements": "<br>".join(d.root_object_implements)
            }
            vue_devs.append(d2)

            self.selected_device_info = to_js2(vue_devs)
            self.bv_modal.show("device-info-modal")
        except:            
            traceback.print_exc()
            js.alert(f"Get device info failed:\n\n{traceback.format_exc()}")

    @vue_method
    async def device_remove(self, dev_name):
        ret = js.confirm(f"Remove device {dev_name}?")
        if not ret:
            return
        try:
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            await dev_manager.async_remove_device(dev_name,None)
        except:
            traceback.print_exc()
            js.alert(f"Device remove failed:\n\n{traceback.format_exc()}")

    @vue_method
    async def device_remove_selected(self, *args):
        
        b_device_table = self.refs.device_list
        selections = b_device_table.getSelections()
        dev_names = []
        count = len(selections)
        for i in range(count):
            t = selections[i]
            dev_names.append(t.local_name)

        if len(dev_names) == 0:
            return

        dev_names_text = ", ".join(dev_names)
        ret = js.confirm(f"Remove devices {dev_names_text}?")
        if not ret:
            return
        try:            
            dev_manager = self.core.device_manager.device_manager.GetDefaultClient()
            for dev_name in dev_names:
                await dev_manager.async_remove_device(dev_name,None)
        except:
            traceback.print_exc()
            js.alert(f"Device remove failed:\n\n{traceback.format_exc()}")
        
    @vue_method
    def implemented_types(self, local_name):
        
        implemented_types = None
        device_infos = None

        try:
            device_infos = self.core.device_infos[local_name]
        except KeyError:
            return ""
        try:            
            implemented_types = [SplitQualifiedName(device_infos["device_info"].root_object_type)[1]]
            root_object_implements = device_infos["device_info"].root_object_implements
            if root_object_implements is not None:
                implemented_types+= [SplitQualifiedName(r)[1] for r in root_object_implements]
            
        except:
            return ""
        return ", ".join(implemented_types)
    
    def core_ready(self):
        super().core_ready()

        self.core.create_task(self.run())


    async def run(self):
        await asyncio.sleep(0.1)
        
        last_devices = set()

        device_table = []
                
        while True:
            try:
                devices_states = self.core.devices_states
                new_devices = self.core.active_device_names                
                table_updated = False
                if set(new_devices) != last_devices:
                    #TODO: Remove old code
                    # getattr(self.vue,"$data").active_device_names = to_js2(new_devices)             
                    # last_devices = set(new_devices)                    
                    # for d in last_devices:
                    #     try:
                    #         getattr(self.vue,"$data").device_names[d] = devices_states.devices_states[d].device.name
                    #         getattr(self.vue,"$data").device_state_flags[d] = util.device_state_flags(devices_states, d)
                    #     except:
                    #         pass
                    last_devices = set(new_devices)
                    new_table = []
                    for d in last_devices:
                        d1 = {
                            "local_name": d,
                            "device_name": "",
                            "types": "",
                            "status": "disconnected",
                            "state_flags": "",
                            "select": False
                        }
                        
                        try:
                            d1["device_name"] = devices_states.devices_states[d].device.name
                            d1["state_flags"] = util.device_state_flags(devices_states, d)
                        except:
                            pass
                        new_table.append(d1)
                    self.device_list = to_js2(new_table)
                    device_table = new_table
                    table_updated = True                    
                            
                if not table_updated:
                    b_device_table = self.refs.device_list                    

                    for i in range(len(device_table)):
                        t = device_table[i]
                        d = t["local_name"]                        
                        try:                            
                            new_status = util.device_status_name(devices_states,d)
                            if t["status"] != new_status:                                
                                b_device_table.updateCell(to_js2({"index": i, "field": "status", "value": new_status}))                                
                                t["status"] = new_status
                            
                            new_flags = util.device_state_flags(devices_states, d)
                            if t["state_flags"] != new_flags:
                                b_device_table.updateCell(to_js2({"index": i, "field": "state_flags", "value": new_flags}))
                                t["state_flags"] = new_flags
                        except:
                            traceback.print_exc()

                        try:
                            d_name = devices_states.devices_states[d].device.name
                            if t["device_name"] != d_name:
                                b_device_table.updateCell(to_js2({"index": i, "field": "device_name", "value": d_name}))
                                t["device_name"] = d_name
                        except:
                            pass

                        try:
                            implemented_types = self.implemented_types(d)                            
                            if t["types"] != implemented_types:
                                b_device_table.updateCell(to_js2({"index": i, "field": "types", "value": implemented_types}))
                                t["types"] = implemented_types
                        except:
                            traceback.print_exc()
                            pass

                        #new_flags[d] = ""
                        #new_status[d] = "error"

                #getattr(self.vue,"$data").active_device_status = to_js2(new_status)
                        
                #getattr(self.vue,"$data").device_state_flags = to_js2(new_flags)

            except:
                traceback.print_exc()
                self.device_list = to_js2([])
            
            await asyncio.sleep(0.5)
        

def register_vue_components():
    vue_register_component('pyri-devices', PyriDevicesComponent)