from typing import List, Dict, Callable, Any, Union, Tuple
import importlib_resources
import js
import traceback
import asyncio

from ..util import to_js2

from ..pyri_vue import PyriVue, VueComponent, vue_register_component, vue_data, vue_method
from RobotRaconteur.Client import *

@VueComponent
class PyriProcedureOutputComponent(PyriVue):

    vue_template = """<pyri-terminal-output ref="output_terminal"/>"""

    def __init__(self):
        super().__init__()

    def core_ready(self):
        super().core_ready()
        self.get_ref_pyobj("output_terminal").append_output_line("Welcome to PyRI! Procedure output will show here.")
        self.core.create_task(self.run())

    async def run(self):
        output_type_to_css_class = {}
        try:
            while True:
                try:
                    sandbox = self.core.device_manager.get_device_subscription("sandbox").GetDefaultClient()
                    output_type_consts = RRN.GetConstants("tech.pyri.sandbox",sandbox)["ProcedureOutputTypeCode"]

                    output_type_to_css_class = {
                        output_type_consts["status"]: "text-success",
                        output_type_consts["info"]: "text-info",
                        output_type_consts["error"]: "text-danger",
                        output_type_consts["debug"]: "text-muted"
                    }

                except Exception:
                    traceback.print_exc()
                    await asyncio.sleep(2)
                    continue
                try:
                    gen = await sandbox.async_getf_output(None)
                    try:
                        while True:

                            output_list = await gen.AsyncNext(None,None)
                            lines_append = [ (l.output, output_type_to_css_class.get(l.output_type,"text_muted")) \
                                for l in  output_list.output_list ]

                            self.get_ref_pyobj("output_terminal").append_output_lines(lines_append)

                    except RR.StopIterationException:
                            continue
                except Exception:
                    traceback.print_exc()
                    await asyncio.sleep(0.5)
                    continue                
        except:
            traceback.print_exc()

def register_vue_components():
    vue_register_component("pyri-procedure-output", PyriProcedureOutputComponent)
