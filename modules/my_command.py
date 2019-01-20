#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>, and others
# Copyright: (c) 2016, Toshio Kuratomi <tkuratomi@ansible.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


import datetime
import glob
import os
import shlex
import select
import subprocess
import traceback
import socket

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils.common.collections import is_iterable

from ansible.module_utils.six import (
    PY2,
    PY3,
    b,
    binary_type,
    integer_types,
    iteritems,
    string_types,
    text_type,
)


def check_command(module, commandline):
    arguments = {'chown': 'owner', 'chmod': 'mode', 'chgrp': 'group',
                 'ln': 'state=link', 'mkdir': 'state=directory',
                 'rmdir': 'state=absent', 'rm': 'state=absent', 'touch': 'state=touch'}
    commands = {'curl': 'get_url or uri', 'wget': 'get_url or uri',
                'svn': 'subversion', 'service': 'service',
                'mount': 'mount', 'rpm': 'yum, dnf or zypper', 'yum': 'yum', 'apt-get': 'apt',
                'tar': 'unarchive', 'unzip': 'unarchive', 'sed': 'replace, lineinfile or template',
                'dnf': 'dnf', 'zypper': 'zypper'}
    become = ['sudo', 'su', 'pbrun', 'pfexec', 'runas', 'pmrun', 'machinectl']
    if isinstance(commandline, list):
        command = commandline[0]
    else:
        command = commandline.split()[0]
    command = os.path.basename(command)

    disable_suffix = "If you need to use command because {mod} is insufficient you can add" \
                     " warn=False to this command task or set command_warnings=False in" \
                     " ansible.cfg to get rid of this message."
    substitutions = {'mod': None, 'cmd': command}

    if command in arguments:
        msg = "Consider using the {mod} module with {subcmd} rather than running {cmd}.  " + disable_suffix
        substitutions['mod'] = 'file'
        substitutions['subcmd'] = arguments[command]
        module.warn(msg.format(**substitutions))

    if command in commands:
        msg = "Consider using the {mod} module rather than running {cmd}.  " + disable_suffix
        substitutions['mod'] = commands[command]
        module.warn(msg.format(**substitutions))

    if command in become:
        module.warn("Consider using 'become', 'become_method', and 'become_user' rather than running %s" % (command,))


import urllib
import urllib2

