import json
import os
import time
from enum import Enum
from io import StringIO
from typing import List, Any, Union

from mcdreforged.api.all import *
from mcdreforged.api.utils import serializer
from ruamel import yaml

scripts_folder: str = ''

scripts_list: dict[str, str] = {}


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
        server.logger.debug(f'Executing task: {self.name}, task_type: {self.task_type}, command: {self.command}')
        server.logger.debug(f'objects_dict: {str(var_dict)}')
        
        start_time = time.time()
        
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
        
        server.logger.debug(f'Task finished, name: {self.name}, task_type: {self.task_type}, command: {self.command}, '
                            f'costs {time.time() - start_time} seconds.')


class Configuration(Serializable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    automatically: bool = True


class TempConfig(Serializable):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
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


temp_config: TempConfig = TempConfig()

config: Configuration


def trigger_hooks(hook: Hooks, server: PluginServerInterface, objects_dict: dict[str, Any] = None):
    if not config.automatically:
        return
    
    try:
        server.logger.debug(f'Triggered hooks {hook.value}')
        server.logger.debug(f'objects_dict: {str(objects_dict)}')
        if len(temp_config.hooks.get(hook.value)) != 0:
            _trigger_hooks(hook, server, objects_dict)
    except Exception as e:
        server.logger.exception(f'Unexpected exception when triggering hook {hook.value}', e)


@new_thread('hooks - trigger')
def _trigger_hooks(hook: Hooks, server: PluginServerInterface, objects_dict: dict[str, Any] = None):
    # 初始化最终变量字典
    finally_var_dict = dict()
    
    if (objects_dict is not None) and (len(objects_dict.keys()) != 0):
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
    
    server.logger.debug(f'Executing hook {hook.value}')
    # 遍历被挂载到此hook的task的key
    for task in temp_config.hooks.get(hook.value):
        if temp_config.task.get(task) is None:
            server.logger.warning(f'Task {task} is not exist, unmount it from hook {hook.value}!')
            temp_config.hooks.get(hook.value).remove(task)
            return
        # 执行任务
        try:
            temp_config.task.get(task).execute_task(server, hook.value, finally_var_dict)
        except Exception as e:
            server.logger.exception(
                f'Unexpected exception when executing task {task}, hook {hook.value}, task_type {temp_config.task.get(task).task_type}, command {temp_config.task.get(task).command}',
                e)


def mount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = temp_config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hook_not_exist', hook))
        return
    
    if task in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_already_exist', task))
        return
    
    src.reply(RTextMCDRTranslation('hooks.mount.success', task, hook))
    h.append(task)
    server.logger.info(f'Successfully mounted task {task}')


def unmount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = temp_config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hook_not_exist', hook))
        return
    
    if task not in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', task))
        return
    
    src.reply(RTextMCDRTranslation('hooks.mount.unmount', hook, task))
    h.remove(task)
    server.logger.info(f'Successfully unmounted task {task}')


def create_task(task_type: str, command: str, name: str, src: CommandSource, server: PluginServerInterface):
    if name in temp_config.task:
        src.reply(RTextMCDRTranslation('hooks.create.already_exist'))
        return
    
    try:
        tsk_type = TaskType(task_type)
    except ValueError:
        src.reply(RTextMCDRTranslation('hooks.create.task_type_wrong', task_type))
        return
    
    temp_config.task[name] = Task(name=name, task_type=tsk_type, command=command)
    
    server.logger.info(f'Successfully created task {name}')
    src.reply(RTextMCDRTranslation('hooks.create.success', name))


def delete_task(name: str, src: CommandSource, server: PluginServerInterface):
    if name not in temp_config.task.keys():
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', name))
        return
    
    server.logger.info(f'Successfully deleted task {name}')
    src.reply(RTextMCDRTranslation('hooks.delete.success', name))
    
    temp_config.task.pop(name)


@new_thread('hooks - list')
def list_task(src: CommandSource):
    rtext_list = RTextList()
    
    if len(temp_config.task.values()) == 0:
        rtext_list.append(RText('Nothing', color=RColor.dark_gray, styles=RStyle.italic))
        src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))
        return
    
    for t in temp_config.task.values():
        rtext_list.append(RText(t.name + '  ', color=RColor.red).h(t.task_type.name + ' -> ' + t.command))
    
    src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))


@new_thread('hooks - list')
def list_mount(src: CommandSource):
    src.reply(
        RTextMCDRTranslation('hooks.list.mount',
                             temp_config.hooks.get(Hooks.on_plugin_loaded.value),
                             temp_config.hooks.get(Hooks.on_plugin_unloaded.value),
                             temp_config.hooks.get(Hooks.on_server_starting.value),
                             temp_config.hooks.get(Hooks.on_server_started.value),
                             temp_config.hooks.get(Hooks.on_server_stopped.value),
                             temp_config.hooks.get(Hooks.on_server_crashed.value),
                             temp_config.hooks.get(Hooks.on_mcdr_started.value),
                             temp_config.hooks.get(Hooks.on_mcdr_stopped.value),
                             temp_config.hooks.get(Hooks.on_player_joined.value),
                             temp_config.hooks.get(Hooks.on_player_left.value),
                             temp_config.hooks.get(Hooks.on_info.value),
                             temp_config.hooks.get(Hooks.on_user_info.value),
                             temp_config.hooks.get(Hooks.undefined.value),
                             )
    )


