import os
import time
from enum import Enum
from io import StringIO

from mcdreforged.api.all import *


class TaskType(Enum):
    undefined = 'undefined'
    
    shell_command = 'shell_command'
    server_command = 'server_command'
    mcdr_command = 'mcdr_command'
    
    python_code = 'python_code'


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
        server.logger.debug(f'Executing task: {self.task_name}, task_type: {self.task_type}, command: {self.command}')
        server.logger.debug(f'objects_dict: {str(var_dict)}')
        
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
        
        server.logger.debug(f'Task finished, name: {self.task_name}, task_type: {self.task_type}, '
                            f'command: {self.command}, costs {time.time() - start_time} seconds.')
