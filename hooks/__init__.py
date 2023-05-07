import os
from enum import Enum
from io import StringIO
from typing import List, Any

from mcdreforged.api.all import *
from mcdreforged.api.utils import serializer


##################################################################
##################### Basic Function #############################
##################################################################

class Hooks(Enum):
    undefined = 'undefined'
    
    on_plugin_loaded = 'on_plugin_loaded'
    on_plugin_unloaded = 'on_plugin_unloaded'
    
    on_server_starting = 'on_server_starting'
    on_server_started = 'on_server_started'
    on_server_stopped = 'on_server_stopped'
    on_server_crashed = 'on_server_crashed'
    
    on_mcdr_started = 'on_mcdr_started'
    on_mcdr_stopped = 'on_mcdr_stopped'
    
    on_player_joined = 'on_player_joined'
    on_player_left = 'on_player_left'
    
    on_info = 'on_info'
    on_user_info = 'on_user_info'


class TaskType(Enum):
    undefined = 'undefined'
    
    shell_command = 'shell_command'
    server_command = 'server_command'
    mcdr_command = 'mcdr_command'


class Task(Serializable):
    name: str = 'undefined'
    
    task_type: TaskType = TaskType.undefined
    
    command: str = ''
    
    @new_thread('hooks - execute')
    def execute_task(self, server: PluginServerInterface, hook: str, var_dict: dict = None):
        if self.task_type == TaskType.undefined:
            server.logger.error(
                f'Task state is not correct! Task: {self.name} Hooks: {hook} TaskType: {self.task_type} command: {self.command}')
            return
        
        # shell
        if self.task_type == TaskType.shell_command:
            # 生成参数
            command = StringIO()
            
            if var_dict is not None:
                for key in var_dict.keys():
                    command.write('export "')
                    command.write(str(key))
                    command.write('"')
                    command.write('=')
                    command.write('"')
                    command.write(str(var_dict.get(key)))
                    command.write('" && ')
            
            command.write(self.command)
            
            os.system(command.getvalue())
        elif self.task_type == TaskType.server_command:
            # 替换参数
            command = self.command
            
            if var_dict is not None:
                for key in var_dict.keys():
                    command = command.replace('{$' + key + '}', str(var_dict.get(key)))
            
            server.execute(command)
        elif self.task_type == TaskType.mcdr_command:
            # 替换参数
            command = self.command
            
            if var_dict is not None:
                for key in var_dict.keys():
                    command = command.replace('{$' + key + '}', str(var_dict.get(key)))
            
            server.execute_command(self.command)


class Configuration(Serializable):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    automatically: bool = True
    
    hooks: dict[str, List[str]] = {
        'undefined': [],
        
        'on_plugin_loaded': [],
        'on_plugin_unloaded': [],
        
        'on_server_starting': [],
        'on_server_started': [],
        'on_server_stopped': [],
        'on_server_crashed': [],
        'on_mcdr_started': [],
        'on_mcdr_stopped': [],
        
        'on_player_joined': [],
        'on_player_left': [],
        
        'on_info': [],
        'on_user_info': []
    }
    
    task: dict[str, Task] = {}


config: Configuration


@new_thread('hooks - trigger')
def trigger_hooks(hook: Hooks, server: PluginServerInterface, objects_dict: dict[str, Any] = None):
    server.logger.debug(f'Triggered hooks {hook.value}')
    
    finally_var_dict = None
    
    if objects_dict is not None:
        # 初始化最终变量字典
        finally_var_dict = dict()
        
        # 遍历所有已知对象
        for an_object_key in objects_dict.keys():
            
            # 目前正在遍历对象的值
            an_object_value: Any = objects_dict.get(an_object_key)
            
            # 目前正在遍历对象的内部属性字典
            var_inner_attr_dict = serializer.serialize(an_object_value)
            
            if (not hasattr(var_inner_attr_dict, 'keys')) or (var_inner_attr_dict is None):
                finally_var_dict[an_object_key] = an_object_value
                continue
            
            # 正在遍历的对象的属性字典中的正在遍历的key
            for var_inner_attr_key in var_inner_attr_dict.keys():
                # 正在遍历的对象的属性字典中的正在遍历的key的value
                var_inner_attr_value: Any = var_inner_attr_dict.get(var_inner_attr_key)
                
                finally_var_dict[an_object_key + '_' + var_inner_attr_key] = var_inner_attr_value
    
    if config.automatically:
        server.logger.debug(f'Executing hook {hook.value}')
        # 遍历被挂载到此hook的task的key
        for i in config.hooks.get(hook.value):
            server.logger.debug(f'Executing task {i}')
            # 执行任务
            config.task.get(i).execute_task(server, hook.value, finally_var_dict)


##################################################################
######################### For Commands ###########################
##################################################################

@new_thread('hooks - mount')
def mount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hooks_not_exist', hook))
        return
    
    if task in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_already_exist', task))
        return
    
    src.reply(RTextMCDRTranslation('hooks.mount.success', task, hook))
    h.append(task)
    server.logger.info(f'Successfully mounted task {task}')


