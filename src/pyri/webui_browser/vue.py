import asyncio
from mimetypes import init
from typing import Dict, Any, Callable, Union
import js

from pyodide.ffi import create_once_callable, create_proxy, to_js
import inspect
import traceback
import sys
import time

def to_js2(val):
    return to_js(val,dict_converter=js.Object.fromEntries)

_wrap_js_this = js.Function.new("fn", "return (function (...args) { return fn(this,...args); })")

def vue_method(fn = None, *, vue_method_name = None):
    assert fn or vue_method_name
    if fn:
        fn._vue_method = fn.__name__
        return fn
    else:
        def _vue_method_inner(fn):
            fn._vue_method = vue_method_name
            return fn
        return _vue_method_inner

def vue_computed(fn = None, *, vue_computed_name = None):
    assert fn or vue_computed_name
    if fn:
        fn._vue_computed = fn.__name__
        return fn
    else:
        def _vue_computed_inner(fn):
            fn._vue_computed = vue_computed_name
            return fn
        return _vue_computed_inner
    

def vue_watch(vue_watch_property, vue_watch_deep = None, vue_watch_immediate = None, vue_watch_flush = None):
    def vue_watch_inner(fn):
        fn._vue_watch_property = vue_watch_property
        if vue_watch_deep is not None:
            fn._vue_watch_deep = vue_watch_deep
        if vue_watch_immediate is not None:
            fn._vue_watch_immediate = vue_watch_immediate
        if vue_watch_flush is not None:
            fn._vue_watch_flush = vue_watch_flush
        return fn
    return vue_watch_inner

class vue_data():
    def __init__(self, init_value = None):
        self._vue_data = None
        self._init_value = init_value

    def __get__(self, instance, owner = None):
        if instance is None:
            return self
        return instance._vue_get_data(self._vue_data)

    def __set__(self, instance, value):
        instance._vue_set_data(self._vue_data, value)

    def __delete__(self, instance):
        return

class vue_prop():
    def __init__(self):
        self._vue_prop = None

    def __get__(self, instance, owner = None):
        if instance is None:
            return self
        return instance._vue_get_prop(self._vue_prop)

    def __set__(self, instance, value):
        raise AttributeError("Props are read only")

    def __delete__(self, instance):
        raise AttributeError("Props are read only")

def _vue_method_proxy(fn):

    def run_method(js_this, *args):
        py_obj = getattr(js_this,"$data").py_obj
        if py_obj is None:
            return None
        res = fn(py_obj,*args)
        if inspect.isawaitable(res):
            async def run_async_method():
                try:
                    await res
                except BaseException as exp:
                    py_obj._vue_handle_async_exception(exp)
            py_obj._vue_create_task(run_async_method())
            return None
        else:
            return res


    return _wrap_js_this(create_proxy(run_method))

def _vue_get_methods(vue_class: type):
    methods = {}
    for a in dir(vue_class):
        a1 = getattr(vue_class, a)
        if hasattr(a1,"_vue_method"):
            methods[a1._vue_method] = _vue_method_proxy(a1)
    return methods

def _vue_get_data(vue_class: type):
    data = {}
    for a in dir(vue_class):
        a1 = getattr(vue_class, a)
        if hasattr(a1,"_vue_data"):
            a1._vue_data = a
            data[a1._vue_data] = a1
    def _new_data(*args):
        ret = {}
        for k,v in data.items():
            if inspect.isfunction(v._init_value):
                init_value_arg_spec = inspect.getfullargspec(v._init_value)
                if init_value_arg_spec.varargs is not None:
                    ret[k] = v._init_value(*args)
                elif len(init_value_arg_spec.args) > 0:
                    ret[k] = v._init_value(*(args[0:len(init_value_arg_spec.args)]))
                else:
                     ret[k] = v._init_value()                
            else:
                ret[k] = v._init_value
        ret["py_obj"] = None
        return to_js2(ret)
    return _new_data

def _vue_get_props(vue_class: type):
    props = []
    for a in dir(vue_class):
        a1 = getattr(vue_class, a)
        if hasattr(a1,"_vue_prop"):
            a1._vue_prop = a
            props.append(a)
    return props

def _vue_get_computed(vue_class: type):
    methods = {}
    for a in dir(vue_class):
        a1 = getattr(vue_class, a)
        if hasattr(a1,"_vue_computed"):
            methods[a1._vue_computed] = _vue_method_proxy(a1)
    return methods

def _vue_get_watch(vue_class: type):
    watch = {}
    for a in dir(vue_class):
        a1 = getattr(vue_class, a)
        if hasattr(a1,"_vue_watch_property"):
            w = { "handler": _vue_method_proxy(a1) }
            if hasattr(a1,"_vue_watch_deep"):
                w["deep"] = a1._vue_watch_deep
            if hasattr(a1,"_vue_watch_immediate"):
                w["immediate"] = a1._vue_watch_immediate
            if hasattr(a1,"_vue_watch_flush"):
                w["flush"] = a1._vue_watch_flush
            watch[a1._vue_watch_property] = w
    return watch


