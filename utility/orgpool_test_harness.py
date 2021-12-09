import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

JSON_STR = None


class FakeMetaCI(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        length = int(self.headers.get("content-length", 0))
        self.send_header("Content-type", "application/json")
        body = self.rfile.read(length)
        if body:
            jsn = json.loads(body.decode("utf-8"))
            print(jsn.keys())
            if jsn["org_name"] == "feature":
                print("RETURNING EMPTY LIST")
                return {}
        self.end_headers()
        self.wfile.write(JSON_STR.encode(encoding="utf_8"))
        print("RETURNING ORG CONFIG")

    def do_GET(self):
        return self.do_POST()


def get_org_json(orgname):
    subprocess.run(f"cci org scratch_delete {orgname}", shell=True)
    subprocess.run(f"cci org remove {orgname}", shell=True)
    out = subprocess.run(
        f"cci org info {orgname} --json", shell=True, stdout=subprocess.PIPE, text=True
    )
    json_ish = out.stdout
    bracket = json_ish.find("{")
    json_str = json_ish[bracket:]
    js = json.loads(json_str)
    out = subprocess.run(
        "sfdx force:org:display --json --verbose -u CumulusCI__feature",
        shell=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    json_ish = out.stdout
    bracket = json_ish.find("{")
    json_str = json_ish[bracket:]
    jsn = json.loads(json_str)
    js["sfdxAuthUrl"] = jsn["result"]["sfdxAuthUrl"]
    return json.dumps(js)


def run(server_class=HTTPServer, handler_class=FakeMetaCI):
    global JSON_STR
    JSON_STR = get_org_json("feature")
    server_address = ("", 8001)
    httpd = server_class(server_address, handler_class)
    print("Ready")
    httpd.serve_forever()


run()
