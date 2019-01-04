import os
import shutil

def ensure_dir(f):
    d = os.path.realpath(f)
    if not os.path.exists(d):
        os.makedirs(d,mode=0755)
        
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