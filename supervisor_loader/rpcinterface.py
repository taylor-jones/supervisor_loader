from supervisor.options import UnhosedConfigParser
from supervisor.options import ProcessGroupConfig
from supervisor.datatypes import list_of_strings
from supervisor.states import SupervisorStates
from supervisor.states import ProcessStates
from supervisor.states import STOPPED_STATES
from supervisor.xmlrpc import Faults as SupervisorFaults
from supervisor.xmlrpc import RPCError
import supervisor.loggers

API_VERSION = "1.0"

class Faults:
    NOT_IN_WHITELIST = 230

class LoaderNamespaceRPCInterface:
    """
    A supervisor rpc interface that provides additional functionality
    for dynamically adding groups and programs to the the supervisor
    configuration at runtime.
    """

    def __init__(self, supervisord, whitelist=[]):
        self.supervisord = supervisord
        self._whitelist = list_of_strings(whitelist)


    def _update(self, func_name):
        """
        Sets the update text to send via the rpc interface. Checks to ensure
        supervisor isn't in the middle of shutting down and that the argued
        function is allowed to be executed.
        
        Arguments:
            func_name {str} -- the name of the method for supervisor to call
            
        Raises:
            RPCError: SHUTDOWN_STATE if supervisor is in the middle of 
                shutting down
            RPCError: NOT_IN_WHITELIST if a whitelist of methods has been
                specified and the given func_name is not in the whitelist
        """
        self.update_text = func_name

        state = self.supervisord.get_state()
        if state == SupervisorStates.SHUTDOWN:
            raise RPCError(SupervisorFaults.SHUTDOWN_STATE)

        if len(self._whitelist) and func_name not in self._whitelist:
            raise RPCError(Faults.NOT_IN_WHITELIST, func_name)


    def getAPIVersion(self):
        """
        Returns the version of the RPC API used by supervisor_loader

        Returns:
            str -- the version id of supervisor_loader
        """
        self._update("getAPIVersion")
        return API_VERSION


    def getGroupNames(self):
        """
        Returns an list of the names of supervisor process groups.
        
        Returns:
            list -- the names of supervisor process groups
        """
        self._update("getGroupNames")
        return list(self.supervisord.process_groups.keys())


    def log(self, message, level=supervisor.loggers.LevelsByName.INFO):
        """
        Writes a message to the main supervisor log.

        Arguments:
            message {str} -- the message to log

        Keyword Arguments:
            level {str|int} -- the log level to which this message should be
                applied (e.g. INFO, 20, etc) (default: {INFO})

        Returns:
            bool -- True if no error occurs, False if an error occurs
        """
        self._update("log")

        if isinstance(level, str):
            log_levels = supervisor.loggers.LevelsByName
            level = getattr(log_levels, level.upper(), None)

        if supervisor.loggers.LOG_LEVELS_BY_NUM.get(level, None) is None:
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS)

        self.supervisord.options.logger.log(level, message)
        return True


    def addProgramToGroup(self, program_name, program_conf, group_name=None):
        """
        Adds a new program to an (optionally) existing process group. If no 
        process group is specified, we'll first look to see if a process group 
        exists that matches the process name. If so, we'll add the process to 
        the existing group. If no matching group already exists, we'll create 
        one and then add the process to the newly-created group.

        Arguments:
            program_name {str} -- the name of the program
            program_conf {dict} -- the program's configuration, which includes
                all available options from a typeical supervisord.conf config
        
        Keyword Arguments:
            group_name {str} -- the group name to add the program to (default: {None})
        
        Raises:
            RPCError: INCORRECT_PARAMETERS if program config is invalid
            RPCError: BAD_NAME if the program already exists
        
        Returns:
            bool -- True if no error occurs, False if an error occurs
        """
        self._update("addProgramToGroup")

        # fall back to the program name if no group name was argued
        group_name = group_name or program_name
        group = self._ensureProcessGroup(group_name)

        # make a configparser instance for program options
        section_name = "program:%s" % program_name
        parser = self._makeConfigParser(section_name, program_conf)

        # make process configs from a parser instance
        options = self.supervisord.options
        try:
            new_configs = options.processes_from_section(
                parser, section_name, group_name
            )
        except ValueError as e:
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS, e)

        # make sure the desired process name doesn't already exist
        for new_config in new_configs:
            for existing_config in group.config.process_configs:
                if new_config.name == existing_config.name:
                    raise RPCError(SupervisorFaults.BAD_NAME, new_config.name)

        # add the process configurations
        group.config.process_configs.extend(new_configs)

        for new_config in new_configs:
            # the process group config already exists, so its after_setuid hook
            # will not be called again to make the auto child logs for this
            # process.
            new_config.create_autochildlogs()

            # add process instance
            group.processes[new_config.name] = new_config.make_process(group)

        return True


    def removeProcessFromGroup(self, group_name, process_name):
        """
        Removes a process from a process group. When a program is added with
        addProgramToGroup(), one or more processes for that program are added
        to the group.  This method removes individual processes (named by the
        numprocs and process_name options), not programs.
        
        Arguments:
            group_name {str} -- name of the group to remove
            process_name {str} -- name of the process to remove from the group
        
        Raises:
            RPCError: BAD_NAME if the process does not exist
            RPCError: STILL_RUNNING if the process is still running
        
        Returns:
            bool -- True if no error, False if error
        """
        
        self._update("removeProcessFromGroup")

        group = self._getProcessGroup(group_name)
        process = group.processes.get(process_name)
        
        # make sure the process exists
        if process is None:
            raise RPCError(SupervisorFaults.BAD_NAME, process_name)
        
        # make sure the process isn't still running
        if process.pid or process.state not in STOPPED_STATES:
            raise RPCError(SupervisorFaults.STILL_RUNNING, process_name)

        group.transition()

        # delete process config from group, then delete process
        for index, config in enumerate(group.config.process_configs):
            if config.name == process_name:
                del group.config.process_configs[index]

        del group.processes[process_name]
        return True


    def addGroup(self, name, priority=999):
        """
        Adds a new supervisor process group.
        
        Arguments:
            name {str} -- the name of the process group to add
        
        Keyword Arguments:
            priority {int} -- priority to assign to the  group (default: {999})
        
        Raises:
            RPCError: ALREADY_ADDED if group already exists
        
        Returns:
            bool -- True if no error occurs, False if error occurs
        """
        self._update("addGroup")

        options = self.supervisord.options
        group_config = None

        for config in options.process_group_configs:
            if name == config.name:
                group_config = config
                break

        if not group_config:
            group_config = ProcessGroupConfig(
                options, name, priority, process_configs=[]
            )
            self.supervisord.options.process_group_configs.append(group_config)

        if name not in self.supervisord.process_groups:
            group_config.after_setuid()
            self.supervisord.process_groups[name] = group_config.make_group()
        else:
            raise RPCError(SupervisorFaults.ALREADY_ADDED, name)

        return True


    def _getProcessGroup(self, name):
        """
        Finds a process group, given the process group's name
        
        Arguments:
            name {str} -- the name of the process group
        
        Raises:
            RPCError: Raises error if no matching process group is found
        
        Returns:
            object -- supervisor process group
        """
        group = self.supervisord.process_groups.get(name)
        if group is None:
            raise RPCError(SupervisorFaults.BAD_NAME, "group: %s" % name)
        return group


    def _ensureProcessGroup(self, name):
        """
        Checks if a given process group exists. If not, the group is created.
        
        Arguments:
            name {str} -- The name of the process group
        
        Raises:
            RPCError: Raises error if group could not be ensured to exist
        
        Returns:
            object -- a supervisor group object
        """
        group = self.supervisord.process_groups.get(name)
        if group is None:
            self.addGroup(name)
            group = self.supervisord.process_groups.get(name)
        return group


    def _makeConfigParser(self, section_name, options):
        """
        Populate a new UnhosedConfigParser instance with a section built 
        from an options dict.
        
        Arguments:
            section_name {str} -- the name of the section
            options {dict} -- options used to populate the section
        
        Raises:
            RPCError: Raises error if section parameters are invalid
        
        Returns:
            object
        """
        config = UnhosedConfigParser()

        try:
            config.add_section(section_name)
            for k, v in dict(options).items():
                config.set(section_name, k, v)
        except (TypeError, ValueError):
            raise RPCError(SupervisorFaults.INCORRECT_PARAMETERS)

        return config


def make_loader_rpcinterface(supervisord, **config):
    return LoaderNamespaceRPCInterface(supervisord, **config)
