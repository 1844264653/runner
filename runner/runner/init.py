import sys

from salmon.runner import server

if __name__ == "__main__":
    args = sys.argv
    if len(args) != 3:
        raise ValueError("Usage: python xxx.py count. count is a number.")
    concurrency = int(args[1])
    mark = args[2]

    deploy_client = server.Deploy(
        # TODO: to get browser  type
        browser_type="chrome", browser_version=None, concurrency=concurrency, mark=mark)