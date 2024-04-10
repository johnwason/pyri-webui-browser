from typing import List, Dict, Callable, Any, Union, Tuple
import importlib_resources
import js
import traceback
import asyncio

from ..util import to_js2

from ..pyri_vue import PyriVue, VueComponent, vue_register_component, vue_data, vue_method, vue_prop
from RobotRaconteur.Client import *
from RobotRaconteurCompanion.Util.UuidUtil import UuidUtil
from .procedure_util import do_stop_all, run_procedure
import io
import json

@VueComponent
class PyriBlocklyEditorComponent(PyriVue):

    vue_template = importlib_resources.read_text(__package__,"procedure_blockly_component.html")

    procedure_name = vue_prop()

    component_info = vue_prop()

    def __init__(self):
        super().__init__()
       
    @vue_method
    async def iframe_load(self, *evt):
        try:

            if self.procedure_name:
                self._procedure_name = self.procedure_name
            else:
                self._procedure_name = self.component_info.procedure_name

            variable_manager = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()

            procedure_src = await variable_manager.async_getf_variable_value("procedure",self._procedure_name,None)

            iframe = self.refs.procedure_blockly_iframe.contentWindow

            delay_count = 0
            while not iframe.blocklyReady():
                delay_count+=1
                assert delay_count < 100
                await asyncio.sleep(0.1)

            iframe.setBlocklyJsonText(procedure_src.data)
        except:
            traceback.print_exc()

    @vue_method
    async def save(self, evt):
        iframe = self.refs.procedure_blockly_iframe.contentWindow

        blockly_json = iframe.getBlocklyJsonText()
        
        try:
            variable_manager = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            await variable_manager.async_setf_variable_value("procedure",self._procedure_name,RR.VarValue(blockly_json,"string"),None)
        except:
            traceback.print_exc()
        
    @vue_method
    def run(self, evt):
        self.core.create_task(run_procedure(self.core.device_manager,self._procedure_name,self))

    @vue_method
    def stop_all(self, evt):
        do_stop_all(self.core,self.core.device_manager)

def register_vue_components():
    vue_register_component("pyri-blockly-editor", PyriBlocklyEditorComponent)

async def open_blockly_editor_panel(core, procedure_name, parent_panel_id = "root"):

    from ..golden_layout import PyriGoldenLayoutPanelConfig

    pyri_panel_config = PyriGoldenLayoutPanelConfig(
        component_type= "pyri-blockly-editor",
        panel_id = f"procedure_blockly_{procedure_name}",
        panel_title = procedure_name,
        closeable=True, 
        component_info = {
            "procedure_name": procedure_name
        },
    )

    await core.layout.add_panel(pyri_panel_config, parent_panel_id)