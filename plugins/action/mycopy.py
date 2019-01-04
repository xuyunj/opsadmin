
# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
import os.path
import stat
import tempfile
import traceback

from ansible import constants as C
from ansible.errors import AnsibleError, AnsibleFileNotFound
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.utils.hashing import checksum
from ansible.plugins.loader import callback_loader
from ansible.plugins.action.copy import _create_remote_file_args,_create_remote_copy_args
from ansible.plugins.action.copy import ActionModule as CopyModule


class ActionModule(CopyModule):

    def _transfer_file(self, local_path, remote_path, callback=None):
        self._connection.put_file(local_path, remote_path, callback )
        return remote_path
    
    def _copy_file(self, source_full, source_rel, content, content_tempfile,
                   dest, task_vars, follow):
        decrypt = boolean(self._task.args.get('decrypt', True), strict=False)
        force = boolean(self._task.args.get('force', 'yes'), strict=False)
        raw = boolean(self._task.args.get('raw', 'no'), strict=False)

        result = {}
        result['diff'] = []
                
        def callback(value, total ):
            for callback_plugin in callback_loader.all(class_only=True):
                plugin_func = getattr(callback_plugin, 'runner_on_rate', None)
                if plugin_func:
                    extra = dict(appid=task_vars['appid'], 
                                 name=os.path.basename(source_full),
                                 socketid=task_vars['webscoketid'],
                                 allsize=task_vars['total'] )
                    plugin_func( value, total, **extra )
                    break
            
        # If the local file does not exist, get_real_file() raises AnsibleFileNotFound
        try:
            source_full = self._loader.get_real_file(source_full, decrypt=decrypt)
        except AnsibleFileNotFound as e:
            result['failed'] = True
            result['msg'] = "could not find src=%s, %s" % (source_full, to_text(e))
            return result

        # Get the local mode and set if user wanted it preserved
        # https://github.com/ansible/ansible-modules-core/issues/1124
        lmode = None
        if self._task.args.get('mode', None) == 'preserve':
            lmode = '0%03o' % stat.S_IMODE(os.stat(source_full).st_mode)

        # This is kind of optimization - if user told us destination is
        # dir, do path manipulation right away, otherwise we still check
        # for dest being a dir via remote call below.
        if self._connection._shell.path_has_trailing_slash(dest):
            dest_file = self._connection._shell.join_path(dest, source_rel)
        else:
            dest_file = dest

        # Attempt to get remote file info
        dest_status = self._execute_remote_stat(dest_file, all_vars=task_vars, follow=follow, checksum=force)

        if dest_status['exists'] and dest_status['isdir']:
            # The dest is a directory.
            if content is not None:
                # If source was defined as content remove the temporary file and fail out.
                self._remove_tempfile_if_content_defined(content, content_tempfile)
                result['failed'] = True
                result['msg'] = "can not use content with a dir as dest"
                return result
            else:
                # Append the relative source location to the destination and get remote stats again
                dest_file = self._connection._shell.join_path(dest, source_rel)
                dest_status = self._execute_remote_stat(dest_file, all_vars=task_vars, follow=follow, checksum=force)

        if dest_status['exists'] and not force:
            # remote_file exists so continue to next iteration.
            return None

        # Generate a hash of the local file.
        local_checksum = checksum(source_full)

        if local_checksum != dest_status['checksum']:
            # The checksums don't match and we will change or error out.

            if self._play_context.diff and not raw:
                result['diff'].append(self._get_diff_data(dest_file, source_full, task_vars))

            if self._play_context.check_mode:
                self._remove_tempfile_if_content_defined(content, content_tempfile)
                result['changed'] = True
                return result

            # Define a remote directory that we will copy the file to.
            tmp_src = self._connection._shell.join_path(self._connection._shell.tmpdir, 'source')

            remote_path = None

            if not raw:
                remote_path = self._transfer_file(source_full, tmp_src, callback)
            else:
                self._transfer_file(source_full, dest_file, callback)

            # We have copied the file remotely and no longer require our content_tempfile
            self._remove_tempfile_if_content_defined(content, content_tempfile)
            self._loader.cleanup_tmp_file(source_full)

            # fix file permissions when the copy is done as a different user
            if remote_path:
                self._fixup_perms2((self._connection._shell.tmpdir, remote_path))

            if raw:
                # Continue to next iteration if raw is defined.
                return None

            # Run the copy module

            # src and dest here come after original and override them
            # we pass dest only to make sure it includes trailing slash in case of recursive copy
            new_module_args = _create_remote_copy_args(self._task.args)
            new_module_args.update(
                dict(
                    src=tmp_src,
                    dest=dest,
                    _original_basename=source_rel,
                    follow=follow
                )
            )
            if not self._task.args.get('checksum'):
                new_module_args['checksum'] = local_checksum

            if lmode:
                new_module_args['mode'] = lmode

            module_return = self._execute_module(module_name='copy', module_args=new_module_args, task_vars=task_vars)

        else:
            # no need to transfer the file, already correct hash, but still need to call
            # the file module in case we want to change attributes
            self._remove_tempfile_if_content_defined(content, content_tempfile)
            self._loader.cleanup_tmp_file(source_full)

            if raw:
                return None

            # Fix for https://github.com/ansible/ansible-modules-core/issues/1568.
            # If checksums match, and follow = True, find out if 'dest' is a link. If so,
            # change it to point to the source of the link.
            if follow:
                dest_status_nofollow = self._execute_remote_stat(dest_file, all_vars=task_vars, follow=False)
                if dest_status_nofollow['islnk'] and 'lnk_source' in dest_status_nofollow.keys():
                    dest = dest_status_nofollow['lnk_source']

            # Build temporary module_args.
            new_module_args = _create_remote_file_args(self._task.args)
            new_module_args.update(
                dict(
                    dest=dest,
                    _original_basename=source_rel,
                    recurse=False,
                    state='file',
                )
            )
            # src is sent to the file module in _original_basename, not in src
            try:
                del new_module_args['src']
            except KeyError:
                pass

            if lmode:
                new_module_args['mode'] = lmode

            # Execute the file module.
            module_return = self._execute_module(module_name='file', module_args=new_module_args, task_vars=task_vars)

        if not module_return.get('checksum'):
            module_return['checksum'] = local_checksum

        result.update(module_return)
        return result

    def _create_content_tempfile(self, content):
        ''' Create a tempfile containing defined content '''
        fd, content_tempfile = tempfile.mkstemp(dir=C.DEFAULT_LOCAL_TMP)
        f = os.fdopen(fd, 'wb')
        content = to_bytes(content)
        try:
            f.write(content)
        except Exception as err:
            os.remove(content_tempfile)
            raise Exception(err)
        finally:
            f.close()
        return content_tempfile
    