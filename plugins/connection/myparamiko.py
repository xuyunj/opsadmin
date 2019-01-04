from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    author: xuyj
    connection: paramiko
    short_description: It's a subclass of paramiko_ssh
    description:
        - It's a subclass of paramiko_ssh
    options:
      remote_addr:
        description:
            - Address of the remote target
        default: inventory_hostname
        vars:
            - name: ansible_host
            - name: ansible_ssh_host
            - name: ansible_paramiko_host
      remote_user:
        description:
            - User to login/authenticate as
            - Can be set from the CLI via the C(--user) or C(-u) options.
        vars:
            - name: ansible_user
            - name: ansible_ssh_user
            - name: ansible_paramiko_user
        env:
            - name: ANSIBLE_REMOTE_USER
            - name: ANSIBLE_PARAMIKO_REMOTE_USER
              version_added: '2.5'
        ini:
            - section: defaults
              key: remote_user
            - section: paramiko_connection
              key: remote_user
              version_added: '2.5'
      password:
        description:
          - Secret used to either login the ssh server or as a passphrase for ssh keys that require it
          - Can be set from the CLI via the C(--ask-pass) option.
        vars:
            - name: ansible_password
            - name: ansible_ssh_pass
            - name: ansible_paramiko_pass
              version_added: '2.5'
      host_key_auto_add:
        description: 'TODO: write it'
        env: [{name: ANSIBLE_PARAMIKO_HOST_KEY_AUTO_ADD}]
        ini:
          - {key: host_key_auto_add, section: paramiko_connection}
        type: boolean
      look_for_keys:
        default: True
        description: 'TODO: write it'
        env: [{name: ANSIBLE_PARAMIKO_LOOK_FOR_KEYS}]
        ini:
        - {key: look_for_keys, section: paramiko_connection}
        type: boolean
      proxy_command:
        default: ''
        description:
            - Proxy information for running the connection via a jumphost
            - Also this plugin will scan 'ssh_args', 'ssh_extra_args' and 'ssh_common_args' from the 'ssh' plugin settings for proxy information if set.
        env: [{name: ANSIBLE_PARAMIKO_PROXY_COMMAND}]
        ini:
          - {key: proxy_command, section: paramiko_connection}
      pty:
        default: True
        description: 'TODO: write it'
        env:
          - name: ANSIBLE_PARAMIKO_PTY
        ini:
          - section: paramiko_connection
            key: pty
        type: boolean
      record_host_keys:
        default: True
        description: 'TODO: write it'
        env: [{name: ANSIBLE_PARAMIKO_RECORD_HOST_KEYS}]
        ini:
          - section: paramiko_connection
            key: record_host_keys
        type: boolean
      host_key_checking:
        description: 'Set this to "False" if you want to avoid host key checking by the underlying tools Ansible uses to connect to the host'
        type: boolean
        default: True
        env:
          - name: ANSIBLE_HOST_KEY_CHECKING
          - name: ANSIBLE_SSH_HOST_KEY_CHECKING
            version_added: '2.5'
          - name: ANSIBLE_PARAMIKO_HOST_KEY_CHECKING
            version_added: '2.5'
        ini:
          - section: defaults
            key: host_key_checking
          - section: paramiko_connection
            key: host_key_checking
            version_added: '2.5'
        vars:
          - name: ansible_host_key_checking
            version_added: '2.5'
          - name: ansible_ssh_host_key_checking
            version_added: '2.5'
          - name: ansible_paramiko_host_key_checking
            version_added: '2.5'
      use_persistent_connections:
        description: 'Toggles the use of persistence for connections'
        type: boolean
        default: False
        env:
          - name: ANSIBLE_USE_PERSISTENT_CONNECTIONS
        ini:
          - section: defaults
            key: use_persistent_connections
# TODO:
#timeout=self._play_context.timeout,
"""


import os
import traceback
from ansible.plugins.connection.paramiko_ssh import Connection as ParamikoConnection
from ansible.errors import AnsibleError, AnsibleConnectionFailure, AnsibleFileNotFound
from ansible.module_utils._text import to_bytes, to_native

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class Connection(ParamikoConnection):
    ''' SSH based connections with Paramiko '''

    transport = 'myparamiko'
    _log_channel = None

    def put_file(self, in_path, out_path, callback=None):
        ''' transfer a file from local to remote '''

        super(Connection, self).put_file(in_path, out_path)

        display.vvv("PUT %s TO %s" % (in_path, out_path), host=self._play_context.remote_addr)

        if not os.path.exists(to_bytes(in_path, errors='surrogate_or_strict')):
            raise AnsibleFileNotFound("file or module does not exist: %s" % in_path)

        try:
            self.sftp = self.ssh.open_sftp()
        except Exception as e:
            raise AnsibleError("failed to open a SFTP connection (%s)" % e)

        try:
            self.sftp.put(to_bytes(in_path, errors='surrogate_or_strict'), to_bytes(out_path, errors='surrogate_or_strict'), callback)
        except IOError:
            raise AnsibleError("failed to transfer file to %s" % out_path)

    def fetch_file(self, in_path, out_path):
        ''' save a remote file to the specified path '''

        super(Connection, self).fetch_file(in_path, out_path)

        display.vvv("FETCH %s TO %s" % (in_path, out_path), host=self._play_context.remote_addr)

        try:
            self.sftp = self._connect_sftp()
        except Exception as e:
            raise AnsibleError("failed to open a SFTP connection (%s)" % to_native(e))

        try:
            self.sftp.get(to_bytes(in_path, errors='surrogate_or_strict'), to_bytes(out_path, errors='surrogate_or_strict'))
        except IOError:
            raise AnsibleError("failed to transfer file from %s" % in_path)