def reload_config(src: CommandSource, server: PluginServerInterface):
    global config, temp_config
    
    temp_config = TempConfig()
    config = server.load_config_simple(target_class=Configuration)
    load_scripts(server)
    server.logger.info('Config reloaded.')
    src.reply(RTextMCDRTranslation('hooks.reload.success'))


def man_run_task(task: str, env_str: str, src: CommandSource, server: PluginServerInterface):
    if task not in temp_config.task.keys():
        src.reply(RTextMCDRTranslation('hooks.man_run.task_not_exist'))
        return
    
    try:
        env_dict: dict[str, str] = dict(json.loads(env_str))
    except Exception as e:
        src.reply(RTextMCDRTranslation('hooks.man_run.illegal_env_json', e))
        return
    
    try:
        temp_config.task.get(task).execute_task(server, Hooks.undefined.value, env_dict)
        src.reply(RTextMCDRTranslation('hooks.man_run.success', task))
    except Exception as e:
        server.logger.exception(
            f'Unexpected exception when executing task {task}, hook {Hooks.undefined.value}, task_type {temp_config.task.get(task).task_type}, command {temp_config.task.get(task).command}',
            e)


def register_scripts(script_path: str):
    # 将绝对路径添加进入script_list
    scripts_list[os.path.basename(script_path)] = script_path


def parse_and_load_scripts(script: str, server: PluginServerInterface):
    # 读取
    with open(scripts_list.get(script), 'r') as f:
        content: dict[str, Union[str, Union[list, dict]]] = yaml.load(f.read(), Loader=yaml.Loader)
    
    for task in content.get('tasks').values():
        # 创建task
        create_task(task.get('task_type'), task.get('command'), task.get('name'), server.get_plugin_command_source(),
                    server)
        for hook in task.get('hooks'):
            # 挂载
            mount_task(hook, task.get('name'), server.get_plugin_command_source(), server)


def load_scripts(server: PluginServerInterface):
    global scripts_list
    
    if not os.path.isdir(scripts_folder):
        # 创建脚本目录
        os.makedirs(scripts_folder)
        return
    
    def list_all_files(root_dir) -> list[str]:
        # 显示一个文件夹及子文件夹中的所有yaml文件
        _files_in_a_folder: list[str] = []
        
        for file in os.listdir(root_dir):
            file_path = os.path.join(root_dir, file)
            
            if os.path.isdir(file_path):
                # 遍历子文件夹
                _files_in_a_folder.extend(list_all_files(file_path))
            if os.path.isfile(file_path) and (file_path.endswith('.yaml') or file_path.endswith('.yml')):
                # 添加文件路径
                _files_in_a_folder.append(file_path)
        
        return _files_in_a_folder
    
    # 遍历所有文件
    for script_path in list_all_files(scripts_folder):
        register_scripts(script_path)
    
    # 遍历所有已成功注册的脚本
    for script in scripts_list.keys():
        parse_and_load_scripts(script, server)


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


def on_load(server: PluginServerInterface, old_module):
    global config, scripts_folder, temp_config
    
    temp_config = TempConfig()
    
    config = server.load_config_simple(target_class=Configuration)
    
    scripts_folder = os.path.join(server.get_data_folder(), 'scripts')
    load_scripts(server)
    
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
            Literal('delete')
            .then(
                Text('task')
                .runs(lambda src, ctx: delete_task(ctx['task'], src, server))
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
        .then(
            Literal('reload')
            .runs(lambda src: reload_config(src, server))
        )
        .then(
            Literal('run')
            .then(
                Text('task')
                .then(
                    GreedyText('env')
                    .runs(lambda src, ctx: man_run_task(ctx['task'], ctx['env'], src, server))
                )
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
    trigger_hooks(Hooks.on_player_joined, server,
                  {'server': process_arg_server(server), 'info': info, 'player': player})


def on_player_left(server: PluginServerInterface, player: str):
    trigger_hooks(Hooks.on_player_left, server, {'server': process_arg_server(server), 'player': player})


def on_server_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_server_starting, server, {'server': process_arg_server(server)})


def on_server_startup(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})


def on_server_stop(server: PluginServerInterface, return_code: int):
    if return_code != 0:
        trigger_hooks(Hooks.on_server_crashed, server,
                      {'server': process_arg_server(server), 'return_code': return_code})
    else:
        trigger_hooks(Hooks.on_server_stopped, server,
                      {'server': process_arg_server(server), 'return_code': return_code})


def on_mcdr_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})


def on_mcdr_stop(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_stopped, server, {'server': process_arg_server(server)})
