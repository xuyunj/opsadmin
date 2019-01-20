#coding: utf-8
import os
import json
import shutil
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.module_utils.six import string_types
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
import ansible.constants as C



class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    
    results = {}
    
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        #print(json.dumps({host.name: result._result}, indent=4))
        self.results[result._host.get_name()] = {'status': 'ok', 'result': result._result }
        
    def runner_on_failed(self, host, res, ignore_errors=False):
        self.results[host] = {'status': 'failed', 'result':res}
        
    def runner_on_unreachable(self, host, res):
        self.results[host] = {'status': 'unreachable', 'result':res}
        
    def v2_playbook_on_no_hosts_matched(self):
        pass
        
    def v2_playbook_on_play_start(self, play):
        pass
        
        
class MyInventory(InventoryManager):
    
    def __init__(self, resource, loader ):
        """ 
        :arg list resource: Each element is a machine attribute dictionary. for example,
            [{"host": "192.168.75.129", "port": "22", "username": "service", "password": "pass"}, ...] 
        """
        self.resource = resource
        super(MyInventory, self).__init__(loader)
        self.load_run_host()
         
    def load_run_host(self):
        """ 
        add hosts to inventory. 
        """
        for h in self.resource:
            host = h.get('host')
            if not host or host in self.hosts:
                continue
            self.add_host(host, group='ungrouped', port=h.get('port'))
            for key, value in h.items():
                self._inventory.hosts[host].set_variable('ansible_ssh_' + key, value)
            
            
class AnsibleAPI(object):
    """ 
    This is a General object for parallel execute modules. 
    """

    def __init__(self, resource, passwords=None, *args, **kwargs):
        module_path = [
            os.path.abspath( os.path.join(os.path.dirname(os.path.abspath(__file__)), '../modules') ),
        ]
        self.passwords = {} if not passwords else passwords
        
        # since API is constructed for CLI it expects certain options to always be set, named tuple 'fakes' the args parsing options object
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become','become_method',
                             'become_user', 'check', 'diff', 'listhosts', 'listtasks', 'listtags','syntax' ])
        self.options = Options( 
                         connection = 'myparamiko',
                         module_path=module_path, 
                         forks=10, 
                         become=None,
                         become_method=None,
                         become_user=None, 
                         check=False, 
                         diff=False, 
                         listhosts=None, 
                         listtasks=None, listtags=None, syntax=None)
        self.loader = DataLoader()
        self.inventory = MyInventory(resource, self.loader)
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)
        self.callback = ResultCallback()

    def run(self, module_name, module_args, extra_vars={}):
        """ 
        run module from andible ad-hoc. 
        :arg string module_name: ansible module_name 
        :arg string module_args: ansible module args 
        """
        run_host_list = [x.name for x in self.inventory.get_hosts()]
        # create datastructure that represents our play, including tasks, this is basically what our YAML loader does internally.
        play_source =  dict(
                name = "Ansible Play",
                hosts = run_host_list,
                gather_facts = 'no',
                tasks=[
                    dict(action=dict(module=module_name, args=module_args)),
                ]
            )
        self.variable_manager.extra_vars = extra_vars
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        # Run it - instantiate task queue manager, which takes care of forking and setting up all objects to iterate over host list and tasks
        tqm = None
        #self.callback = ResultCallback()
        try:
            tqm = TaskQueueManager(
                    inventory=self.inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=self.options,
                    passwords=self.passwords,
                    stdout_callback=self.callback,  # Use our custom callback instead of the ``default`` callback plugin, which prints to stdout
                )
            result = tqm.run(play) # most interesting data for a play is actually sent to the callback's methods
        finally:
            # we always need to cleanup child procs and the structres we use to communicate with them
            if tqm is not None:
                tqm.cleanup()
        
            # Remove ansible tmpdir
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    def run_playbook(self, playbooks, extra_vars={}):
        """ 
        run ansible palybook 
        :arg list playbooks: playbook files. for example, ['/user/share/playbooks/test.yaml', ]
        """
        try:
            # --extra-vars "port='8090' "
            self.variable_manager.extra_vars = extra_vars
            executor = PlaybookExecutor(
                    playbooks, 
                    self.inventory, 
                    self.variable_manager, 
                    self.loader, self.options, 
                    self.passwords
                )
            executor._tqm._stdout_callback = self.callback
            result = executor.run()
        except Exception, e:
            print "error:",e.message
        return self.callback.results
        
    def put_file(self, src, dest, extra=None):
        """
        Ansible copy file
        """
        module_args = "src=%s  dest=%s"%(src, dest)
        self.run('copy', module_args)
        return self.callback.results
        
    def get_file(self, src, dest, extra=None):
        """
        Ansible fetch file
        """
        module_args = "src=%s dest=%s flat=yes" % (src, dest)
        self.run('fetch', module_args)
        return self.callback.results
        
    def exec_command(self, cmd):
        """
        Ansible commands
        """
        self.run('command', cmd)
        return self.callback.results

    def exec_shell(self, path):
        """
        Ansible shell
        """
        self.run('shell', path)
        return self.callback.results
        
    def exec_timely_command(self, cmd, url, name, uid ):
        """
        Timely output script execution information.
        """
        module_args = 'command="%s" url=%s name=%s uid=%s' %(cmd, url, name, uid)
        self.run('my_command', module_args)
        return self.callback.results
    
    
