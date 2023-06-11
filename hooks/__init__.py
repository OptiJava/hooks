import json
import os
from typing import Union, Any

from ruamel import yaml

from mcdreforged.api.all import *

import hooks.config as cfg
import hooks.schedule_task as schedule_task
import hooks.tasks as tasks
import hooks.utils as utils
from hooks.utils import process_arg_server

scripts_folder: str = ''


def stop_all_schedule_daemon_threads():
    if len(cfg.temp_config.schedule_daemon_threads) == 0:
        return
    
    for thr in cfg.temp_config.schedule_daemon_threads:
        thr.break_thread()
        cfg.temp_config.schedule_daemon_threads.remove(thr)


def trigger_hooks(hook: tasks.Hooks, server: PluginServerInterface, objects_dict: dict[str, Any] = None):
    if not cfg.config.automatically:
        return
    
    try:
        server.logger.debug(f'Triggered hooks {hook.value}')
        server.logger.debug(f'objects_dict: {str(objects_dict)}')
        if len(cfg.temp_config.hooks.get(hook.value)) != 0:
            _trigger_hooks(hook, server, objects_dict)
    except Exception as e:
        server.logger.exception(f'Unexpected exception when triggering hook {hook.value}', e)


@new_thread('hooks - trigger')
def _trigger_hooks(hook: tasks.Hooks, server: PluginServerInterface, objects_dict: dict[str, Any] = None):
    # 初始化最终变量字典
    finally_var_dict = dict()
    
    if (objects_dict is not None) and (len(objects_dict.keys()) != 0):
        # 遍历所有已知对象
        for an_object_key in objects_dict.keys():
            # 目前正在遍历对象的值
            an_object_value: Any = objects_dict.get(an_object_key)
            # 目前正在遍历对象的内部属性字典
            var_inner_attr_dict = serialize(an_object_value)
            # 判断var_inner_attr_dict是否为基本类型
            if (not hasattr(var_inner_attr_dict, 'keys')) or (var_inner_attr_dict is None):
                finally_var_dict[an_object_key] = an_object_value
                continue
            
            # 正在遍历的对象的属性字典中的正在遍历的key
            for var_inner_attr_key in var_inner_attr_dict.keys():
                # 正在遍历的对象的属性字典中的正在遍历的key的value
                var_inner_attr_value: Any = var_inner_attr_dict.get(var_inner_attr_key)
                # 整合进入finally_var_dict
                finally_var_dict[an_object_key + '_' + var_inner_attr_key] = var_inner_attr_value
    
    # 遍历被挂载到此hook的task的key
    for task in cfg.temp_config.hooks.get(hook.value):
        if cfg.temp_config.task.get(task) is None:
            server.logger.warning(f'Task {task} is not exist, unmount it from hook {hook.value}!')
            cfg.temp_config.hooks.get(hook.value).remove(task)
            return
        # 执行任务
        try:
            cfg.temp_config.task.get(task).execute_task(server, hook.value, finally_var_dict, obj_dict=objects_dict)
        except Exception as e:
            server.logger.exception(
                f'Unexpected exception when executing task {task}, hook {hook.value}, '
                f'task_type {cfg.temp_config.task.get(task).task_type}, '
                f'command {cfg.temp_config.task.get(task).command}',
                e)


def mount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = cfg.temp_config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hook_not_exist', hook))
        return
    
    if task in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_already_exist', task, hook))
        return
    
    h.append(task)
    server.logger.info(f'Successfully mounted task {task}')
    src.reply(RTextMCDRTranslation('hooks.mount.success', task, hook))


def unmount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = cfg.temp_config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hook_not_exist', hook))
        return
    
    if task not in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', task))
        return
    
    h.remove(task)
    server.logger.info(f'Successfully unmounted task {task}')
    src.reply(RTextMCDRTranslation('hooks.mount.unmount', hook, task))


