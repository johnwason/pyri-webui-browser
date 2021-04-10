from typing import List, Dict, Callable, Any
from ..plugins.panel import PyriWebUIBrowserPanelBase
from .. import PyriWebUIBrowser
import importlib_resources
import js
import traceback
from RobotRaconteur.Client import *

import numpy as np

def R2rpy(R):
    assert np.linalg.norm(R[0:2,0]) > np.finfo(float).eps * 10.0, "Singular rpy requested"
    
    r=np.arctan2(R[2,1],R[2,2])
    y=np.arctan2(R[1,0], R[0,0])
    p=np.arctan2(-R[2,0], np.linalg.norm(R[2,1:3]))
        
    return (r,p,y)

def q2R(q):
   
    I = np.identity(3)
    qhat = hat(q[1:4])
    qhat2 = qhat.dot(qhat)
    return I + 2*q[0]*qhat + 2*qhat2

def hat(k):
    khat=np.zeros((3,3))
    khat[0,1]=-k[2]
    khat[0,2]=k[1]
    khat[1,0]=k[2]
    khat[1,2]=-k[0]
    khat[2,0]=-k[1]
    khat[2,1]=k[0]    
    return khat

class PyriJogPanel(PyriWebUIBrowserPanelBase):
    def __init__(self, device_manager, core):
        self.vue = None
        self.mousedown = False
        self.device_manager = device_manager
        self.core = core
        self.jog_connected = False
        
    def init_vue(self,vue):
        self.vue = vue

    def current_robot_options(self, vue, *args):
                
        robot_device_names = []

        for local_name in vue["$store"].state.active_device_names:
            
            try:
                device_infos = vue["$store"].state.device_infos[local_name]
            except KeyError:
                traceback.print_exc()
                continue
            try:                
                root_object_type = device_infos.device_info.root_object_type
                if root_object_type == "com.robotraconteur.robotics.robot.Robot":
                    robot_device_names.append({"value": local_name, "text": local_name})
                    continue
                root_object_implements = device_infos.device_info.root_object_implements
                if "com.robotraconteur.robotics.robot.Robot" in root_object_implements:
                    robot_device_names.append({"value": local_name, "text": local_name})
                    continue           
            except AttributeError:
                traceback.print_exc()
                continue

        return js.python_to_js(robot_device_names)

    
    def watch_current_robot_options(self, new_value, *args):
        if new_value.length > 0:
            if self.vue["$data"].current_robot is None:
                self.vue["$data"].current_robot = new_value[0].value
        else:
            self.vue["$data"].current_robot = None

    def joint_state(self, vue, *args):
        
        current_robot = vue["$data"].current_robot
        if current_robot is None:
            return []

        ret = []
        joint_info = None
        joint_position = None
        try:
            joint_info = vue["$store"].state.device_infos[current_robot].extended_info["com.robotraconteur.robotics.robot.RobotInfo"].joint_info
        except AttributeError:
            #traceback.print_exc()
            pass
            
        except KeyError:
            #traceback.print_exc()
            pass

        if joint_info is None:
            return []      

        try:
            e_state = vue["$store"].state.devices_states.devices_states[current_robot].state
            if e_state is not None:
                for e in e_state:
                    if e.type == "com.robotraconteur.robotics.robot.RobotState":
                        joint_position = e.state_data.joint_position
        except AttributeError:
            traceback.print_exc()
        except KeyError:
            traceback.print_exc()

        

        for i in range(len(joint_info)):
            v = dict()
            if joint_info is not None:
                v["lower"]= f"{np.rad2deg(joint_info[i].joint_limits.lower):.2f}"
                v["upper"]= f"{np.rad2deg(joint_info[i].joint_limits.upper):.2f}"
            else:
                v["lower"] = "N/A"
                v["upper"] = "N/A"

            if joint_position is not None:
                try:
                    v["current"] = f"{np.rad2deg(joint_position[i]):.2f}"
                except KeyError:
                    v["current"] = "N/A"
            else:
                v["current"] = "N/A"
            
            ret.append(v)        
        return js.python_to_js(ret)

    def current_robot_mode(self, vue, *args):
        current_robot = vue["$data"].current_robot
        if current_robot is None:
            return "Invalid"

        mode = "Invalid"

        try:
            e_state = vue["$store"].state.devices_states.devices_states[current_robot].state
            if e_state is not None:
                for e in e_state:
                    if e.type == "com.robotraconteur.robotics.robot.RobotState":
                        command_mode = e.state_data.command_mode

                        if command_mode < 0:
                            mode = "Error"
                        elif command_mode == 0:
                            mode = "Halt"
                        elif command_mode == 1:
                            mode = "Jog"
                        elif command_mode == 2:
                            mode = "Trajectory"
                        elif command_mode == 3:
                            mode = "Position Command"
                        elif command_mode == 4:
                            mode = "Velocity Command"
                        elif command_mode == 5:
                            mode = "Homing"
                        else:
                            mode = f"Unknown ({command_mode})"
        except AttributeError:
            traceback.print_exc()
        except KeyError:
            traceback.print_exc()

        return mode

    def current_robot_connected(self, vue, *args):
        try:
            current_robot = vue["$data"].current_robot
            return vue["$store"].state.devices_states.devices_states[current_robot].connected
        except:
            return False

    def current_robot_error(self, vue, *args):
        try:
            current_robot = vue["$data"].current_robot
            return vue["$store"].state.devices_states.devices_states[current_robot].error
        except:
            return True

    def current_robot_ready(self, vue, *args):
        try:
            current_robot = vue["$data"].current_robot
            return vue["$store"].state.devices_states.devices_states[current_robot].ready
        except:
            return False

    def current_tool_connected(self, vue, *args):
        try:
            current_tool = vue["$data"].current_tool
            return vue["$store"].state.devices_states.devices_states[current_tool].connected
        except:
            return False

    def current_tool_error(self, vue, *args):
        try:
            current_tool = vue["$data"].current_tool
            return vue["$store"].state.devices_states.devices_states[current_tool].error
        except:
            return True

    def current_tool_ready(self, vue, *args):
        try:
            current_tool = vue["$data"].current_tool
            return vue["$store"].state.devices_states.devices_states[current_tool].ready
        except:
            return False

    async def get_jog(self):
        
        #TODO: Fix connect_device("robotics_jog")
        if not self.jog_connected:
            self.device_manager.connect_device("robotics_jog")            
            self.jog_connected = True
            
        current_robot = self.vue["$data"].current_robot
        if current_robot is None:
            return None, None
        try:
            jog_service = await self.device_manager.get_device_subscription("robotics_jog").AsyncGetDefaultClient(None,timeout=1)
            jog =  await jog_service.async_get_jog(current_robot,None)
            return jog
        except:
            traceback.print_exc()
            return None

    def jog_joints(self,q_i, sign):
        # @burakaksoy RR-Client-WebBrowser-Robot.py:380
        self.core.loop.create_task(self.async_jog_joints(q_i, sign))

    async def async_jog_joints(self, q_i, sign):
        try:
            # @burakaksoy RR-Client-WebBrowser-Robot.py:391
            jog = await self.get_jog()
            while (self.mousedown): 
                # Call Jog Joint Space Service funtion to handle this jogging
                # await plugin_jogJointSpace.async_jog_joints2(q_i, sign, None)
                speed_perc = float(self.vue["$data"].selected_joint_speed)
                await jog.async_jog_joints(q_i, sign, speed_perc, None)

            #await plugin_jogJointSpace.async_stop_joints(None)
        except:
            traceback.print_exc()
        
    def jog_decrement_mousedown(self, joint_index):
        self.jog_joints(joint_index+1,-1)

    def jog_increment_mousedown(self, joint_index):
        self.jog_joints(joint_index+1,+1)

    async def do_set_jog_mode(self):
        try:
            jog = await self.get_jog()
            if jog is None:
                return
            await jog.async_setf_jog_mode(None)
        except:
            traceback.print_exc()

    def set_jog_mode(self, evt):
        self.core.create_task(self.do_set_jog_mode())

    def set_halt_mode(self, evt):
        self.core.create_task(self.do_set_halt_mode())
    
    async def do_set_halt_mode(self):
        try:
            jog = await self.get_jog()
            if jog is None:
                return
            await jog.async_setf_halt_mode(None)
        except:
            traceback.print_exc()

    def mousedown_evt(self,evt):
        self.mousedown = True

    def mouseup_evt(self,evt):
        self.mousedown = False

    def mouseleave_evt(self,evt):
        self.mousedown = False
        # try:
        #     self.vue["$data"].selected_joystick_enable = "disable"
        #     self.vue["$data"].selected_task_joystick_enable = "disable"
        # except:
        #     pass

    def jog_cart_decrement_mousedown(self, index):
        #self.jog_joints(joint_index+1,-1)
        if index == 0:
            self.jog_cartesian(np.array(([-1.,0.,0.])), np.array(([0.,0.,0.])))
            return
        if index == 1:
            self.jog_cartesian(np.array(([0.,-1.,0.])), np.array(([0.,0.,0.])))
            return
        if index == 2:
            self.jog_cartesian(np.array(([0.,0.,-1.])), np.array(([0.,0.,0.])))
            return
        if index == 3:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([-1.,0.,0.])))
            return
        if index == 4:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([0.,-1.,0.])))
            return
        if index == 5:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([0.,0.,-1.])))
            return

    def jog_cart_increment_mousedown(self, index):
        #self.jog_joints(joint_index+1,+1)
        if index == 0:
            self.jog_cartesian(np.array(([+1.,0.,0.])), np.array(([0.,0.,0.])))
            return
        if index == 1:
            self.jog_cartesian(np.array(([0.,+1.,0.])), np.array(([0.,0.,0.])))
            return
        if index == 2:
            self.jog_cartesian(np.array(([0.,0.,+1.])), np.array(([0.,0.,0.])))
            return
        if index == 3:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([+1.,0.,0.])))
            return
        if index == 4:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([0.,+1.,0.])))
            return
        if index == 5:
            self.jog_cartesian(np.array(([0.,0.,0.])), np.array(([0.,0.,+1.])))
            return

    def jog_cartesian(self,P_axis, R_axis):
        # @burakaksoy RR-Client-WebBrowser-Robot.py:508
        self.core.loop.create_task(self.async_jog_cartesian(P_axis, R_axis))

    async def async_jog_cartesian(self, P_axis, R_axis):
        # @burakaksoy RR-Client-WebBrowser-Robot.py:520
        try:
            jog = await self.get_jog()
            #await jog.async_prepare_jog(None)
                            
            while (self.mousedown):
                # Call Jog Cartesian Space Service funtion to handle this jogging
                # await plugin_jogCartesianSpace.async_jog_cartesian(P_axis, R_axis, None)
                spatial_velocity_dtype = RRN.GetNamedArrayDType("com.robotraconteur.geometry.SpatialVelocity",jog)
                vel = RRN.ArrayToNamedArray(np.concatenate((R_axis,P_axis)),spatial_velocity_dtype)
                speed_perc = float(self.vue["$data"].selected_task_speed)
                await jog.async_jog_cartesian(vel, speed_perc, "robot", None)

            #await plugin_jogCartesianSpace.async_stop_joints(None)
        except:
            traceback.print_exc()
        
    def cur_ZYX_angles(self, vue, *args):
        current_robot = vue["$data"].current_robot
        if current_robot is None:
            return ""

        current_rpy = ""
        try:
            e_state = vue["$store"].state.devices_states.devices_states[current_robot].state
            if e_state is not None:
                for e in e_state:
                    if e.type == "com.robotraconteur.robotics.robot.RobotState":
                        
                        current_rpy = np.array2string(np.rad2deg(R2rpy(q2R(np.array([e.state_data.kin_chain_tcp[0][0][x] for x in range(4)],dtype=np.float64)))),formatter={'float_kind':lambda x: "%.2f" % x})
        except AttributeError:
            #traceback.print_exc()
            pass
        except KeyError:
            #traceback.print_exc()
            pass

        return current_rpy

    def cur_position(self, vue, *args):

        current_robot = vue["$data"].current_robot
        if current_robot is None:
            return ""

        current_position = ""
        try:
            e_state = vue["$store"].state.devices_states.devices_states[current_robot].state
            if e_state is not None:
                for e in e_state:
                    if e.type == "com.robotraconteur.robotics.robot.RobotState":
                        current_position = np.array2string(np.array([e.state_data.kin_chain_tcp[0][1][x] for x in range(3)],dtype=np.float64), formatter={'float_kind':lambda x: "%.2f" % x})
        except AttributeError:
            #traceback.print_exc()
            pass
        except KeyError:
            #traceback.print_exc()
            pass

        return current_position

    async def do_move_to_angles(self,joint_angles):
        try:
            jog = await self.get_jog()
            speed_perc = float(self.vue["$data"].selected_joint_speed)
            await jog.async_jog_joints_to_angles(joint_angles,speed_perc,None)
        except:
            traceback.print_exc()

    def get_target_joint_angles(self):
        try:
            current_robot = self.vue["$data"].current_robot
            joint_info = self.vue["$store"].state.device_infos[current_robot].extended_info["com.robotraconteur.robotics.robot.RobotInfo"].joint_info
        except:
            traceback.print_exc()
            js.alert("Robot not selected!")
            return

        n_joints = len(joint_info)
        target_angles = [0.0]*n_joints
        try:
            for i in range(n_joints):                
                target_angles[i] = float(js.jQuery.find(f"#j{i}_angle_in")[0].value)

            target_angles = np.deg2rad(target_angles)
        except:
            traceback.print_exc()
            js.alert("Invalid joint angle entries")
            return
        return target_angles

    def set_target_joint_angles(self,target_angles):
        # TODO: Verify the length and boards of target_angles
        try:
            for i in range(len(target_angles)):
                js.jQuery.find(f"#j{i}_angle_in")[0].value = (target_angles[i])
        except:
            traceback.print_exc()
            js.alert("Invalid joint angle entries")
            return
        return target_angles

    def move_to_angles(self,evt):
        target_angles = self.get_target_joint_angles()

        self.core.create_task(self.do_move_to_angles(target_angles))

    async def do_load_joint_pose(self):
        try:
            selected_pose = self.vue["$data"].load_joint_pose_selected
            var_storage = self.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            joint_pose = await var_storage.async_getf_variable_value("globals",selected_pose,None)
            self.set_target_joint_angles(joint_pose.data)
            
        except:
            traceback.print_exc()
            js.alert(f"Refresh joint pose failed:\n\n{traceback.format_exc()}")

    def load_joint_pose(self,evt):
        self.core.create_task(self.do_load_joint_pose())
        
    async def do_refresh_joint_pose_options(self):
        try:
            var_storage = self.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            joint_pose_names = await var_storage.async_filter_variables("globals",".*",["joint_pose"],None)
            self.vue["$data"].load_joint_pose_options = js.python_to_js(joint_pose_names)
        except:
            traceback.print_exc()
            js.alert(f"Save joint pose failed:\n\n{traceback.format_exc()}")

    def refresh_joint_pose_options(self,evt):
        self.core.create_task(self.do_refresh_joint_pose_options())

    async def do_save_joint_pose(self, name, joint_angles):
        try:
            var_storage = self.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            var_consts = RRN.GetConstants('tech.pyri.variable_storage', var_storage)
            variable_persistence = var_consts["VariablePersistence"]
            variable_protection_level = var_consts["VariableProtectionLevel"]
                                    
            await var_storage.async_add_variable2("globals", name ,"double[]", \
                RR.VarValue(np.array(joint_angles,dtype=np.float64),"double[]"), ['joint_pose'], {}, variable_persistence["const"], None, variable_protection_level["read_write"], \
                    [], "Saved joint pose", False, None)
        except:
            traceback.print_exc()
            js.alert(f"Save joint pose failed:\n\n{traceback.format_exc()}")

    def save_joint_pose(self,evt):
        joint_pose_name = js.prompt("Joint Pose Name")
        current_robot = self.vue["$data"].current_robot
        joint_angles = None
        e_state = self.vue["$store"].state.devices_states.devices_states[current_robot].state
        if e_state is not None:
            for e in e_state:
                if e.type == "com.robotraconteur.robotics.robot.RobotState":
                    joint_angles = np.rad2deg([j for j in e.state_data.joint_position])
        if joint_angles is None:
            js.alert("Could not determine robot pose")
            return
        self.core.create_task(self.do_save_joint_pose(joint_pose_name,joint_angles))

    async def do_delete_joint_pose(self):
        try:
            selected_pose = self.vue["$data"].load_joint_pose_selected
            var_storage = self.device_manager.get_device_subscription("variable_storage").GetDefaultClient()
            await var_storage.async_delete_variable("globals",selected_pose,None)
            
        except:
            traceback.print_exc()
            js.alert(f"Save joint pose failed:\n\n{traceback.format_exc()}")

    def delete_joint_pose(self,evt):
        self.core.create_task(self.do_delete_joint_pose())

    def current_tool_options(self, vue, *args):
                
        tool_device_names = []

        for local_name in vue["$store"].state.active_device_names:
            
            try:
                device_infos = vue["$store"].state.device_infos[local_name]
            except KeyError:
                traceback.print_exc()
                continue
            try:                
                root_object_type = device_infos.device_info.root_object_type
                if root_object_type == "com.robotraconteur.robotics.tool.Tool":
                    tool_device_names.append({"value": local_name, "text": local_name})
                    continue
                root_object_implements = device_infos.device_info.root_object_implements
                if "com.robotraconteur.robotics.tool.Tool" in root_object_implements:
                    tool_device_names.append({"value": local_name, "text": local_name})
                    continue           
            except AttributeError:
                traceback.print_exc()
                continue

        return js.python_to_js(tool_device_names)

    
    def watch_current_tool_options(self, new_value, *args):
        if new_value.length > 0:
            if self.vue["$data"].current_tool is None:
                self.vue["$data"].current_tool = new_value[0].value
        else:
            self.vue["$data"].current_tool = None

    async def get_tool(self):
        
        #TODO: Fix connect_device("jog_joint")
        if not self.jog_connected:
            self.device_manager.connect_device("robotics_jog")            
            self.jog_connected = True
            
        current_tool = self.vue["$data"].current_tool
        if current_tool is None:
            return None
        try:
            jog_service = await self.device_manager.get_device_subscription("robotics_jog").AsyncGetDefaultClient(None,timeout=1)
        except:
            return None
        return  await jog_service.async_get_tool(current_tool,None)        

    def tool_open(self):
        self.core.loop.create_task(self.async_tool_open())

    async def async_tool_open(self):
        try:
            
            tool = await self.get_tool()
            await tool.async_open(None)            
        except:
            traceback.print_exc()

    def tool_close(self):
        self.core.loop.create_task(self.async_tool_close())

    async def async_tool_close(self):
        try:
            
            tool = await self.get_tool()
            await tool.async_close(None)            
        except:
            traceback.print_exc()

    async def async_selected_joystick_enable_changed(self,e):
        try:

            if e == "disable":
                jog = await self.get_jog()
                await jog.async_disable_jog_joints_joystick(None)
                return
            if e == "group1":
                group = 0,
            elif e == "group2":
                group = 1
            else:
                assert False, "Invalid joint jog group"
            
            self.vue["$data"].selected_task_joystick_enable = "disable"
            jog = await self.get_jog()
            while self.vue["$data"].selected_joystick_enable == e: 
                # Call Jog Joint Space Service funtion to handle this jogging
                # await plugin_jogJointSpace.async_jog_joints2(q_i, sign, None)
                speed_perc = float(self.vue["$data"].selected_joint_speed)
                
                await jog.async_enable_jog_joints_joystick(group, speed_perc, None)

            #await plugin_jogJointSpace.async_stop_joints(None)
        except:
            self.vue["$data"].selected_joystick_enable = "disable"
            traceback.print_exc()

    def selected_joystick_enable_changed(self,e):
        self.core.loop.create_task(self.async_selected_joystick_enable_changed(e))

    async def async_selected_task_joystick_enable_changed(self,e):
        try:

            if e == "disable":
                jog = await self.get_jog()
                await jog.async_disable_jog_cartesian_joystick(None)
                return
            assert e=="enable"

            self.vue["$data"].selected_joystick_enable = "disable"
                            
            jog = await self.get_jog()
            while self.vue["$data"].selected_task_joystick_enable == "enable": 
                # Call Jog Joint Space Service funtion to handle this jogging
                # await plugin_jogJointSpace.async_jog_joints2(q_i, sign, None)
                speed_perc = float(self.vue["$data"].selected_task_speed)
                
                await jog.async_enable_jog_cartesian_joystick(speed_perc, "robot", None)

            #await plugin_jogJointSpace.async_stop_joints(None)
        except:
            self.vue["$data"].selected_task_joystick_enable = "disable"
            traceback.print_exc()

    def selected_task_joystick_enable_changed(self,e):
        self.core.loop.create_task(self.async_selected_task_joystick_enable_changed(e))

    def current_robot_changed(self,e):
        self.vue["$data"].selected_joystick_enable = "disable"
        self.vue["$data"].selected_task_joystick_enable = "disable"        