class Vue:
    def __init__(self, el: Union["js.JsProxy",str] = None):
        self._mounted = False
        self._mount_futures = []
        if self._vue_class is None:
            vue_methods = _vue_get_methods(type(self))
            vue_data = _vue_get_data(type(self))
            vue_computed = _vue_get_computed(type(self))
            vue_watch = _vue_get_watch(type(self))            

            components = type(self).vue_components

            components_vue = {k: v._vue_class for k,v in components.items()}

            vue_options = {
                    "el": el,
                    "components": to_js2(components_vue),
                    "data": to_js2(vue_data),
                    "methods": to_js2(vue_methods),
                    "created": _vue_method_proxy(type(self).before_mount),
                    "beforeMount": _vue_method_proxy(type(self).before_mount),
                    "mounted": _vue_method_proxy(type(self).mounted),
                    "beforeDestray": _vue_method_proxy(type(self).before_destroy),
                    "computed": to_js2(vue_computed),
                    "watch": to_js2(vue_watch)
                }

            vue_template = getattr(type(self), "vue_template", None)
            if vue_template:
                vue_options["template"] = vue_template

            self._vue = js.Vue.new(to_js2(vue_options))

            getattr(self.vue,"$data").py_obj = self

    @property
    def vue(self):
        return self._vue

    def destroy(self):
        self.vue.destroy()

    def _vue_get_data(self, data_name):
        return getattr(getattr(self.vue, "$data"),data_name)

    def _vue_set_data(self, data_name, value):
        return setattr(getattr(self.vue, "$data"),data_name,value)

    def _vue_get_prop(self, prop_name):
        return getattr(getattr(self.vue, "$props"),prop_name)

    def _vue_set_prop(self, prop_name, value):
        return setattr(getattr(self.vue, "$props"),prop_name,value)

    def _vue_create_task(self, task):
        loop = asyncio.get_event_loop()
        return loop.create_task(task)

    def _vue_handle_async_exception(self, exp):
        print(f"Uncaught exception in async task: {traceback.format_exception(exp)}", file=sys.stderr)

    _vue_class = None

    def created(self):
        pass

    def before_mount(self):
        pass

    def mounted(self):
        for f in self._mount_futures:
            try:
                asyncio.get_event_loop().call_soon(lambda: f.set_result(None))
            except: 
                traceback.print_exc()

    def before_destroy(self):
        pass

    @property
    def emit(self):
        return getattr(self.vue,"$emit")

    @property
    def on(self):
        return getattr(self.vue,"$on")

    @property
    def refs(self):
        return getattr(self.vue,"$refs")

    def get_ref_pyobj(self, ref_name, index = None):
        ref1 = getattr(self.refs,ref_name)
        if index is not None:
            ref1 = ref1[index]
        return getattr(ref1,"$data").py_obj

    async def get_ref_pyobj_wait(self, ref_name, index = None, timeout = 2.5):
        t1 = time.time()

        while True:
            if time.time() - t1 > timeout:
                raise TimeoutError(f"Timed out waiting for component {ref_name} to mount")

            try:
                return self.get_ref_pyobj(ref_name, index)
            except AttributeError:
                #traceback.print_exc()
                pass

            await self.next_tick()

    @property
    def bv_modal(self):
        return getattr(self.vue,"$bvModal")

    def next_tick(self):
        return getattr(self.vue,"$nextTick")()

    @property
    def watch(self):
        return getattr(self.vue,"$watch")

    @property
    def el(self):
        return getattr(self.vue, "$el")

    vue_template = None

    vue_components = {}

    async def wait_mounted(self, timeout = 2.5):

        if self._mounted:
            return
        
        f = asyncio.Future()
        try:
            self._mount_futures.append(f)
            await asyncio.wait_for(f,timeout)
        finally:
            self._mount_futures.remove(f)


def VueComponent(vue_py_class):
    vue_methods = _vue_get_methods(vue_py_class)
    vue_data = _vue_get_data(vue_py_class)
    vue_props = _vue_get_props(vue_py_class)
    vue_computed = _vue_get_computed(vue_py_class)
    vue_watch = _vue_get_watch(vue_py_class)

    components = vue_py_class.vue_components

    vue_components = dict()
    for k,v in components.items():
        if hasattr(v, "_vue_class"):
            vue_components[k] = v._vue_class
        else:
            vue_components[k] = v
    
    def component_created(js_this):
        py_obj = vue_py_class()
        py_obj._vue = js_this
        getattr(js_this,"$data").py_obj = py_obj        
        py_obj.created()

    vue_py_class._vue_class = js.Vue.extend(to_js2(
        {
            "template": vue_py_class.vue_template,
            "data": to_js2(vue_data),
            "methods": to_js2(vue_methods),
            "props": to_js2(vue_props),
            "created": _wrap_js_this(create_proxy(component_created)),
            "beforeMount": _vue_method_proxy(vue_py_class.before_mount),
            "mounted": _vue_method_proxy(vue_py_class.mounted),
            "beforeDestroy": _vue_method_proxy(vue_py_class.before_destroy),
            "computed": to_js2(vue_computed),
            "components": to_js2(vue_components),
            "watch": to_js2(vue_watch)
            
        })
    )

    return vue_py_class


def vue_register_component(component_name, component_type):
    js.Vue.component(component_name, component_type._vue_class)