def create_task(task_type: str, command: str, name: str, src: CommandSource, server: PluginServerInterface,
                is_schedule=False, exec_interval=0, created_by=None):
    if name in cfg.temp_config.task:
        src.reply(RTextMCDRTranslation('hooks.create.already_exist'))
        return
    
    if name is None or len(name) == 0:
        return
    
    try:
        tsk_type = tasks.TaskType(task_type)
    except ValueError:
        src.reply(RTextMCDRTranslation('hooks.create.task_type_wrong', task_type))
        return
    
    if created_by is None:
        created_by = str(src)
    
    if not is_schedule:
        cfg.temp_config.task[name] = tasks.Task(name=name, task_type=tsk_type, command=command, created_by=created_by)
    else:
        var1 = schedule_task.ScheduleTask(name=name, task_type=tsk_type, command=command, created_by=created_by,
                                          server_inst=server, exec_interval=exec_interval)
        cfg.temp_config.task[name] = var1
        var1.start()
    
    server.logger.info(f'Successfully created task {name}')
    src.reply(RTextMCDRTranslation('hooks.create.success', name))


def delete_task(name: str, src: CommandSource, server: PluginServerInterface):
    if name not in cfg.temp_config.task.keys():
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', name))
        return
    
    for hook in cfg.temp_config.hooks.keys():
        for tasks_in_hook in cfg.temp_config.hooks.get(hook):
            if tasks_in_hook == name:
                unmount_task(hook, name, src, server)
    
    var1 = cfg.temp_config.task.get(name)
    if isinstance(var1, schedule_task.ScheduleTask):
        var1.break_thread()
        cfg.temp_config.schedule_daemon_threads.remove(var1)
    
    cfg.temp_config.task.pop(name)
    
    server.logger.info(f'Successfully deleted task {name}')
    src.reply(RTextMCDRTranslation('hooks.delete.success', name))


@new_thread('hooks - list')
def list_task(src: CommandSource):
    rtext_list = RTextList()
    
    if len(cfg.temp_config.task.values()) == 0:
        rtext_list.append(RText('Nothing', color=RColor.dark_gray, styles=RStyle.italic))
        src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))
        return
    
    for t in cfg.temp_config.task.values():
        rtext_list.append(RTextList(
            RText('\n  '),
            RText(t.task_name, color=RColor.red).h(t.task_type.name),
            RText(f'  created by: "{t.created_by}"', color=RColor.green)
        ))
    src.reply(RTextMCDRTranslation('hooks.list.task', rtext_list))


@new_thread('hooks - list')
def list_mount(src: CommandSource):
    list_hooks: list = list()
    
    for hk in dict(tasks.Hooks.__members__).keys():
        list_hooks.append(str(cfg.temp_config.hooks.get(str(hk))))
    
    src.reply(RTextMCDRTranslation('hooks.list.mount', *list_hooks))


@new_thread('hooks - list')
def list_scripts(src: CommandSource):
    rtext_list = RTextList()
    
    for scr in cfg.temp_config.scripts_list.keys():
        rtext_list.append(RText(scr + '  ', color=RColor.red).h(cfg.temp_config.scripts_list.get(scr)))
    
    if rtext_list.is_empty():
        rtext_list.append(RText('Nothing', color=RColor.dark_gray, styles=RStyle.italic))
    
    src.reply(RTextMCDRTranslation('hooks.list.script', rtext_list))


def reload_config(src: CommandSource, server: PluginServerInterface):
    stop_all_schedule_daemon_threads()
    
    cfg.temp_config = cfg.TempConfig()
    cfg.config = server.load_config_simple(target_class=cfg.Configuration)
    
    load_scripts(server)
    server.logger.info('Config reloaded.')
    src.reply(RTextMCDRTranslation('hooks.reload.success'))


def man_run_task(task: str, env_str: str, src: CommandSource, server: PluginServerInterface):
    if task not in cfg.temp_config.task.keys():
        src.reply(RTextMCDRTranslation('hooks.man_run.task_not_exist'))
        return
    
    try:
        env_dict: dict[str, str] = dict(json.loads(env_str))
    except Exception as e:
        src.reply(RTextMCDRTranslation('hooks.man_run.illegal_env_json', e))
        return
    
    try:
        cfg.temp_config.task.get(task).execute_task(server, tasks.Hooks.undefined.value, var_dict=env_dict,
                                                    obj_dict=env_dict)
        src.reply(RTextMCDRTranslation('hooks.man_run.success', task))
    except Exception as e:
        server.logger.exception(
            f'Unexpected exception when executing task {task}, hook {tasks.Hooks.undefined.value}, '
            f'task_type {cfg.temp_config.task.get(task).task_type}, command {cfg.temp_config.task.get(task).command}',
            e)


