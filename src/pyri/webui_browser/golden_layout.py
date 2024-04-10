import js
import json
from .util import to_js2
from pyodide.ffi import create_proxy
from .pyri_vue import PyriVue, VueComponent, vue_data, vue_prop, vue_register_component
import traceback
from typing import NamedTuple, Dict

_golden_layout_config = {
    "settings":{
        "hasHeaders": True,
        "constrainDragToContainer": True,
        "reorderEnabled": True,
        "selectionEnabled": False,
        "popoutWholeStack": False,
        "blockedPopoutsThrowError": True,
        "closePopoutsOnUnload": True,
        "showPopoutIcon": False, 
        "showMaximiseIcon": True,
        "showCloseIcon": False
    },
    "dimensions": 
    {
        "borderWidth": 15,
        "minItemHeight": 10,
        "minItemWidth": 10,
        "headerHeight": 30,
        "dragProxyWidth": 300,
        "dragProxyHeight": 200
    },
    "labels": 
    {
        "close": 'close',
        "maximise": 'maximise',
        "minimise": 'minimise',
        "popout": 'open in new window'
    },
    "root":
    {
        "type": "stack",
        "isClosable": True
    },
    "header":
    {
        "popout": False,
        "popin": False,
        "close": True
    }
}


class PyriGoldenLayoutPanelConfig(NamedTuple):
    component_type: str
    panel_id: str
    panel_title: str
    closeable: bool = False
    component_info: Dict = {}
    default_parent: str = "root"

_gl_template = """
<div class="v-100 h-100">
    <div ref="goldenlayout_root" style="position: absolute; width: 100%; height: 100%">
    </div>
    <div v-for="panel in panels" :ref="'goldenlayout_vue_panel_wrapper_' + panel.panel_id" style="overflow: none">
      <component :is="panel.component_type" :key="panel.panel_id"  :ref="'goldenlayout_vue_panel_component_' + panel.panel_id" 
      :component_info="panel.component_info"/>
    </div>
</div>
"""

#https://github.com/chyj4747/vue3-golden-layout-virtualcomponent/blob/980fdc1f153671fb81502dc7412e5b3c52c1211d/src/components/Glayout.vue

