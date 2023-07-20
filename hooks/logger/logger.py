from mcdreforged.api.types import PluginServerInterface

import hooks.config as cfg


def debug(msg: str, server: PluginServerInterface):
    if cfg.config.debug:
        server.logger.info('[debug] ' + msg)