async def add_jog_panel(panel_type: str, core: PyriWebUIBrowser, parent_element: Any):

    assert panel_type == "jog"

    
    jog_panel_html = importlib_resources.read_text(__package__,"jog_panel.html")

    panel_config = {
        "type": "component",
        "componentName": "jog",
        "componentState": {},
        "title": "Jogging",
        "id": "jog",
        "isClosable": False
    }

    gl = core.layout.layout

    def register_jog_panel(container, state):
        container.getElement().html(jog_panel_html)

    core.layout.register_component("jog",register_jog_panel)

    core.layout.add_panel(panel_config)

    core.layout.add_panel_menu_item("jog", "Jogging")

    jog_panel_obj = PyriJogPanel(core.device_manager,core)

    jog_panel = js.Vue.new(js.python_to_js({
        "el": "#jog_panel_component",
        "store": core.vuex_store,
        "data":
        {
            "current_robot": None,
            "current_tool": None,
            "load_joint_pose_selected": "",
            "load_joint_pose_options": [],
            "selected_joint_speed": 10,
            "selected_task_speed": 10,
            "selected_joystick_enable": "disable",
            "selected_task_joystick_enable": "disable"

        },
        "methods":
        {
            "current_robot_changed": jog_panel_obj.current_robot_changed,
            "jog_decrement_mousedown": jog_panel_obj.jog_decrement_mousedown,
            "jog_increment_mousedown": jog_panel_obj.jog_increment_mousedown,
            "set_jog_mode": jog_panel_obj.set_jog_mode,
            "set_halt_mode": jog_panel_obj.set_halt_mode,
            "mousedown": jog_panel_obj.mousedown_evt,
            "mouseup": jog_panel_obj.mouseup_evt,
            "mouseleave": jog_panel_obj.mouseleave_evt,
            "jog_cart_decrement_mousedown": jog_panel_obj.jog_cart_decrement_mousedown,
            "jog_cart_increment_mousedown": jog_panel_obj.jog_cart_increment_mousedown,
            "move_to_angles": jog_panel_obj.move_to_angles,
            "load_joint_pose": jog_panel_obj.load_joint_pose,
            "refresh_joint_pose_options": jog_panel_obj.refresh_joint_pose_options,
            "save_joint_pose": jog_panel_obj.save_joint_pose,
            "delete_joint_pose": jog_panel_obj.delete_joint_pose,
            "tool_open": jog_panel_obj.tool_open,
            "tool_close": jog_panel_obj.tool_close,
            "selected_joystick_enable_changed": jog_panel_obj.selected_joystick_enable_changed,
            "selected_task_joystick_enable_changed": jog_panel_obj.selected_task_joystick_enable_changed

        },
        "computed": 
        {
            "current_robot_options": jog_panel_obj.current_robot_options,
            "current_robot_connected": jog_panel_obj.current_robot_connected,
            "current_robot_error": jog_panel_obj.current_robot_error,
            "current_robot_ready": jog_panel_obj.current_robot_ready,
            "joint_state": jog_panel_obj.joint_state,
            "current_robot_mode": jog_panel_obj.current_robot_mode,
            "cur_ZYX_angles": jog_panel_obj.cur_ZYX_angles,
            "cur_position": jog_panel_obj.cur_position,
            "current_tool_options": jog_panel_obj.current_tool_options,
            "current_tool_connected": jog_panel_obj.current_tool_connected,
            "current_tool_error": jog_panel_obj.current_tool_error,
            "current_tool_ready": jog_panel_obj.current_tool_ready,
        },
        "watch":
        {
            "current_robot_options": jog_panel_obj.watch_current_robot_options,
            "current_tool_options": jog_panel_obj.watch_current_tool_options

        }
    }))

    jog_panel_obj.init_vue(jog_panel)

    return jog_panel_obj