"""Private persistent service client. Isolates blocking requests from Python
subscriber callbacks in the installed gz-transport13 bindings."""
import base64
import json
import sys
from gz.transport13 import Node


def main():
    node=Node()
    for line in sys.stdin:
        try:
            r=json.loads(line)
            ok,data=node.request_raw(r['service'],base64.b64decode(r['request']),r['request_type'],r['response_type'],r['timeout'])
            result={'ok':ok,'response':base64.b64encode(data).decode()}
        except Exception as e: result={'error':str(e)}
        print(json.dumps(result),flush=True)


if __name__=='__main__': main()
