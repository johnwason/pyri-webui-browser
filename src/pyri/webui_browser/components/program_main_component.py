from typing import List, Dict, Callable, Any, Union, Tuple
import importlib_resources
import js
import traceback

from ..util import to_js2

from ..pyri_vue import PyriVue, VueComponent, vue_register_component, vue_data, vue_method
from RobotRaconteur.Client import *
from RobotRaconteurCompanion.Util.UuidUtil import UuidUtil
from .procedure_util import do_stop_all, rr_uuid_to_py_uuid
import uuid
import re
import asyncio

@VueComponent
class PyriProgramMainComponent(PyriVue):

    vue_template = importlib_resources.read_text(__package__, "program_main_component.html")

    program_name = vue_data("main")
    current_program = vue_data(None)
    program_steps = vue_data(lambda: [])
    edit_step_name = vue_data("")
    edit_step_uuid = vue_data(None)
    edit_step_index = vue_data(-1)
    edit_step_procedure_name = vue_data("")
    edit_step_procedure_args = vue_data("")
    edit_step_next_steps = vue_data("")
    start_marker_highlight_class = vue_data("")

    def __init__(self):
        super().__init__()

    def core_ready(self):
        super().core_ready()

        # TODO: initial reload
        #self.core.create_task(self.reload())
        self.core.create_task(self.run())
         
    def _get_client(self):
        return self.core.device_manager.get_device_subscription("program_master").GetDefaultClient()

    @vue_method
    async def save(self, evt):
        try:
            program = self.current_program
            assert program is not None, "Internal program error"
            program_var = RR.VarValue(program,"tech.pyri.program_master.PyriProgram")
            var_storage = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            exists_l = await var_storage.async_filter_variables("program", "main", [], None)
            if len(exists_l) > 0:
                await var_storage.async_setf_variable_value("program",self.program_name,program_var,None)
            else:
                var_consts = RRN.GetConstants('tech.pyri.variable_storage', var_storage)
                variable_persistence = var_consts["VariablePersistence"]
                variable_protection_level = var_consts["VariableProtectionLevel"]
                var_storage.async_add_variable2("program","main","tech.pyri.program_master.PyriProgram", \
                    RR.VarValue(program,"tech.pyri.program_master.PyriProgram"), ["program"], {}, variable_persistence["const"], \
                    None, variable_protection_level["read_write"], \
                    [], "test state machine program", False, None)
        except:
            js.alert(f"Run failed :\n\n{traceback.format_exc()}")


    def _op_code_to_class(self,opcode):
        if opcode == 1:
            return "program_main_step_op_stop"
        elif opcode == 2:
            return "program_main_step_op_next"
        elif opcode == 3:
            return "program_main_step_op_jump"
        elif opcode == 4:
            return "program_main_step_op_error"
        
        return "program_main_step_op_error"

    def _program_to_plain(self,program):
        uuid_util = UuidUtil(client_obj=self._get_client())
        ret = []
        for s1 in program.steps:
            uuid_str = uuid_util.UuidToString(s1.step_id)
            s2 = {
                "name": s1.step_name,
                "procedure": s1.procedure_name,
                "procedure_args": ", ".join(s1.procedure_args),
                "card_id": f"program-main-step_{uuid_str}",
                "uuid": uuid_str
            }
            next_steps = []
            for n in s1.next:
                jump_target = ""
                if n.op_code == 3:
                    jump_target_uuid = uuid_util.UuidToPyUuid(n.jump_target)
                    for s3 in program.steps:
                        if uuid_util.UuidToPyUuid(s3.step_id) == jump_target_uuid:
                            jump_target = s3.step_name
                            break

                next_steps.append(
                    {
                        "result": n.result,
                        "op_code_class": self._op_code_to_class(n.op_code),
                        "jump_target": jump_target
                    }
                )
                s2["next_steps"] = next_steps

            ret.append(s2)
        return ret

    def _program_to_vue_program_steps(self, program):
        ret = self._program_to_plain(program)
        for r in ret:
            r["step_highlight_class"] = ""
        return to_js2(ret)

    @vue_method
    async def reload(self, evt = None, show_error = True):
        try:
            var_storage = self.core.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            program = await var_storage.async_getf_variable_value("program",self.program_name,None)
            self.program_steps = self._program_to_vue_program_steps(program.data)
            self.current_program = program.data
        except:
            if show_error:
                js.alert(f"Program main load failed:\n\n{traceback.format_exc()}")
            else:
                traceback.print_exc()

    async def do_run(self):
        try:
            await self._get_client().async_run(None)
        except:
            js.alert(f"Run failed :\n\n{traceback.format_exc()}")

    @vue_method
    def run_btn(self, evt):
        self.core.create_task(self.do_run())

    async def do_step_one(self):
        try:
            await self._get_client().async_step_one(None)
        except:
            js.alert(f"Step one failed :\n\n{traceback.format_exc()}")

    @vue_method
    def step_one(self, evt):
        self.core.create_task(self.do_step_one())

    @vue_method
    async def pause(self, evt):
        try:
            await self._get_client().async_pause(None)
        except:
            js.alert(f"Pause failed :\n\n{traceback.format_exc()}")

    @vue_method
    def stop_all(self, evt):
        do_stop_all(self.core,self.core.device_manager)

    @vue_method
    def add_step(self, evt):
        try:
            self.fill_edit_step(-1)
            self.bv_modal.show("program_main_edit_step_modal")
        except:
            traceback.print_exc()

    @vue_method
    async def move_cursor_to_step(self,index):
        try:
            step_id = self.current_program.steps[index].step_id
            await self._get_client().async_setf_step_pointer(step_id,None)
        except:
            js.alert(f"Move cursor to step failed :\n\n{traceback.format_exc()}")

    @vue_method
    async def clear_error(self, evt):
        try:
            await self._get_client().async_clear_errors(None)
        except:
            js.alert(f"Clear errors failed :\n\n{traceback.format_exc()}")

    @vue_method
    async def clear_pointer(self, evt):
        try:
            await self._get_client().async_clear_step_pointer(None)
        except:
            js.alert(f"Clear step pointer failed :\n\n{traceback.format_exc()}")

    @vue_method
    def move_step_up(self, index):
        try:
            program = self.current_program
            if index == 0:
                return

            step = program.steps.pop(index)
            program.steps.insert(index-1,step)
            
            self.program_steps = self._program_to_vue_program_steps(program)
            self.current_program = program

        except:
            js.alert(f"Move step up failed :\n\n{traceback.format_exc()}")

    @vue_method
    def move_step_down(self, index):
        try:
            program = self.current_program
            if not index < len(program.steps)-1:
                return
            step = program.steps.pop(index)
            program.steps.insert(index+1,step)
            
            self.program_steps = self._program_to_vue_program_steps(program)
            self.current_program = program

        except:
            js.alert(f"Move step down failed :\n\n{traceback.format_exc()}")

    @vue_method
    def delete_step(self, index):
        try:
            program = self.current_program
            program.steps.pop(index)
            
            self.program_steps = self._program_to_vue_program_steps(program)
            self.current_program = program

        except:
            js.alert(f"Move step down failed :\n\n{traceback.format_exc()}")

    @vue_method
    def configure_step(self, index):
        try:
            self.fill_edit_step(index)
            self.bv_modal.show("program_main_edit_step_modal")
        except:
            traceback.print_exc()

    async def run(self):
        await asyncio.sleep(0.1)
        
        while True:
            try:
                try:
                    program_master_state = None
                    if self.core.devices_states is not None:
                        e_state = self.core.devices_states.devices_states["program_master"].state
                        if e_state is not None:
                            for e in e_state:
                                if e.type == "tech.pyri.program_master.PyriProgramState":
                                    program_master_state = e.state_data.data
                except KeyError:
                    traceback.print_exc()
                else:
                    if program_master_state is not None:
                        current_step_uuid = str(rr_uuid_to_py_uuid(program_master_state.current_step))
                        flags = program_master_state.program_state_flags
                        if (flags & 0x2) != 0:
                            step_class = "bg-danger"
                        elif (flags & 0x10) != 0:
                            step_class = "bg-warning"
                        elif (flags & 0x8) != 0:
                            step_class = "bg-success"
                        else:
                            step_class = "bg-info"
                        if current_step_uuid == "00000000-0000-0000-0000-000000000000":
                            self.start_marker_highlight_class = step_class
                        else:
                            self.start_marker_highlight_class = ""

                        for i in range(len(self.program_steps)):
                            if self.program_steps[i].uuid == current_step_uuid:
                                self.program_steps[i].step_highlight_class = step_class
                            else:
                                self.program_steps[i].step_highlight_class = ""

            except:
                traceback.print_exc()

            await asyncio.sleep(0.2)

    @vue_method
    def edit_step_ok(self, evt):
        name_regex = "^[a-zA-Z](?:\\w*[a-zA-Z0-9])?$"
        step_regex = r"^(\w+)\s+(?:(stop)|(next)|(error)|(?:(jump))\s+([a-zA-Z](?:\w*[a-zA-Z0-9])?))$"
        try:
            step_name = self.edit_step_name.strip()
            m = re.match(name_regex, step_name)
            if m is None:
                js.alert(f"Invalid step name: {step_name}")
                evt.preventDefault()
                return

            procedure_name = self.edit_step_procedure_name.strip()
            m = re.match(name_regex, procedure_name)
            if m is None:
                js.alert(f"Invalid procedure name: {procedure_name}")
                evt.preventDefault()
                return

            procedure_args = self.edit_step_procedure_args.strip().splitlines()
            procedure_args = [s.strip() for s in procedure_args]
            if "" in procedure_args:
                js.alert(f"Invalid procedure args: {', '.join(procedure_args)}")
                evt.preventDefault()
                return

            next_steps = self.edit_step_next_steps.strip().splitlines()
            for p in next_steps:
                m = re.match(step_regex, p)
                if m is None:
                    js.alert(f"Invalid next steps: {', '.join(next_steps)}")
                    evt.preventDefault()
                    return
                if m.group(5) is not None:
                    jump_target_name = m.group(6)
                    jump_target_found = False
                    for s1 in self.current_program.steps:
                        if s1.step_name == jump_target_name:
                            jump_target_found = True
                    if not jump_target_found:
                        js.alert(f"Invalid jump target: {jump_target_name}")
                        evt.preventDefault()
                        return

            step_index = self.edit_step_index
            step_uuid = uuid.UUID(self.edit_step_uuid)

            client = self._get_client()
            uuid_util = UuidUtil(client_obj = client)

            if step_index < 0:
                step = RRN.NewStructure("tech.pyri.program_master.PyriProgramStep", client)
                step.step_id = uuid_util.UuidFromPyUuid(step_uuid)
            else:
                step = self.current_program.steps[step_index]
                assert step_uuid == rr_uuid_to_py_uuid(step.step_id), "Internal error updating step"

            step.step_name = step_name
            step.procedure_name = procedure_name
            step.procedure_args = procedure_args

            next_steps2 = []
            for p in next_steps:
                n = RRN.NewStructure("tech.pyri.program_master.PyriProgramStepNext", client)
                m = re.match(step_regex, p)
                n.result = m.group(1)
                n.jump_target = uuid_util.UuidFromPyUuid(uuid.UUID(bytes=b'\x00'*16))
                if m.group(2) is not None:
                    n.op_code = 1
                elif m.group(3) is not None:
                    n.op_code = 2
                elif m.group(4) is not None:
                    n.op_code = 4
                elif m.group(5) is not None:
                    n.op_code = 3
                    jump_target_name = m.group(6)
                    jump_target_uuid = None
                    if self.current_program is not None:
                        for s1 in self.current_program.steps:
                            if s1.step_name == jump_target_name:
                                jump_target_uuid = s1.step_id
                    assert jump_target_uuid is not None, f"Internal error finding jump target {jump_target_name}"
                    n.jump_target = jump_target_uuid

                next_steps2.append(n)

            step.next = next_steps2

            if step_index < 0:
                if self.current_program is None:
                    self.current_program = RRN.NewStructure("tech.pyri.program_master.PyriProgram", client)
                    self.current_program.steps=[]
                    self.current_program.name="main"
                self.current_program.steps.append(step)
            
            self.program_steps = self._program_to_vue_program_steps(self.current_program)
            self.highlighted_step_class = None
            self.highlighted_step_uuid = None

        except:
            js.alert(f"Error applying changes:\n\n{traceback.format_exc()}")

    def fill_edit_step(self, index):
        step = None
        if index >= 0:
            try:
                step = self.current_program.steps[index]
            except IndexError:
                pass
        if step is not None:
            self.edit_step_name = step.step_name
            self.edit_step_uuid = str(rr_uuid_to_py_uuid(step.step_id))
            self.edit_step_index = index
            self.edit_step_procedure_name = step.procedure_name
            self.edit_step_procedure_args = "\n".join(step.procedure_args)
            next_steps = []
            for n in step.next:
                if n.op_code == 1:
                    next_steps.append(f"{n.result} stop")
                elif n.op_code == 2:
                    next_steps.append(f"{n.result} next")
                elif n.op_code == 3:
                    jump_target = None
                    jump_target_uuid = rr_uuid_to_py_uuid(n.jump_target)
                    for s3 in self.current_program.steps:
                        if rr_uuid_to_py_uuid(s3.step_id) == jump_target_uuid:
                            jump_target = s3.step_name
                            break
                    if jump_target is None:
                        next_steps.append(f"{n.result} error")    
                    else:
                        next_steps.append(f"{n.result} jump {str(jump_target)}")
                elif n.op_code == 4:
                    next_steps.append(f"{n.result} error")
                else:
                    next_steps.append(f"{n.result} error")
            
            self.edit_step_next_steps = "\n".join(next_steps)
        else:
            new_ind = 0
            if self.current_program is not None:
                new_ind = len(self.current_program.steps)
                for s in self.current_program.steps:
                    m = re.match(r"^step(\d+)$", s.step_name)
                    if m is not None:
                        ind1 = int(m.group(1))
                        if ind1 > new_ind:
                            new_ind = ind1

            self.edit_step_name = f"step{new_ind+1}"
            self.edit_step_uuid = str(uuid.uuid4())
            self.edit_step_index = -1
            self.edit_step_procedure_name = "my_procedure"
            self.edit_step_procedure_args = ""
            self.edit_step_next_steps = "DEFAULT next\nERROR error"

def register_vue_components():
    vue_register_component("pyri-program-main", PyriProgramMainComponent)