class MyAnsibleModule(AnsibleModule):
    
    def __init__(self, **kwargs):
        super(MyAnsibleModule, self).__init__(**kwargs)
        
    def get_host_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 53))
            ip = s.getsockname()[0]
        finally:
            s.close()
            return ip
        
    def send_webmsg(self, url, name, uid, msg ):
        params = {
            'name': name, 
            'uid': uid, 
            'host': self.get_host_ip(), 
            'msg': msg }
        #url = url + '?' + urllib.urlencode(params)
        req = urllib2.Request( url,  urllib.urlencode(params))
        resp = urllib2.urlopen(req)
        #response = resp.read()
        resp.close()
        
    def run_command(self, args, check_rc=False, close_fds=True, executable=None, data=None, binary_data=False, path_prefix=None, cwd=None,
                    use_unsafe_shell=False, prompt_regex=None, environ_update=None, umask=None, encoding='utf-8', errors='surrogate_or_strict'):
        '''
        Execute a command, returns rc, stdout, and stderr.

        :arg args: is the command to run
            * If args is a list, the command will be run with shell=False.
            * If args is a string and use_unsafe_shell=False it will split args to a list and run with shell=False
            * If args is a string and use_unsafe_shell=True it runs with shell=True.
        :kw check_rc: Whether to call fail_json in case of non zero RC.
            Default False
        :kw close_fds: See documentation for subprocess.Popen(). Default True
        :kw executable: See documentation for subprocess.Popen(). Default None
        :kw data: If given, information to write to the stdin of the command
        :kw binary_data: If False, append a newline to the data.  Default False
        :kw path_prefix: If given, additional path to find the command in.
            This adds to the PATH environment vairable so helper commands in
            the same directory can also be found
        :kw cwd: If given, working directory to run the command inside
        :kw use_unsafe_shell: See `args` parameter.  Default False
        :kw prompt_regex: Regex string (not a compiled regex) which can be
            used to detect prompts in the stdout which would otherwise cause
            the execution to hang (especially if no input data is specified)
        :kw environ_update: dictionary to *update* os.environ with
        :kw umask: Umask to be used when running the command. Default None
        :kw encoding: Since we return native strings, on python3 we need to
            know the encoding to use to transform from bytes to text.  If you
            want to always get bytes back, use encoding=None.  The default is
            "utf-8".  This does not affect transformation of strings given as
            args.
        :kw errors: Since we return native strings, on python3 we need to
            transform stdout and stderr from bytes to text.  If the bytes are
            undecodable in the ``encoding`` specified, then use this error
            handler to deal with them.  The default is ``surrogate_or_strict``
            which means that the bytes will be decoded using the
            surrogateescape error handler if available (available on all
            python3 versions we support) otherwise a UnicodeError traceback
            will be raised.  This does not affect transformations of strings
            given as args.
        :returns: A 3-tuple of return code (integer), stdout (native string),
            and stderr (native string).  On python2, stdout and stderr are both
            byte strings.  On python3, stdout and stderr are text strings converted
            according to the encoding and errors parameters.  If you want byte
            strings on python3, use encoding=None to turn decoding to text off.
        '''
        # used by clean args later on
        self._clean = None

        if not isinstance(args, (list, binary_type, text_type)):
            msg = "Argument 'args' to run_command must be list or string"
            self.fail_json(rc=257, cmd=args, msg=msg)

        shell = False
        if use_unsafe_shell:

            # stringify args for unsafe/direct shell usage
            if isinstance(args, list):
                args = " ".join([shlex_quote(x) for x in args])

            # not set explicitly, check if set by controller
            if executable:
                args = [executable, '-c', args]
            elif self._shell not in (None, '/bin/sh'):
                args = [self._shell, '-c', args]
            else:
                shell = True
        else:
            # ensure args are a list
            if isinstance(args, (binary_type, text_type)):
                # On python2.6 and below, shlex has problems with text type
                # On python3, shlex needs a text type.
                if PY2:
                    args = to_bytes(args, errors='surrogate_or_strict')
                elif PY3:
                    args = to_text(args, errors='surrogateescape')
                args = shlex.split(args)

            # expand shellisms
            args = [os.path.expanduser(os.path.expandvars(x)) for x in args if x is not None]

        prompt_re = None
        if prompt_regex:
            if isinstance(prompt_regex, text_type):
                if PY3:
                    prompt_regex = to_bytes(prompt_regex, errors='surrogateescape')
                elif PY2:
                    prompt_regex = to_bytes(prompt_regex, errors='surrogate_or_strict')
            try:
                prompt_re = re.compile(prompt_regex, re.MULTILINE)
            except re.error:
                self.fail_json(msg="invalid prompt regular expression given to run_command")

        rc = 0
        msg = None
        st_in = None

        # Manipulate the environ we'll send to the new process
        old_env_vals = {}
        # We can set this from both an attribute and per call
        for key, val in self.run_command_environ_update.items():
            old_env_vals[key] = os.environ.get(key, None)
            os.environ[key] = val
        if environ_update:
            for key, val in environ_update.items():
                old_env_vals[key] = os.environ.get(key, None)
                os.environ[key] = val
        if path_prefix:
            old_env_vals['PATH'] = os.environ['PATH']
            os.environ['PATH'] = "%s:%s" % (path_prefix, os.environ['PATH'])

        # If using test-module and explode, the remote lib path will resemble ...
        #   /tmp/test_module_scratch/debug_dir/ansible/module_utils/basic.py
        # If using ansible or ansible-playbook with a remote system ...
        #   /tmp/ansible_vmweLQ/ansible_modlib.zip/ansible/module_utils/basic.py

        # Clean out python paths set by ansiballz
        if 'PYTHONPATH' in os.environ:
            pypaths = os.environ['PYTHONPATH'].split(':')
            pypaths = [x for x in pypaths
                       if not x.endswith('/ansible_modlib.zip') and
                       not x.endswith('/debug_dir')]
            os.environ['PYTHONPATH'] = ':'.join(pypaths)
            if not os.environ['PYTHONPATH']:
                del os.environ['PYTHONPATH']

        if data:
            st_in = subprocess.PIPE

        kwargs = dict(
            executable=executable,
            shell=shell,
            close_fds=close_fds,
            stdin=st_in,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=self._restore_signal_handlers,
        )

        # store the pwd
        prev_dir = os.getcwd()

        # make sure we're in the right working directory
        if cwd and os.path.isdir(cwd):
            cwd = os.path.abspath(os.path.expanduser(cwd))
            kwargs['cwd'] = cwd
            try:
                os.chdir(cwd)
            except (OSError, IOError) as e:
                self.fail_json(rc=e.errno, msg="Could not open %s, %s" % (cwd, to_native(e)),
                               exception=traceback.format_exc())

        old_umask = None
        if umask:
            old_umask = os.umask(umask)

        try:
            if self._debug:
                self.log('Executing: ' + self._clean_args(args))
            cmd = subprocess.Popen(args, **kwargs)

            # the communication logic here is essentially taken from that
            # of the _communicate() function in ssh.py

            stdout = b('')
            stderr = b('')
            rpipes = [cmd.stdout, cmd.stderr]

            if data:
                if not binary_data:
                    data += '\n'
                if isinstance(data, text_type):
                    data = to_bytes(data)
                cmd.stdin.write(data)
                cmd.stdin.close()

            while True:
                rfds, wfds, efds = select.select(rpipes, [], rpipes, 1)
                normalout = self._read_from_pipes(rpipes, rfds, cmd.stdout)
                if normalout:
                    #print('output--->: ', normalout)
                    self.send_webmsg(self.params['url'], self.params['name'], self.params['uid'], normalout )
                stdout += normalout
                errout = self._read_from_pipes(rpipes, rfds, cmd.stderr)
                stderr += errout

                # if we're checking for prompts, do it now
                if prompt_re:
                    if prompt_re.search(stdout) and not data:
                        if encoding:
                            stdout = to_native(stdout, encoding=encoding, errors=errors)
                        else:
                            stdout = stdout
                        return (257, stdout, "A prompt was encountered while running a command, but no input data was specified")
                # only break out if no pipes are left to read or
                # the pipes are completely read and
                # the process is terminated
                if (not rpipes or not rfds) and cmd.poll() is not None:
                    break
                # No pipes are left to read but process is not yet terminated
                # Only then it is safe to wait for the process to be finished
                # NOTE: Actually cmd.poll() is always None here if rpipes is empty
                elif not rpipes and cmd.poll() is None:
                    cmd.wait()
                    # The process is terminated. Since no pipes to read from are
                    # left, there is no need to call select() again.
                    break

            cmd.stdout.close()
            cmd.stderr.close()

            rc = cmd.returncode
        except (OSError, IOError) as e:
            self.log("Error Executing CMD:%s Exception:%s" % (self._clean_args(args), to_native(e)))
            self.fail_json(rc=e.errno, msg=to_native(e), cmd=self._clean_args(args))
        except Exception as e:
            self.log("Error Executing CMD:%s Exception:%s" % (self._clean_args(args), to_native(traceback.format_exc())))
            self.fail_json(rc=257, msg=to_native(e), exception=traceback.format_exc(), cmd=self._clean_args(args))

        # Restore env settings
        for key, val in old_env_vals.items():
            if val is None:
                del os.environ[key]
            else:
                os.environ[key] = val

        if old_umask:
            os.umask(old_umask)

        if rc != 0 and check_rc:
            msg = heuristic_log_sanitize(stderr.rstrip(), self.no_log_values)
            self.fail_json(cmd=self._clean_args(args), rc=rc, stdout=stdout, stderr=stderr, msg=msg)

        # reset the pwd
        os.chdir(prev_dir)

        if encoding is not None:
            return (rc, to_native(stdout, encoding=encoding, errors=errors),
                    to_native(stderr, encoding=encoding, errors=errors))

        return (rc, stdout, stderr)
    
