from typing import List, Dict, Callable, Any, Union, Tuple
import importlib_resources
import js
import traceback

from ..util import to_js2

from ..pyri_vue import PyriVue, VueComponent, vue_register_component, vue_data, vue_method, vue_prop
from RobotRaconteur.Client import *
from RobotRaconteurCompanion.Util.UuidUtil import UuidUtil
from .procedure_util import do_stop_all, run_procedure
import io
import json
import asyncio

@VueComponent
class PyriEditorComponent(PyriVue):

    vue_template = importlib_resources.read_text(__package__,"procedure_pyri_component.html")

    procedure_name = vue_prop()

    component_info = vue_prop()

    insert_function_selected = vue_data()
    insert_function_options = vue_data(lambda: [])
    insert_function_selected_doc = vue_data("")

    def __init__(self):
        super().__init__()


    @vue_method    
    async def iframe_load(self, *args):
        try:
            print("iframe_loaded")
            if self.procedure_name:
                self._procedure_name = self.procedure_name
            else:
                self._procedure_name = self.component_info.procedure_name
            
            variable_manager = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()

            procedure_src = await variable_manager.async_getf_variable_value("procedure",self._procedure_name,None)

            iframe = self.refs.procedure_pyri_iframe.contentWindow

            delay_count = 0
            while not iframe.editorReady():
                delay_count+=1
                assert delay_count < 100
                await asyncio.sleep(0.1)

            iframe.setValue(procedure_src.data)
        except:
            traceback.print_exc()

    @vue_method
    async def save(self, evt):
        iframe = self.refs.procedure_pyri_iframe.contentWindow

        pyri_src = iframe.getValue()
       
        try:
            variable_manager = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            await variable_manager.async_setf_variable_value("procedure",self._procedure_name,RR.VarValue(pyri_src,"string"),None)
        except:
            traceback.print_exc()
        
    @vue_method
    def run(self, evt):
        self.core.create_task(run_procedure(self.core.device_manager,self._procedure_name,self))

    @vue_method
    def stop_all(self, evt):
        do_stop_all(self.core,self.core.device_manager)

    def _get_iframe(self):
        iframe = self.refs.procedure_pyri_iframe.contentWindow
        return iframe

    @vue_method
    def cursor_left(self,evt):
        self._get_iframe().cursorLeft()

    @vue_method
    def cursor_right(self,evt):
        self._get_iframe().cursorRight()

    @vue_method
    def cursor_up(self,evt):
        self._get_iframe().cursorUp()

    @vue_method
    def cursor_down(self,evt):
        self._get_iframe().cursorDown()

    @vue_method
    def cursor_home(self,evt):
        self._get_iframe().home()

    @vue_method
    def cursor_end(self,evt):
        self._get_iframe().end()

    @vue_method
    def cursor_outdent(self,evt):
        self._get_iframe().outdentLines()

    @vue_method
    def cursor_indent(self,evt):
        self._get_iframe().indentLines()

    @vue_method
    def move_line_up(self,evt):
        self._get_iframe().moveLineUp()

    @vue_method
    def move_line_down(self,evt):
        self._get_iframe().moveLineDown()

    @vue_method
    def editor_newline(self,evt):
        self._get_iframe().newline()

    @vue_method
    def editor_select_more(self,evt):
        self._get_iframe().selectMore()
    
    @vue_method
    def editor_select_less(self,evt):
        self._get_iframe().selectLess()

    @vue_method
    def editor_delete_left(self,evt):
        self._get_iframe().deleteLeft()

    @vue_method
    def editor_delete_right(self,evt):
        self._get_iframe().deleteRight()

    @vue_method
    def editor_delete_line(self,evt):
        self._get_iframe().deleteLine()

    @vue_method
    def editor_find(self,evt):
        self._get_iframe().find()

    @vue_method
    def editor_replace(self,evt):
        self._get_iframe().replace()

    @vue_method
    def editor_gotoline(self,evt):
        self._get_iframe().gotoline()

    @vue_method
    def editor_undo(self,evt):
        self._get_iframe().undo()

    @vue_method
    def editor_redo(self,evt):
        self._get_iframe().redo()

    @vue_method
    def editor_comment_line(self,evt):
        self._get_iframe().commentLine()

    @vue_method
    def editor_remove_comment_line(self,evt):
        self._get_iframe().removeCommentLine()

    @vue_method
    async def insert_function(self, evt):
        try:
            res = await js.fetch('/sandbox_functions/all_functions.json', {"cache": "no-store"})
            res_io = io.TextIOWrapper(io.BytesIO((await res.arrayBuffer()).to_py()),encoding="utf-8")
            res_str = res_io.read()

            res_json = json.loads(res_str)

            all_functions_list = res_json["all_functions"]
            all_functions = {}
            for v in all_functions_list:
                all_functions[v["name"]] = v

            self.all_functions = all_functions

            opts = []
            for v in self.all_functions.values():
                opts.append({
                    "value": v["name"],
                    "text": v["full_signature"]
                })

            getattr(self.vue,"$data").insert_function_options = to_js2(opts)

            getattr(self.vue,"$bvModal").show("insert-function-modal")
        except:
            traceback.print_exc()

    @vue_method
    def insert_function_selected_changed(self,value):
        if value is None:
            return

        try:
            v = self.all_functions[value]
            getattr(self.vue,"$data").insert_function_selected_doc = v["docstring"] or ""
        except:
            traceback.print_exc()

    @vue_method
    def insert_function_ok(self,evt):
        try:
            value = getattr(self.vue,"$data").insert_function_selected
            if value is None:
                return
            v = self.all_functions[value]

            iframe = self._get_iframe()
            iframe.insertText(v["full_signature"])

        except:
            traceback.print_exc()

    @vue_method
    def insert_function_hidden(self,*args):
        getattr(self.vue,"$data").insert_function_selected_doc = ""
        getattr(self.vue,"$data").insert_function_selected = None

def register_vue_components():
    vue_register_component("pyri-editor", PyriEditorComponent)

async def open_pyri_editor_panel(core, procedure_name, parent_panel_id = "root"):

    from ..golden_layout import PyriGoldenLayoutPanelConfig

    pyri_panel_config = PyriGoldenLayoutPanelConfig(
        component_type= "pyri-editor",
        panel_id = f"procedure_pyri_{procedure_name}",
        panel_title = procedure_name,
        closeable=True, 
        component_info = {
            "procedure_name": procedure_name
        },
    )

    await core.layout.add_panel(pyri_panel_config, parent_panel_id)
