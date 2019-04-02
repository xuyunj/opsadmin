
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    author: xuyj
    connection: mysaltstack
"""

import re
import os
import pty
import subprocess

from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.six.moves import cPickle

HAVE_SALTSTACK = False
try:
    import salt.auth
    import salt.client as sc
    import salt.config
    import salt.syspaths as syspaths
    from salt.exceptions import EauthAuthenticationError
    HAVE_SALTSTACK = True
except ImportError:
    pass

import os
from ansible import errors
from ansible.plugins.connection import ConnectionBase

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    import sys
    sys.path.append('/home/service/opsadmin')
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
from django.conf import settings



class Connection(ConnectionBase):
    ''' Salt-based connections '''

    has_pipelining = False
    # while the name of the product is salt, naming that module salt cause
    # trouble with module import
    transport = 'mysaltstack'

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(Connection, self).__init__(play_context, new_stdin, *args, **kwargs)
        self.host = self._play_context.remote_addr
        
        self.token = None
        self.token = self.mk_token(self._play_context.remote_user, self._play_context.password)

    def _connect(self):
        if not HAVE_SALTSTACK:
            raise errors.AnsibleError("saltstack is not installed")

        self.client = sc.LocalClient()
        self._connected = True
        return self
        
    def mk_token(self, user, passwd, eauth='pam'):
        '''
        Run time_auth and create a token. Return False or the token
        '''
  
        options = salt.config.master_config(os.path.join(syspaths.CONFIG_DIR, 'master'))
        
        resolver = salt.auth.Resolver(options)
        try:
            creds = dict(
                username=user,
                password=passwd,
                eauth=eauth
            )
            tokenage = resolver.mk_token(creds)
        except Exception as ex:
            raise EauthAuthenticationError(
                "Authentication failed with {0}.".format(repr(ex)))
               
        if 'token' not in tokenage:
            raise EauthAuthenticationError("Authentication failed with provided credentials.")
            
        return tokenage['token']
            
    def exec_command(self, cmd, sudoable=False, in_data=None):
        ''' run a command on the remote minion '''
        super(Connection, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)

        if in_data:
            raise errors.AnsibleError("Internal Error: this module does not support optimized module pipelining")

        self._display.vvv("EXEC %s" % (cmd), host=self.host)
        # need to add 'true;' to work around https://github.com/saltstack/salt/issues/28077
        res = self.client.cmd(self.host, 'cmd.exec_code_all', ['bash', 'true;' + cmd], token=self.token)
        if self.host not in res:
            raise errors.AnsibleError("Minion %s didn't answer, check if salt-minion is running and the name is correct" % self.host)

        p = res[self.host]
        return (p['retcode'], p['stdout'], p['stderr'])

    def _normalize_path(self, path, prefix):
        if not path.startswith(os.path.sep):
            path = os.path.join(os.path.sep, path)
        normpath = os.path.normpath(path)
        return os.path.join(prefix, normpath[1:])

    def put_file(self, in_path, out_path, task_vars=None):
        ''' transfer a file from local to remote '''

        super(Connection, self).put_file(in_path, out_path)

        out_path = self._normalize_path(out_path, '/')
        self._display.vvv("PUT %s TO %s" % (in_path, out_path), host=self.host)
        
        if 'source' == os.path.basename(out_path) and task_vars:
            extra = dict(
                appid=task_vars['appid'],
                name=os.path.basename(in_path),
                socketid=task_vars['webscoketid'],
                filesize=os.path.getsize(in_path),
                allsize=task_vars['total'] )
            svn_out = os.path.dirname(os.path.dirname(settings.SVN_OUTPATH))
            in_path = 'salt://' + in_path[len(svn_out)+1:]
            callback = {'url': settings.WEBSOCKET_NOTIFY_URL, 'vars': extra}
            res = self.client.cmd(self.host, 'mycp.get_file', [in_path, out_path, callback], token=self.token )
        else:
            content = open(in_path).read()
            res = self.client.cmd(self.host, 'file.write', [out_path, content],  token=self.token )
            self.client.cmd(self.host, 'file.truncate', [out_path, os.path.getsize(in_path)], token=self.token )
        print("PUT %s RESULT %s" % (in_path, res ) )

    # TODO test it
    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote to local '''

        super(Connection, self).fetch_file(in_path, out_path)

        in_path = self._normalize_path(in_path, '/')
        self._display.vvv("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        content = self.client.cmd(self.host, 'cp.get_file_str', [in_path], token=self.token )[self.host]
        open(out_path, 'wb').write(content)

    def close(self):
        ''' terminate the connection; nothing to do here '''
        pass


        
