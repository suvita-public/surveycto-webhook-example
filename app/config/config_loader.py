import configparser
import logging
import logging.config
import os


def getconfigs(config_file_name):
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, config_file_name)
    with open(config_path, encoding="utf-8-sig") as fp:
        config.read_file(fp)

    dict_configs_temp = {}
    for section in config.sections():
        dict_configs_temp[section] = dict(config.items(section))

    return dict_configs_temp


def getlogger(log_file_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, log_file_name)
    with open(log_path, encoding="utf-8-sig") as fp:
        logging.config.fileConfig(fp, disable_existing_loggers=False)
    return logging.getLogger("file_logger")


def getlogobject(section_name):
    log_file_name = dict_configs[section_name]["log_file_path"]
    return getlogger(log_file_name)


dict_configs = getconfigs("appconfig.ini")
logger = getlogobject("logging")

__all__ = ["logger", "dict_configs", "getlogobject"]
