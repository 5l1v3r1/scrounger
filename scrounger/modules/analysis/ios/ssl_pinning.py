from scrounger.core.module import BaseModule

# helper functions
from scrounger.utils.config import Log, _CERT_PATH
from scrounger.utils.general import strings, pretty_grep
from scrounger.lib.proxy2 import create_server

from time import sleep
import re

class Module(BaseModule):
    meta = {
        "author": "RDC",
        "description": "Checks if the application implements SSL pinning",
        "certainty": 60
    }

    options = [
        {
            "name": "class_dump",
            "description": "local path to the application's class dump",
            "required": True,
            "default": None
        },
        {
            "name": "binary",
            "description": "local path to the application's decrypted binary",
            "required": True,
            "default": None
        },
        {
            "name": "identifier",
            "description": "the application's identifier",
            "required": False,
            "default": None
        },
        {
            "name": "device",
            "description": "the remote device",
            "required": False,
            "default": None
        },
        {
            "name": "proxy_host",
            "description": "the hostname to have a proxy listening on",
            "required": False,
            "default": ""
        },
        {
            "name": "proxy_port",
            "description": "the port to have a proxy listening on",
            "required": False,
            "default": 9090
        },
        {
            "name": "wait_time",
            "description": "set how long (seconds) to wait before starting the \
proxy - this time is used to allow setup of proxy on the remote device.",
            "required": False,
            "default": 20
        },
        {
            "name": "relay",
            "description": "to be used when UNSSUPORTED PROTOCOLS errors occur \
on iOS SSL intercept - relays to invisible proxy on 127.0.0.1:8080 and expects \
the request to be returned to 127.0.0.1:9091",
            "required": False,
            "default": False
        },
        {
            "name": "ignore_url",
            "description": "domains to be ignored",
            "required": False,
            "default": ".icloud.com;.apple.com;.googleapis.com;\
graph.facebook.com;.crashlytics.com;api.branch.io;t.appsflyer.com;\
gate.hockeyapp.net;www.paypalobjects.com;www.gstatic.com;app.adjust.com;\
data.flurry.com;.doubleclick.net;.google-analytics.com;.adobedtm.com;\
googletagmanager.com"
        },
    ]

    _regex = r"setAllowInvalidCertificates|allowsInvalidSSLCertificate|\
validatesDomainName|SSLPinningMode"

    def run(self):
        result = {
            "title": "Application Does Not Implement SSL Pinning",
            "details": "",
            "severity": "Medium",
            "report": False
        }

        ignored_urls = [url.strip() for url in self.ignore_url.split(";")]

        Log.info("Getting application's strings")
        strs = strings(self.binary)

        Log.info("Analysing strings and class dump")
        matches = re.findall(self._regex, strs)
        evidence = pretty_grep(self._regex, self.class_dump)

        if matches:
            result.update({
                "report": True,
                "details": "The following strings were found:\n* {}".format(
                    "\n* ".join(sorted(set(matches))))
            })

        if evidence:
            result.update({
                "report": True,
                "details": "{}\nThe following was found in the class dump:\n\
{}".format(result["details"], pretty_grep_to_str(evidence, self.class_dump))
            })

        if self.device and self.identifier and \
        self.proxy_host != None and self.proxy_port != None:
            Log.info("Testing SSL Pinning using a proxy")
            Log.info("Make sure your device trusts the CA in: {}/ca.crt".format(
                _CERT_PATH))
            Log.info("Waiting for {} seconds to allow time to setup the \
proxy on the remote device".format(self.wait_time))
            sleep(int(self.wait_time))

            Log.info("Killing the application")
            self.device.stop(self.identifier)

            Log.info("Starting the SSL proxy")
            if self.relay:
                proxy_server, upstream_server = create_server(
                    self.proxy_host, self.proxy_port, _CERT_PATH,
                    "127.0.0.1", 8080, 9091)
            else:
                proxy_server = create_server(self.proxy_host, self.proxy_port,
                    _CERT_PATH)

            Log.info("Starting the Application")
            self.device.start(self.identifier)

            Log.info("Waiting for the Application to start and make requests")
            sleep(10)

            if self.relay:
                proxy_server.server.requested = list(set(
                    upstream_server.server.requested))
            unfiltered_pinned = list(set(proxy_server.server.connected) -
                set(proxy_server.server.requested))
            pinned = []
            for url in unfiltered_pinned:
                if not any([u in url for u in ignored_urls]):
                    pinned += [url]

            if not proxy_server.server.connected:
                Log.error("No connections made by the application")

            if pinned:
                result.update({
                    "title": "Application Implements SSL Pinning",
                    "report": True,
                    "details": "{}\n\nThe application started a connection but \
made no requests to the following domains:\n* {}".format(result["details"],
                        "\n* ".join(pinned))
                    })

            if proxy_server.server.requested:
                result.update({
                    "report": True,
                    "details": "{}\n\nThe application started a connection and \
made requests to the following domains:\n* {}".format(result["details"],
                        "\n* ".join(proxy_server.server.requested))
                    })

            if self.relay:
                upstream_server.stop()
            proxy_server.stop()

        return {
            "{}_result".format(self.name()): result
        }

