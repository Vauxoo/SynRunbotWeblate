# coding: utf-8

import os
import xmlrpclib
import requests
import subprocess
import ConfigParser


class Rpc(object):

    def __init__(self, configuration):
        self.url = '%s/xmlrpc/' % configuration.get('odoo', 'url')
        self.db = configuration.get('odoo', 'db')
        self.username = configuration.get('odoo', 'username')
        self.password = configuration.get('odoo', 'password')

    def login(self):
        self._user = xmlrpclib.ServerProxy(self.url + 'common').login(
            self.db, self.username, self.password)
        if not self._user:
            raise Exception('Not login into %s' % self.url)

    def execute(self, *args, **kargs):
        return xmlrpclib.ServerProxy(self.url + 'object').execute(
            self.db, self._user, self.password, *args, **kargs)


class WeblateAPI(object):

    def __init__(self, configuration):
        self._weblate_container = False
        if configuration.has_section('docker'):
            self._weblate_container = configuration.get('docker', 'name')

    def _init_api(self, url, token):
        self._url = url
        self._token = token
        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'syn_runbot_weblate',
            'Authorization': 'Token %s' % self._token
        })
        self._api_projects = self._session.get(self._url + '/projects/').json()['results']

    def create_project(self, repo, slug):
        slug = slug.replace('/', '-')
        if (not any([pre for pre in ['http://', 'https://'] if pre in repo])
                and '@' in repo):
            repo = 'http://' + repo.split('@')[1:].pop().replace(':', '/')
        cmd = []
        if self._weblate_container:
            cmd.extend(['docker', 'exec', self._weblate_container])
        cmd.extend(['django-admin', 'shell', '-c',
                    'import weblate.trans.models.project as project;'
                    'project.Project(name=\'{0}\', slug=\'{0}\', web=\'{1}\').save()'.format(slug, repo)])
        print cmd
        subprocess.check_output(cmd)
        return self._session.get(self._url + '/projects/%s/' % slug).json()

    def find_or_create_project(self, project):
        repo = project['repo']
        slug = ''
        if '@' in repo:
            slug = repo.split('@')[1:].pop().replace('/', '-')
        if any([pre for pre in ['http://', 'https://'] if pre in repo]):
            slug = repo.replace('https://', '').replace('http://', '').split('/')
            slug = slug[0] + ':' +  slug[1] + '-' + slug[2]
        slug = slug.replace('.git', '') + '(' + project['branch'] + ')'
        for pro in self._api_projects:
            if slug == pro['name']:
                return pro
        return self.create_project(repo, slug)

    def create_component(self, project, branch):
        cmd = []
        if self._weblate_container:
            cmd.extend(['docker', 'exec', self._weblate_container])
        cmd.extend(['django-admin',
                    'import_project', project['slug'], project['web'],
                    branch['branch_name'], '**/i18n/*.po'])
        print cmd
        print subprocess.check_output(cmd)

    def import_from_runbot(self, repo, branches):
        self._init_api(repo['weblate_url'], repo['weblate_token'])
        for branch in branches:
            project = self.find_or_create_project({
                'repo': repo['name'],
                'branch': branch['branch_name']
            })
            self.create_component(project, branch)

    def _request_api(self, url):
        return self._session.get(self._url + url).json()


class SynRunbotWeblate(object):

    def __init__(self, configuration):
        self._rpc = Rpc(configuration)
        self._wlapi = WeblateAPI(configuration)

    def sync(self):
        self._rpc.login()
        ids = self._rpc.execute('runbot.repo', 'search',
            [['weblate_token', '!=', ''], ['weblate_url', '!=', '']])
        repos = self._rpc.execute('runbot.repo', 'read', ids)
        for repo in repos:
            ids = self._rpc.execute('runbot.branch', 'search',
                [['uses_weblate', '=', True], ['repo_id', '=', repo['id']]])
            branches = self._rpc.execute('runbot.branch', 'read', ids)
            self._wlapi.import_from_runbot(repo, branches)
        return 0


if __name__ == '__main__':
    configuration = ConfigParser.ConfigParser()
    configuration.readfp(open(os.path.join(os.getcwd(), 'synchronize.cfg')))

    exit(SynRunbotWeblate(configuration).sync())
