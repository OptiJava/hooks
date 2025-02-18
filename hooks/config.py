from typing import List, Any, Dict

from mcdreforged.api.all import Serializable


class Configuration(Serializable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    automatically: bool = True
    
    debug: bool = False


class TempConfig:
    
    def __init__(self):
        self.hooks = {
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
        self.task = {}
        self.scripts_list = {}
    
    hooks: Dict[str, List[str]]
    
    task: Dict[str, Any]
    
    scripts_list: Dict[str, str]
    
    schedule_daemon_threads: list = list()
    
    
temp_config: TempConfig

config: Configuration