@VueComponent
class PyriGoldenLayout(PyriVue):

    vue_template = _gl_template

    component_info = vue_prop()

    panels = vue_data(lambda: [])

    def __init__(self):
        super().__init__()
        self._layout = None
        self._on_resize_proxy = None
        self._gl_bounding_client_rect = None

    def mounted(self):
        super().mounted()
        
        layoutContainer = self.refs.goldenlayout_root
        self._layout =js.goldenLayout.VirtualLayout.new(
            layoutContainer,
            create_proxy(self._bind_component_event_listener),
            create_proxy(self._unbind_component_event_listener)
        )
        self._layout.loadLayout(to_js2(_golden_layout_config))


        #self._layout.init()

        #js.jQuery(js.window).resize(create_proxy(lambda _: self._layout.updateSize()))

        self._on_resize_proxy = create_proxy(self._on_resize)
        js.window.addEventListener("resize", self._on_resize_proxy, to_js2({"passive": True}))

        self._layout.beforeVirtualRectingEvent = create_proxy(self._handle_before_virtual_recting_event)

    def before_destroy(self):
        super().before_destroy()

        js.window.removeEventListener("resize", self._on_resize_proxy)
        try:
            self._layout.destroy()
        except:
            pass
        self._layout = None

    def _handle_before_virtual_recting_event(self, count):
        self._gl_bounding_client_rect = getattr(self.vue,"$el").getBoundingClientRect()

    def _on_resize(self, evt):
        try:
            el = getattr(self.vue,"$el")
            width = el.offsetWidth
            height = el.offsetHeight
            self._layout.setSize(width, height)
        except:
            traceback.print_exc()
        
    def _bind_component_event_listener(self, container, item_config):
        
        #el = self.get_panel_pyobj(container.state.panel_id).el

        container.virtualRectingRequiredEvent = create_proxy(self._handle_container_virtual_recting_requiredEvent)
        container.virtualVisibilityChangeRequiredEvent  = create_proxy(self._handle_container_virtual_visibility_change_required_event)
        container.virtualZIndexChangeRequiredEvent = create_proxy(self._handle_container_virtual_z_index_change_required_event)

        return to_js2({"component": {}, "virtual": True })

    def _unbind_component_event_listener(self, container):

        panel_id = container.state.panel_id

        i = self.panels.length - 1
        while i >= 0:
            if self.panels[i].panel_id == panel_id:
                self.panels.splice(i,1)
            i -= 1
        

    def _handle_container_virtual_recting_requiredEvent(self, container, width, height):
        panel_el = self.get_panel_wrapper(container.state.panel_id)

        container_bounding_client_rect = container.element.getBoundingClientRect()
        left = container_bounding_client_rect.left - self._gl_bounding_client_rect.left
        top = container_bounding_client_rect.top - self._gl_bounding_client_rect.top

        panel_el.style.position = "absolute"
        panel_el.style.left = f"{left}px"
        panel_el.style.top = f"{top}px"
        panel_el.style.width = f"{width}px"
        panel_el.style.height = f"{height}px"

    def _handle_container_virtual_visibility_change_required_event(self, container, visible):
        panel_el = self.get_panel_wrapper(container.state.panel_id)

        if visible:
            panel_el.style.display = ""
        else:
            panel_el.style.display = "none"

    def _handle_container_virtual_z_index_change_required_event(self, container, logical_z_index, default_z_index):
        panel_el = self.get_panel_wrapper(container.state.panel_id)
        
        panel_el.style.zIndex = default_z_index
        

    @property
    def layout(self):
        return self._layout

    async def add_panel(self, panel_config: PyriGoldenLayoutPanelConfig, parent_panel_id: str = "root"):

        
        if panel_config.component_type == "stack" or panel_config.component_type == "golden-layout-stack":

            #Currently unsupported to add stack inside stack, ignore so it can be used in the future
            pass
            # stack_component_item_config = {
            #     "type": "stack",
            #     "isClosable": False,
            #     "content": [],
            #     "id": panel_config.panel_id,
            #     "title": panel_config.panel_title
            # }

            # #self._layout.addItem(to_js2(stack_component_item_config))
            # self._layout.root.addItem(to_js2(stack_component_item_config))
        else:

            panels = self.panels

            panels.push(to_js2(panel_config._asdict()))

            await self.next_tick()
            await self.next_tick()

            panel_pyobj = await self.get_panel_pyobj_wait(panel_config.panel_id)

            component_item_config = {
                "type": "component",
                "isClosable": panel_config.closeable,
                "content": [],
                "id": panel_config.panel_id,
                "title": panel_config.panel_title,
                "componentType": panel_config.component_type,
                "componentState": to_js2({"panel_id": panel_config.panel_id})
            }

            # self._layout.addComponent(panel_config.component_type, 
            #     to_js2({"panel_id": panel_config.panel_id}), 
            #     panel_config.panel_title)

            self._layout.addItem(to_js2(component_item_config))

            await self.next_tick()
            await self.next_tick()

            

        #self._layout.root.contentItems[0].addChild(to_js2(panel_config))


    async def select_panel(self, panel_id: str):
        items = self._layout.root.getAllContentItems()
        for i in range(len(items)):
            p = items[i]
            if getattr(p,"id") == panel_id:
                p.parent.setActiveComponentItem(p)

    def get_panel_pyobj(self, panel_id):
        return self.get_ref_pyobj('goldenlayout_vue_panel_component_' + panel_id, 0)

    async def get_panel_pyobj_wait(self, panel_id, timeout = 2.5):
        panel_pyobj = await self.get_ref_pyobj_wait('goldenlayout_vue_panel_component_' + panel_id, index = 0, timeout = timeout)
        if hasattr(panel_pyobj, "wait_core"):
            await panel_pyobj.wait_core(timeout)
        return panel_pyobj

    def get_panel_wrapper(self, panel_id):
        return getattr(self.refs,'goldenlayout_vue_panel_wrapper_' + panel_id)[0]



def register_vue_components():
    vue_register_component("pyri-golden-layout", PyriGoldenLayout)