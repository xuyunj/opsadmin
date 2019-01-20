import os
import shutil
from django.conf import settings

def ensure_dir(f):
    d = os.path.realpath(f)
    if not os.path.exists(d):
        os.makedirs(d,mode=0755)
        
def clear_cachr_dir(name, uid):
    cachedir = os.path.join(settings.COMMAND_TIMELY_RECORD, name, uid )
    if os.path.exists(cachedir):
        shutil.rmtree( cachedir  )
        
def get_version(path):
    """
    Get current deploy version.
    :arg path string: The file path that records version information.
    :return version string
    """
    version = None
    with open(path) as f:
        version = f.read()
    return version.strip()
    
def filter_path(path, filter = []):
    """
    Filter the specified directory.
    :arg path string
    :arg filter list
    """
    filesize = 0
    version = None
    for root, dirs, files in os.walk(path):
    
        #[ os.remove(root, name ) for name in dirs if name in filter]
        for file in files:
            if 'version' == file:
                version = get_version( os.path.join(root, file) )
            filesize += os.path.getsize( os.path.join(root, file ) ) 
            
        for dirname in dirs:
            if dirname not in filter:
                #os.path.getsize(pathTmp)  
                continue
            shutil.rmtree( os.path.join(root, dirname) )
    return version,filesize
    
def writedoc2unix(filepath, content ):
    """
    Doc formats Convert to unix formats.
    :arg string: File absolute path.
    :content string: File content from web client.
    """
    unix_content = ""
    for line in content.split('\r\n'):
        unix_content += line.rstrip() + "\n"
    with open(filepath, 'w') as f:
        f.write( unix_content )
