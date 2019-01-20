import os
import logging
import logging.handlers


def setLogger(logpath, logLevel="INFO", when='midnight', backupCount=30):  
    logger = logging.getLogger()
    logger.setLevel(logLevel)
    
    if 'DEBUG' == logLevel:
        handler = logging.StreamHandler()
    else:
        dname = os.path.dirname(logpath)
        if dname and not os.path.isdir(dname):
            os.makedirs(dname, 0755)
        handler = logging.handlers.TimedRotatingFileHandler(
            filename = logpath,
            when = when,
            backupCount = backupCount,
        )
    handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(filename)s-line%(lineno)d %(levelname)s: %(message)s')
    )
    logger.addHandler( handler )  