from scrounger.core.module import BaseModule

# helper functions
from scrounger.utils.general import pretty_grep, pretty_grep_to_str
from scrounger.utils.android import smali_dirs
from scrounger.utils.config import Log

class Module(BaseModule):
    meta = {
        "author": "RDC",
        "description": "Checks if the application's webviews delete cached \
files",
        "certainty": 80
    }

    options = [
        {
            "name": "decompiled_apk",
            "description": "local folder containing the decompiled apk file",
            "required": True,
            "default": None
        },
        {
            "name": "ignore",
            "description": "paths to ignore, seperated by ;",
            "required": False,
            "default": "/com/google/;/android/support/"
        }
    ]

    use_webview_regex = r"android.webkit.WebView;"
    regex = r"android.webkit.WebView;->clearCache"

    def run(self):
        result = {
            "title": "Application Does Not Delete Cached Files On Exit",
            "details": "",
            "severity": "Low",
            "report": False
        }

        # preparing variable to run
        webview_files = {}
        clear_cache = {}
        ignore = [filepath.strip() for filepath in self.ignore.split(";")]

        Log.info("Identifying smali directories")
        dirs = smali_dirs(self.decompiled_apk)

        Log.info("Analysing application's smali code")
        for directory in dirs:
            smali = "{}/{}".format(self.decompiled_apk, directory)
            webview_files.update(pretty_grep(self.use_webview_regex, smali))
            clear_cache.update(pretty_grep(self.regex, smali))

        Log.info("Analysing WebViews")

        for filename in clear_cache:
            webview_files.pop(filename)

        if webview_files:
            result.update({
                "report": True,
                "details": pretty_grep_to_str(webview_files,
                    self.decompiled_apk, ignore)
            })

        return {
            "{}_result".format(self.name()): result
        }

