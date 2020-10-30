import requests
import re
import json
import zipfile
import argparse
import configparser
import os
import io
import subprocess
import logging

class OverleafAPI:
    def __init__(self, url, email, password):
        self.url = url
        self.email = email
        self.password = password
        self.logged_in = False

        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'

    def ensure_login(self):
        if self.logged_in:
            return
        self.logged_in = True

        page = self.session.get(f'{self.url}/login')
        m = re.search(r'window.csrfToken = "([^"]+)', page.content.decode('utf-8'))
        csrf_token = m.group(1)

        page = self.session.post(f"{conf.url}/login", data={
            '_csrf': csrf_token,
            'email': self.email,
            'password': self.password
        })

    def projects(self):
        self.ensure_login()
        page = self.session.get(self.url)

        m = re.search(r"({\"projects\":.*?)</script>", page.content.decode('utf-8'), flags=re.DOTALL)
        data = json.loads(m.group(1))

        return data['projects']

    def download_extract(self, project_id, path):
        self.ensure_login()
        page = self.session.get(f"{self.url}/project/{project_id}/download/zip")

        with zipfile.ZipFile(io.BytesIO(page.content)) as z:
            z.extractall(path)

def cmd_sync(conf):
    with open(os.path.join(conf.path, ".projectid")) as f:
        project_id = f.read().strip()

    api = OverleafAPI(conf.url, conf.email, conf.password)
    api.download_extract(project_id, conf.path)
    subprocess.check_call(["git", "commit", "-a", "-m", "autocommit"], cwd=conf.path)

def cmd_sync_all(conf):
    projects = {}
    for obj in os.listdir(conf.path):
        try:
            with open(os.path.join(conf.path, obj, ".projectid")) as f:
                projects[os.path.join(conf.path, obj)] = f.read().strip()
        except NotADirectoryError:
            pass

    api = OverleafAPI(conf.url, conf.email, conf.password)
    for project in api.projects():
        if project['id'] not in projects.values():
            project_path = os.path.join(conf.path, project['name'].replace(' ', '_'))
            try:
                os.makedirs(project_path)
            except FileExistsError:
                project_path += f'_{project["id"]}'
                os.makedirs(project_path)
            with open(os.path.join(project_path, ".projectid"), "w") as f:
                f.write(project['id'])
            subprocess.check_call(["git", "init"], cwd=project_path)
            projects[project_path] = project['id']

    for path, project_id in projects.items():
        api.download_extract(project_id, path)
        print(path)
        subprocess.check_call(["git", "add", "."], cwd=path)
        changes = subprocess.check_output(["git", "status", "--porcelain"], cwd=path).decode('utf-8').strip()
        if changes:
            subprocess.check_call(["git", "commit", "-m", "autocommit"], cwd=path)

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='https://www.overleaf.com')
subparsers = parser.add_subparsers(dest='cmd', required=True)

p = subparsers.add_parser('sync')
p.add_argument('path', default='.', nargs='?')

p = subparsers.add_parser('sync_all')
p.add_argument('path', default='.', nargs='?')

conf = parser.parse_args()
cnf = configparser.ConfigParser()
cnf.read(os.path.expanduser('~/.overleaf'))
conf.email = cnf.get('auth', 'email')
conf.password = cnf.get('auth', 'password')

globals()[f'cmd_{conf.cmd}'](conf)
