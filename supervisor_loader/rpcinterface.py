from supervisor.options import UnhosedConfigParser
from supervisor.options import ProcessGroupConfig

from supervisor.states import SupervisorStates
from supervisor.states import STOPPED_STATES
from supervisor.xmlrpc import Faults
from supervisor.xmlrpc import RPCError
import supervisor.loggers

API_VERSION = '1.0'


class CountCache:
    """
    Maintains an integer count of the number of the number of
    process instances for any given program name.
    """
    def __init__(self):
        self._cache = {}

    def clear(self):
        self._cache.clear()
        
    def get(self, key):
        if key in self._cache:
            return self._cache[key]
        return 0

    def increment(self, key):
        if key in self._cache:
            self._cache[key] += 1
        else:
            self._cache[key] = 1

    def decrement(self, key):
        if key in self._cache:
            self._cache[key] -= 1
        if self._cache[key] == 0:
            del self._cache[key]

    def keys(self):
        return sorted(self._cache.keys())



class LoaderNamespaceRPCInterface:
    def __init__(self, supervisord, **kwargs):
        self.supervisord = supervisord
        self.numprocs = CountCache()


    def _update(self, function_name):
        self.update_text = function_name
        state = self.supervisord.get_state()

        if state == SupervisorStates.SHUTDOWN:
            raise RPCError(Faults.SHUTDOWN_STATE)


    def getAPIVersion(self):
        """
        Returns the version of the RPC API used by supervisor_loader
        
        Returns:
            str
        """
        self._update('getAPIVersion')
        return API_VERSION


    def getGroupNames(self):
        """
        Returns a list of the supervisor process groups.
        
        Returns:
            list
        """
        self._update('getGroupNames')
        return list(self.supervisord.process_groups.keys())


    def hasGroup(self, group_name):
        """
        Checks if a specified group exists in the supervisor configuration.
        
        Args:
            group_name (str): The name of the group to check for
        
        Returns:
            bool
        """
        group = self.supervisord.process_groups.get(group_name)
        return group is not None


    def hasProcessInGroup(self, group_name, process_name):
        """
        Checks if a specified process exists in a specified group
        
        Args:
            group_name (str): The name of the group
            process_name (str): The name of the process
        
        Returns:
            bool
        """
        try:
            group = self._get_process_group(group_name, False)
        except RPCError as e:
            return False
        return group.processes.get(process_name) is not None


    def log(self, message, level=supervisor.loggers.LevelsByName.INFO):
        """
        Writes a message to the main supervisor log.

        Args:
            message (str): The message to write.
            level (str, optional): The log level to assign to the message.
                Defaults to supervisor.loggers.LevelsByName.INFO.

        Raises:
            RPCError: INCORRECT_PARAMETERS if an invalid log level is provided

        Returns:
            boolean: True, unless an error was raised.
        """
        self._update('log')

        if isinstance(level, str):
            level = getattr(
                supervisor.loggers.LevelsByName, level.upper(), None)

        if supervisor.loggers.LOG_LEVELS_BY_NUM.get(level, None) is None:
            raise RPCError(Faults.INCORRECT_PARAMETERS)

        self.supervisord.options.logger.log(level, message)
        return True


    def addGroup(self, group_name, priority=999):
        """
        Adds a new process group to the supervisor configuration.
        
        Args:
            group_name (str): The name of the group to add.
            priority (int, optional): The group priority. Defaults to 999.
            
        Returns:
            (boolean) True, unless an error is raised.
        """
        self._update('addGroup')

        # make sure the group doesn't already exist
        if self.supervisord.process_groups.get(group_name) is not None:
            raise RPCError(Faults.ALREADY_ADDED, group_name)
        
        options = self.supervisord.options
        group_config = ProcessGroupConfig(
            options, group_name, priority, process_configs=[])
        self.supervisord.options.process_group_configs.append(group_config)
        group_config.after_setuid()
        self.supervisord.process_groups[group_name] = group_config.make_group()

        return True


    def _apply_process_num(self, config, process_num):
        # make sure the process_name is present
        config['process_name'] = '%(program_name)s_{0}'.format(process_num)

        # replace any instances of the process_num interpolation with the
        # determined process_num value
        target = '%(process_num)02d'
        for key, value in config.iteritems():
            config[key] = value.replace(target, process_num)
        
        return config


    def addProgramToGroup(self, group_name, program_name, program_options):
        """
        Adds a new program to an existing process group.
        
        Args:
            group_name (str): The name of the group to add this program to.
            program_name (str): The name of the program to add to supervisor.
            program_options (dict): The program configuration options.
        
        Returns:
            (boolean): True, unless an error is raised
        """
        self._update('addProgramToGroup')
        group = self._get_process_group(group_name, True)

        # determine the process name based on the current instances
        # of this program.
        current_program_instances = self.numprocs.get(program_name)
        process_num = '%d' % (current_program_instances + 1)
        self._apply_process_num(program_options, process_num)
        
        # make a configparser instance for the program
        section_name = 'program:%s' % program_name
        parser = self._make_config_parser(section_name, program_options)
        
        # make the process configs from the parser instance
        options = self.supervisord.options
        try:
            new_configs = options.processes_from_section(
                parser, section_name, group_name)
        except ValueError as e:
            raise RPCError(Faults.INCORRECT_PARAMETERS, e)
        
        # make sure the new program doesn't already exist in the group
        for new_config in new_configs:
            for existing_config in group.config.process_configs:
                if new_config.name == existing_config.name:
                    raise RPCError(Faults.BAD_NAME, new_config.name)

        # add the new program configuration(s) to the group
        group.config.process_configs.extend(new_configs)
        for new_config in new_configs:
            new_config.create_autochildlogs()
            group.processes[new_config.name] = new_config.make_process(group)
        
        self.numprocs.increment(program_name)
        return True


    def _get_process_group(self, group_name, create_group_if_not_exists=True):
        """
        Retrieves the process group config for a specified process group.
        
        Args:
            group_name (str): The name of the process group to get.

        Returns:
            (ProcessGroupConfig): The process group configuration
        """
        if not self.hasGroup(group_name):
            if create_group_if_not_exists:
                self.addGroup(group_name)
            else:
                raise RPCError(Faults.BAD_NAME, 'group: %s' % group_name)
        return self.supervisord.process_groups.get(group_name)


    def _make_config_parser(self, section_name, section_options):
        """
        Populates a new UnhosedConfigParser instance with a section
        built from a dict of section options.
        
        Args:
            section_name (str) -- The name of the section
            section_options (dict) -- The configuration options for the section

        Returns:
            config (supervisor.options.UnhosedConfgParser)

        Raises:
            RPCError: Raises error if section parameters are invalid
        """
        config = UnhosedConfigParser()
        try:
            config.add_section(section_name)
            for key, value in dict(section_options).items():
                config.set(section_name, key, value)
        except (TypeError, ValueError):
            raise RPCError(Faults.INCORRECT_PARAMETERS)
        return config



def make_loader_rpcinterface(supervisord, **config):
    return LoaderNamespaceRPCInterface(supervisord, **config)