def _parse_and_apply_scripts(script: str, server: PluginServerInterface):
    try:
        # 读取
        with open(cfg.temp_config.scripts_list.get(script), 'r') as f:
            content: dict[str, Union[str, Union[list, dict]]] = yaml.load(f.read(), Loader=yaml.Loader)
        
        if content is not None:
            if content.get('tasks') is not None:
                for task in content.get('tasks'):
                    use_cmd_file: bool = False
                    cmd_file_path: str = ''
                    
                    if task.get('command_file') is not None:
                        var1 = str(task.get('command_file')).replace('{hooks_config_path}', server.get_data_folder())
                        
                        if os.path.isfile(var1):
                            cmd_file_path = var1
                            use_cmd_file = True
                        else:
                            server.logger.warning(
                                f'Script path for task {task.get("name")} is invalid, use command instead! '
                                f'{task.get("command_file")}')
                    
                    if use_cmd_file:
                        # 读取
                        with open(cmd_file_path, 'r') as command_file:
                            command_file_content = command_file.read()
                        # 创建task
                        create_task(task.get('task_type'), command_file_content, task.get('name'),
                                    server.get_plugin_command_source(),
                                    server, created_by=script)
                    else:
                        # 创建task
                        create_task(task.get('task_type'), task.get('command'), task.get('name'),
                                    server.get_plugin_command_source(),
                                    server, created_by=script)
                    
                    if task.get('hooks') is None:
                        continue
                    for hook in task.get('hooks'):
                        # 挂载
                        mount_task(hook, task.get('name'), server.get_plugin_command_source(), server)
            
            if content.get('schedule_tasks') is not None:
                for schedule in content.get('schedule_tasks'):
                    use_cmd_file: bool = False
                    cmd_file_path: str = ''
                    
                    if int(schedule.get('exec_interval')) <= 0:
                        server.logger.warning(f'Invalid exec_interval in schedule task {schedule.get("name")}!')
                    
                    if schedule.get('command_file') is not None:
                        var1 = str(schedule.get('command_file')).replace('{hooks_config_path}',
                                                                         server.get_data_folder())
                        
                        if os.path.isfile(var1):
                            cmd_file_path = var1
                            use_cmd_file = True
                        else:
                            server.logger.warning(
                                f'Script path for task {schedule.get("name")} is invalid, use command instead! '
                                f'{schedule.get("command_file")}')
                    
                    if use_cmd_file:
                        with open(cmd_file_path, 'r') as command_file:
                            command_file_content = command_file.read()
                        # 创建task
                        create_task(schedule.get('task_type'), command_file_content, schedule.get('name'),
                                    server.get_plugin_command_source(),
                                    server, created_by=script, is_schedule=True,
                                    exec_interval=schedule.get('exec_interval'))
                    else:
                        # 创建task
                        create_task(schedule.get('task_type'), schedule.get('command'), schedule.get('name'),
                                    server.get_plugin_command_source(),
                                    server, created_by=script, is_schedule=True,
                                    exec_interval=schedule.get('exec_interval'))
                    
                    if schedule.get('hooks') is None:
                        continue
                    for hook in schedule.get('hooks'):
                        # 挂载
                        mount_task(hook, schedule.get('name'), server.get_plugin_command_source(), server)
    except Exception as e:
        server.logger.exception(f'Unexpected exception when parse or apply scripts {os.path.basename(script)}! Please '
                                f'check your scripts.', e)


def load_scripts(server: PluginServerInterface):
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
    
    # 遍历所有yaml文件
    for script_path in list_all_files(scripts_folder):
        # key：文件名    value：文件路径
        cfg.temp_config.scripts_list[os.path.basename(script_path)] = script_path
    
    # 遍历所有已成功注册的脚本
    for script in cfg.temp_config.scripts_list.keys():
        _parse_and_apply_scripts(script, server)


