import platform
from typing import Any

from mcdreforged.api.types import PluginServerInterface
from mcdreforged.api.utils.serializer import serialize


def is_windows() -> bool:
    return platform.platform().__contains__('Windows')


def is_int_var(obj: Any) -> bool:
    if type(obj) == int:
        return True
    else:
        try:
            int(str(obj))
        except ValueError:
            return False
        return True


def is_dict_var(obj: Any) -> bool:
    if type(obj) == dict:
        return True
    else:
        try:
            return isinstance(eval(str(obj)), dict)
        except:
            return False


def is_list_var(obj: Any) -> bool:
    if type(obj) == list:
        return True
    else:
        try:
            return isinstance(eval(str(obj)), list)
        except:
            return False


def process_arg_server(server: PluginServerInterface) -> PluginServerInterface:
    server.func_is_server_running = server.is_server_running()
    server.func_is_server_startup = server.is_server_startup()
    server.func_is_rcon_running = server.is_rcon_running()
    server.func_get_server_pid = server.get_server_pid()
    server.func_get_server_pid_all = server.get_server_pid_all()
    server.func_get_server_information = str(serialize(server.get_server_information()))
    server.func_get_data_folder = server.get_data_folder()
    server.func_get_plugin_file_path = server.get_plugin_file_path('hooks')
    server.func_get_plugin_list = str(server.get_plugin_list())
    server.func_get_unloaded_plugin_list = str(server.get_unloaded_plugin_list())
    server.func_get_disabled_plugin_list = str(server.get_disabled_plugin_list())
    server.func_get_mcdr_language = server.get_mcdr_language()
    server.func_get_mcdr_config = str(server.get_mcdr_config())
    return server
