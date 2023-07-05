from enum import Enum

from mcdreforged.api.all import CommandSource, PluginServerInterface, RTextMCDRTranslation

from hooks import config as cfg


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