def on_load(server: PluginServerInterface, old_module):
    global scripts_folder
    
    cfg.temp_config = cfg.TempConfig()
    cfg.config = server.load_config_simple(target_class=cfg.Configuration)
    
    scripts_folder = os.path.join(server.get_data_folder(), 'scripts')
    load_scripts(server)
    
    if utils.is_windows():
        server.logger.warning('!###################################################################################!')
        server.logger.warning('Some features of hooks plugin cannot be run on Windows, you have already been warned.')
        server.logger.warning('!###################################################################################!')
    
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
                        .requires(lambda src: src.has_permission(3))
                        .runs(lambda src, ctx: create_task(ctx['task_type'], ctx['command'], ctx['name'], src, server))
                    )
                )
            )
        )
        .then(
            Literal('schedule')
            .then(
                Text('name')
                .then(
                    Integer('exec_interval')
                    .then(
                        Text('task_type')
                        .then(
                            GreedyText('command')
                            .requires(lambda src: src.has_permission(3))
                            .runs(lambda src, ctx: create_task(ctx['task_type'], ctx['command'], ctx['name'], src,
                                                               server, is_schedule=True,
                                                               exec_interval=ctx['exec_interval']))
                        )
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
                    .requires(lambda src: src.has_permission(3))
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
                    .requires(lambda src: src.has_permission(3))
                    .runs(lambda src, ctx: unmount_task(ctx['hook'], ctx['task'], src, server))
                )
            )
        )
        .then(
            Literal('delete')
            .then(
                Text('task')
                .requires(lambda src: src.has_permission(3))
                .runs(lambda src, ctx: delete_task(ctx['task'], src, server))
            )
        )
        .then(
            Literal('list')
            .then(
                Literal('task')
                .requires(lambda src: src.has_permission(3))
                .runs(lambda src: list_task(src))
            )
            .then(
                Literal('mount')
                .requires(lambda src: src.has_permission(3))
                .runs(lambda src: list_mount(src))
            )
            .then(
                Literal('scripts')
                .requires(lambda src: src.has_permission(3))
                .runs(lambda src: list_scripts(src))
            )
        )
        .then(
            Literal('reload')
            .requires(lambda src: src.has_permission(3))
            .runs(lambda src: reload_config(src, server))
        )
        .then(
            Literal('run')
            .then(
                Text('task')
                .then(
                    GreedyText('env')
                    .requires(lambda src: src.has_permission(3))
                    .runs(lambda src, ctx: man_run_task(ctx['task'], ctx['env'], src, server))
                )
            )
        )
    )
    
    trigger_hooks(tasks.Hooks.on_plugin_loaded, server,
                  {'server': process_arg_server(server), 'old_module': old_module})


def on_unload(server: PluginServerInterface):
    stop_all_schedule_daemon_threads()
    
    trigger_hooks(tasks.Hooks.on_plugin_unloaded, server, {'server': process_arg_server(server)})
    
    server.save_config_simple(cfg.config)


def on_info(server: PluginServerInterface, info: Info):
    trigger_hooks(tasks.Hooks.on_info, server, {'server': process_arg_server(server), 'info': info})


def on_user_info(server: PluginServerInterface, info: Info):
    trigger_hooks(tasks.Hooks.on_user_info, server, {'server': process_arg_server(server), 'info': info})


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    trigger_hooks(tasks.Hooks.on_player_joined, server,
                  {'server': process_arg_server(server), 'info': info, 'player': player})


def on_player_left(server: PluginServerInterface, player: str):
    trigger_hooks(tasks.Hooks.on_player_left, server, {'server': process_arg_server(server), 'player': player})


def on_server_start(server: PluginServerInterface):
    trigger_hooks(tasks.Hooks.on_server_starting, server, {'server': process_arg_server(server)})


def on_server_startup(server: PluginServerInterface):
    trigger_hooks(tasks.Hooks.on_server_started, server, {'server': process_arg_server(server)})


def on_server_stop(server: PluginServerInterface, return_code: int):
    if return_code != 0:
        trigger_hooks(tasks.Hooks.on_server_crashed, server,
                      {'server': process_arg_server(server), 'return_code': return_code})
    else:
        trigger_hooks(tasks.Hooks.on_server_stopped, server,
                      {'server': process_arg_server(server), 'return_code': return_code})


def on_mcdr_start(server: PluginServerInterface):
    trigger_hooks(tasks.Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})


def on_mcdr_stop(server: PluginServerInterface):
    trigger_hooks(tasks.Hooks.on_mcdr_stopped, server, {'server': process_arg_server(server)})
