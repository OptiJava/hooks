import threading
from time import sleep

import hooks.tasks as tasks
from hooks import config as cfg
import hooks.logger.logger as logger


class AThread(threading.Thread):
    def init_thread(self):
        super().__init__(daemon=True)
    
    def set_thread_name(self, name: str):
        self.name = name


class ScheduleTask(tasks.Task, AThread):
    def __init__(self, name, task_type, created_by, command, server_inst, exec_interval):
        super().__init__(name, task_type, created_by, command)
        self.server_inst = server_inst
        self.exec_interval = exec_interval
        self.stop_event = threading.Event()
        super().init_thread()
        super(tasks.Task, self).set_thread_name(f'hooks - schedule_task_daemon({name})')
        cfg.temp_config.schedule_daemon_threads.append(self)
    
    def break_thread(self):
        self.stop_event.set()
    
    def run(self):
        if self.exec_interval <= 0:
            self.server_inst.logger.warning(
                f'Schedule task {self.task_name} has illegal exec_interval: {self.exec_interval}')
            return
        
        while True:
            for _ in range(self.exec_interval):
                if self.stop_event.is_set():
                    logger.debug(f'Schedule task {self.task_name} stopped.', self.server_inst)
                    return
                sleep(1.0)
            logger.debug(f'Schedule task {self.task_name} triggered. exec_interval: {self.exec_interval}', self.server_inst)
            if cfg.config.automatically:
                self.execute_task(self.server_inst, 'schedule')


def stop_all_schedule_daemon_threads(server):
    logger.debug('Stopping all schedule task daemon thread...', server)
    if len(cfg.temp_config.schedule_daemon_threads) == 0:
        return
    
    for thr in cfg.temp_config.schedule_daemon_threads:
        thr.break_thread()
        cfg.temp_config.schedule_daemon_threads.remove(thr)
