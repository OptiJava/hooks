import os
import time
from enum import Enum
from io import StringIO

from mcdreforged.api.all import CommandSource, PluginServerInterface, RTextMCDRTranslation, new_thread

from hooks import config as cfg, mount as mount, schedule_tasks as schedule_tasks
import hooks.logger.logger as logger


class TaskType(Enum):
    undefined = 'undefined'
    
    shell_command = 'shell_command'
    server_command = 'server_command'
    mcdr_command = 'mcdr_command'
    
    python_code = 'python_code'


class Task:
    def __init__(self, name, task_type, created_by, command):
        self.task_name = name
        self.task_type = task_type
        self.created_by = created_by
        self.command = command
    
    task_name: str = 'undefined'
    
    task_type: TaskType = TaskType.undefined
    
    created_by: str = 'undefined'
    
    command: str = ''
    
    @new_thread('hooks - execute')
    def execute_task(self, server: PluginServerInterface, hook: str, var_dict: dict = None, obj_dict: dict = None):
        logger.debug(f'Executing task: {self.task_name}, task_type: {self.task_type}', server)
        
        start_time = time.time()
        
        if self.command is None:
            server.logger.error(
                f'Task state is not correct! Task: {self.task_name} Hooks: {hook} TaskType: {self.task_type} '
                f'command: {self.command}')
            return
        
        if self.task_type == TaskType.undefined:
            server.logger.error(
                f'Task state is not correct! Task: {self.task_name} Hooks: {hook} TaskType: {self.task_type} '
                f'command: {self.command}')
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
        # mc command
        elif self.task_type == TaskType.server_command:
            # 替换参数
            command = self.command
            if var_dict is not None:
                for key in var_dict.keys():
                    command = command.replace('{$' + key + '}', str(var_dict.get(key)))
            
            server.execute(command)
        # mcdr command
        elif self.task_type == TaskType.mcdr_command:
            # 替换参数
            command = self.command
            if var_dict is not None:
                for key in var_dict.keys():
                    command = command.replace('{$' + key + '}', str(var_dict.get(key)))
            
            server.execute_command(command)
        
        # python code
        elif self.task_type == TaskType.python_code:
            if obj_dict is not None:
                exec(self.command, {}, obj_dict)
            else:
                if var_dict is not None:
                    exec(self.command, {}, var_dict)
                else:
                    exec(self.command, {}, locals())
        
        logger.debug(f'Task finished, name: {self.task_name}, task_type: {self.task_type}, '
                     f'costs {time.time() - start_time} seconds.', server)


def create_task(task_type: str, command: str, name: str, src: CommandSource, server: PluginServerInterface,
                is_schedule=False, exec_interval=0, created_by=None):
    if name in cfg.temp_config.task:
        src.reply(RTextMCDRTranslation('hooks.create.already_exist'))
        return
    
    if name is None or len(name) == 0:
        return
    
    try:
        tsk_type = TaskType(task_type)
    except ValueError:
        src.reply(RTextMCDRTranslation('hooks.create.task_type_wrong', task_type))
        return
    
    if created_by is None:
        created_by = str(src)
    
    if not is_schedule:
        cfg.temp_config.task[name] = Task(name=name, task_type=tsk_type, command=command, created_by=created_by)
    else:
        if exec_interval <= 0:
            src.reply(RTextMCDRTranslation('hooks.create.exec_interval_invalid', exec_interval))
            return
        var1 = schedule_tasks.ScheduleTask(name=name, task_type=tsk_type, command=command, created_by=created_by,
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
                mount.unmount_task(hook, name, src, server)
    
    var1 = cfg.temp_config.task.get(name)
    if isinstance(var1, schedule_tasks.ScheduleTask):
        var1.break_thread()
        cfg.temp_config.schedule_daemon_threads.remove(var1)
    
    cfg.temp_config.task.pop(name)
    
    server.logger.info(f'Successfully deleted task {name}')
    src.reply(RTextMCDRTranslation('hooks.delete.success', name))
