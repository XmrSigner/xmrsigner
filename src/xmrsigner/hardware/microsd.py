from os import path, remove, mkfifo
from time import sleep

from xmrsigner.models.singleton import Singleton
from xmrsigner.models.threads import BaseThread
from xmrsigner.models.settings import Settings



class MicroSD(Singleton, BaseThread):
    ACTION__INSERTED = 'add'
    ACTION__REMOVED = 'remove'


    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            # Instantiate the one and only instance
            microsd = cls.__new__(cls)
            cls._instance = microsd

            # explicitly call BaseThread __init__ since multiple class inheritance
            BaseThread.__init__(microsd)

        return cls._instance


    @property
    def is_inserted(self):
        if Settings.HOSTNAME == Settings.XMRSIGNER_OS:
            return path.exists(Settings.MICROSD_MOUNT_POINT)
        # Always True for Raspi OS
        return True

    def start_detection(self):
        self.start()

    def run(self):
        from xmrsigner.controller import Controller
        action = ''
        # explicitly only microsd add/remove detection in seedsigner-os
        if Settings.HOSTNAME == Settings.XMRSIGNER_OS:
            # at start-up, get current status and inform Settings
            Settings.handle_microsd_state_change(
                action=MicroSD.ACTION__INSERTED if self.is_inserted else MicroSD.ACTION__REMOVED
            )
            if path.exists(Settings.MICROSD_FIFO_PATH):
                remove(Settings.MICROSD_FIFO_PATH)
            mkfifo(Settings.MICROSD_FIFO_PATH, Settings.MICROSD_FIFO_MODE)
            while self.keep_running:
                with open(Settings.MICROSD_FIFO_PATH) as fifo:
                    action = fifo.read()
                    print(f"fifo message: {action}")
                    Settings.handle_microsd_state_change(action=action)
                sleep(0.1)