@new_thread('hooks - unmount')
def unmount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hook_not_exist', hook))
        return
    
    if task not in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', task))
        return
    
    src.reply(RTextMCDRTranslation('hooks.mount.unmount', hook, task))
    h.remove(task)
    server.logger.info(f'Successfully unmounted task {task}')


@new_thread('hooks - create')
def create_task(task_type: str, command: str, name: str, src: CommandSource, server: PluginServerInterface):
    if name in config.task:
        src.reply(RTextMCDRTranslation('hooks.create.already_exist'))
        return
    
    server.logger.info(f'Successfully created task {name}')
    src.reply(RTextMCDRTranslation('hooks.create.success', name))
    
    config.task[name] = Task(name=name, task_type=TaskType(task_type), command=command)


@new_thread('hooks - list')
def list_task(src: CommandSource):
    rtext_list = RTextList()
    
    if len(config.task.values()) == 0:
        rtext_list.append(RText('Nothing', color=RColor.dark_gray, styles=RStyle.italic))
        src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))
        return
    
    for t in config.task.values():
        rtext_list.append(RText(t.name + '  ', color=RColor.red).h(t.task_type.name + ' -> ' + t.command))
    
    src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))


@new_thread('hooks - list')
def list_mount(src: CommandSource):
    src.reply(
        RTextMCDRTranslation('hooks.list.mount',
                             config.hooks.get(Hooks.on_plugin_loaded.value),
                             config.hooks.get(Hooks.on_plugin_unloaded.value),
                             config.hooks.get(Hooks.on_server_starting.value),
                             config.hooks.get(Hooks.on_server_started.value),
                             config.hooks.get(Hooks.on_server_stopped.value),
                             config.hooks.get(Hooks.on_server_crashed.value),
                             config.hooks.get(Hooks.on_mcdr_started.value),
                             config.hooks.get(Hooks.on_mcdr_stopped.value),
                             config.hooks.get(Hooks.on_player_joined.value),
                             config.hooks.get(Hooks.on_player_left.value),
                             config.hooks.get(Hooks.on_info.value),
                             config.hooks.get(Hooks.on_user_info.value),
                             config.hooks.get(Hooks.undefined.value),
                             )
    )


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


##################################################################
############################ Triggers ############################
##################################################################

def on_load(server: PluginServerInterface, old_module):
    global config
    
    config = server.load_config_simple(target_class=Configuration)
    
    server.register_command(
        Literal('!!hooks')
        .then(
            Literal('create')
            .then(
                Text('name')
                .then(
                    Text('task_type')
                    .then(
                        GreedyText('command')
                        .runs(lambda src, ctx: create_task(ctx['task_type'], ctx['command'], ctx['name'], src, server))
                    )
                )
            )
        )
        .then(
            Literal('mount')
            .then(
                Text('task')
                .then(
                    Text('hook')
                    .runs(lambda src, ctx: mount_task(ctx['hook'], ctx['task'], src, server))
                )
            )
        )
        .then(
            Literal('unmount')
            .then(
                Text('task')
                .then(
                    Text('hook')
                    .runs(lambda src, ctx: unmount_task(ctx['hook'], ctx['task'], src, server))
                )
            )
        )
        .then(
            Literal('list')
            .then(
                Literal('task')
                .runs(lambda src: list_task(src))
            )
            .then(
                Literal('mount')
                .runs(lambda src: list_mount(src))
            )
        )
    )
    
    trigger_hooks(Hooks.on_plugin_loaded, server, {'server': process_arg_server(server), 'old_module': old_module})


def on_unload(server: PluginServerInterface):
    trigger_hooks(Hooks.on_plugin_unloaded, server, {'server': process_arg_server(server)})
    
    server.save_config_simple(config)


def on_info(server: PluginServerInterface, info: Info):
    trigger_hooks(Hooks.on_info, server, {'server': process_arg_server(server), 'info': info})


def on_user_info(server: PluginServerInterface, info: Info):
    trigger_hooks(Hooks.on_user_info, server, {'server': process_arg_server(server), 'info': info})


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    trigger_hooks(Hooks.on_player_joined, server, {'server': process_arg_server(server), 'info': info, 'player': player})


def on_player_left(server: PluginServerInterface, player: str):
    trigger_hooks(Hooks.on_player_left, server, {'server': process_arg_server(server), 'player': player})


def on_server_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_server_starting, server, {'server': process_arg_server(server)})


def on_server_startup(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})


def on_server_stop(server: PluginServerInterface, return_code: int):
    if return_code != 0:
        trigger_hooks(Hooks.on_server_crashed, server, {'server': process_arg_server(server), 'return_code': return_code})
    else:
        trigger_hooks(Hooks.on_server_stopped, server, {'server': process_arg_server(server), 'return_code': return_code})


def on_mcdr_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})


def on_mcdr_stop(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_stopped, server, {'server': process_arg_server(server)})