def main():

    # the command module is the one ansible module that does not take key=value args
    # hence don't copy this one if you are looking to build others!
    module = MyAnsibleModule(
        argument_spec=dict(
            command=dict(required=True),
            _uses_shell=dict(type='bool', default=False),
            argv=dict(type='list'),
            chdir=dict(type='path'),
            executable=dict(),
            creates=dict(type='path'),
            removes=dict(type='path'),
            # The default for this really comes from the action plugin
            warn=dict(type='bool', default=True),
            stdin=dict(required=False),
            url=dict(required=True),
            name=dict(required=True),
            uid=dict(required=True),
        ),
        supports_check_mode=True,
    )
    shell = module.params['_uses_shell']
    chdir = module.params['chdir']
    executable = module.params['executable']
    args = module.params['command']
    argv = module.params['argv']
    creates = module.params['creates']
    removes = module.params['removes']
    warn = module.params['warn']
    stdin = module.params['stdin']

    if not shell and executable:
        module.warn("As of Ansible 2.4, the parameter 'executable' is no longer supported with the 'command' module. Not using '%s'." % executable)
        executable = None

    if (not args or args.strip() == '') and not argv:
        module.fail_json(rc=256, msg="no command given")

    if args and argv:
        module.fail_json(rc=256, msg="only command or argv can be given, not both")

    if not shell and args:
        args = shlex.split(args)

    args = args or argv

    # All args must be strings
    if is_iterable(args, include_strings=False):
        args = [to_native(arg, errors='surrogate_or_strict', nonstring='simplerepr') for arg in args]

    if chdir:
        chdir = os.path.abspath(chdir)
        os.chdir(chdir)

    if creates:
        # do not run the command if the line contains creates=filename
        # and the filename already exists.  This allows idempotence
        # of command executions.
        if glob.glob(creates):
            module.exit_json(
                cmd=args,
                stdout="skipped, since %s exists" % creates,
                changed=False,
                rc=0
            )

    if removes:
        # do not run the command if the line contains removes=filename
        # and the filename does not exist.  This allows idempotence
        # of command executions.
        if not glob.glob(removes):
            module.exit_json(
                cmd=args,
                stdout="skipped, since %s does not exist" % removes,
                changed=False,
                rc=0
            )

    if warn:
        check_command(module, args)

    startd = datetime.datetime.now()

    if not module.check_mode:
        rc, out, err = module.run_command(args, executable=executable, use_unsafe_shell=shell, encoding=None, data=stdin)
    elif creates or removes:
        rc = 0
        out = err = b'Command would have run if not in check mode'
    else:
        module.exit_json(msg="skipped, running in check mode", skipped=True)

    endd = datetime.datetime.now()
    delta = endd - startd

    result = dict(
        cmd=args,
        stdout=out.rstrip(b"\r\n"),
        stderr=err.rstrip(b"\r\n"),
        rc=rc,
        start=str(startd),
        end=str(endd),
        delta=str(delta),
        changed=True,
    )

    if rc != 0:
        module.fail_json(msg='non-zero return code', **result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()