from scrounger.core.module import BaseModule

# helper functions
from scrounger.utils.config import Log
from langdetect import detect_langs
from time import sleep

class Module(BaseModule):
    meta = {
        "author": "RDC",
        "description": "Looks for world readable files in the application's \
data directory",
        "certainty": 70
    }

    options = [
        {
            "name": "device",
            "description": "the remote device",
            "required": True,
            "default": None
        },
        {
            "name": "identifier",
            "description": "the application's identifier",
            "required": True,
            "default": None
        },
    ]

    def run(self):
        result = {
            "title": "Application Has World Readable Files",
            "details": "",
            "severity": "Medium",
            "report": False
        }

        if not self.device.installed(self.identifier):
            return {"print": "Application not installed"}

        Log.info("Starting the application")
        self.device.start(self.identifier)

        sleep(5)

        Log.info("Analysing application's data")

        target_paths = self.device.data_paths(self.identifier)

        world_readable_files = []
        for data_path in target_paths:
            world_readable_files += self.device.world_files(data_path, "r")

        if world_readable_files:
            result.update({
                "report": True,
                "details": "* World Readable Files:\n * {}".format("\n* ".join(
                    world_readable_files))
            })

        return {
            "{}_result".format(self.name()): result
        }

