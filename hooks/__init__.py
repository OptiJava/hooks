import os
from enum import Enum
from typing import Dict, List

from mcdreforged.api.all import *


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
    

class Task:
    name: str = 'undefined'
    
    task_type: TaskType = TaskType.undefined
    
    command: str = ''
    
    def __init__(self, name: str, task_type: TaskType, command: str):
        self.name = name
        self.task_type = task_type
        self.command = command
    
    @new_thread('hooks - execute')
    def execute_task(self, server: PluginServerInterface, hook: str):
        if self.task_type == TaskType.undefined:
            server.logger.error(f'Task state is not correct! Task: {self.name} Hooks: {hook} TaskType: {self.task_type} command: {self.command}')
            return
        
        if self.task_type == TaskType.shell_command:
            os.system(self.command)
        elif self.task_type == TaskType.server_command:
            server.execute(self.command)
        elif self.task_type == TaskType.mcdr_command:
            server.execute_command(self.command)


class Configuration(Serializable):
    automatically: bool = True
    
    hooks: Dict[str, List[str]] = {
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
    
    task: Dict[str, Task] = {}


config: Configuration

def trigger_hooks(hook: Hooks, server: PluginServerInterface):
    server.logger.debug(f'Triggered hooks {hook.value}')
    
    if config.automatically:
        for i in config.hooks.get(hook.value):
            server.logger.debug(f'Executing task {i}')
            config.task.get(i).execute_task(server, hook.value)
            
            
##################################################################
######################### For Commands ###########################
##################################################################
            
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
    
    
def unmount_task(hook: str, task: str, src: CommandSource, server: PluginServerInterface):
    h = config.hooks.get(hook)
    
    if h is None:
        src.reply(RTextMCDRTranslation('hooks.mount.hooks_not_exist', hook))
        return
    
    if task not in h:
        src.reply(RTextMCDRTranslation('hooks.mount.task_not_exist', task))
        return

    src.reply(RTextMCDRTranslation('hooks.mount.unmount', hook, task))
    h.remove(task)
    
    
def create_task(task_type: str, command: str, name: str, src: CommandSource, server: PluginServerInterface):
    if name in config.task:
        src.reply(RTextMCDRTranslation('hooks.create.already_exist'))
        return
    
    server.logger.info(server.rtr('hooks.create.success', name))
    src.reply(RTextMCDRTranslation('hooks.create.success', name))

    config.task[name] = Task(name, TaskType(task_type), command)
    

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
    )
    
    trigger_hooks(Hooks.on_plugin_loaded, server)
    
    
def on_unload(server: PluginServerInterface):
    trigger_hooks(Hooks.on_plugin_unloaded, server)
    
    server.save_config_simple(config)
    
    
def on_info(server: PluginServerInterface, info: Info):
    trigger_hooks(Hooks.on_info, server)
    
    
def on_user_info(server: PluginServerInterface, info: Info):
    trigger_hooks(Hooks.on_user_info, server)
    

def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    trigger_hooks(Hooks.on_player_joined, server)
    
    
def on_player_left(server: PluginServerInterface, player: str):
    trigger_hooks(Hooks.on_player_left, server)
    
    
def on_server_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_server_starting, server)
    
    
def on_server_startup(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server)
    
    
def on_server_stop(server: PluginServerInterface, return_code: int):
    if return_code != 0:
        trigger_hooks(Hooks.on_server_crashed, server)
    else:
        trigger_hooks(Hooks.on_server_stopped, server)

def on_mcdr_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server)
    
    
def on_mcdr_stop(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_stopped, server)