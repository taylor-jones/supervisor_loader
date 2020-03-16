# supervisor_loader

supervisor_loader is an xml-rpc extension for supervisor that allows for dynamically adding or removing program groups, program, and/or processes to the supervisor configuration at runtime.

## Credit

This program is an adaptaptation, heavily based on ideas from the following projects:
* [supervisor_twiddler](https://github.com/mnaberez/supervisor_twiddler/blob/master/supervisor_twiddler/rpcinterface.py)
* [supervisor_cache](https://github.com/mnaberez/supervisor_cache)

## Configuration

To use supervisor_loader, add the following to your supervisor configuration:

```ini
[rpcinterface:loader]
supervisor.rpcinterface_factory = supervisor_loader.rpcinterface:make_loader_rpcinterface
```

## Usage

After adding `supervisor_loader` to your supervisor configuration, you can then reference the `loader` object in an xml-rpc connection to the supervisor server, just as you would the `supervisor` object:

```python
import sys

# import the appropriate ServerProxy depending
# on whether we're using python2 or python3
if sys.version_info > (2, 7):
    from xmlrpc.client import ServerProxy
else:
    from xmlrpclib import ServerProxy

# connect to supervisor via xmlrpc
server = ServerProxy('http://localhost:9001/RPC2')
supervisor = server.supervisor
loader = server.loader
system = server.system

# creating an example group and process
group_name = 'mygroup'
process_name = 'fizzbuzz'
process_conf = {
    'command': 'fizzbuzz.py',
    'autostart': 'true',
    'autorestart': 'false',
    'environment': 'PYTHONUNBUFFERED=1',
    'priority': '1',
    'startsecs': '0',
    'startretries': '0',
    'stopwaitsecs': '0',
    'exitcodes': '0,1,2',
    'redirect_stderr': 'true',
    'stderr_logfile': 'NONE',
    'stdout_logfile': '%(ENV_LOGDIR)s/%(program_name)s_%(process_num)d.log',
    'stdout_events_enabled': 'true',
    'stderr_events_enabled': 'true',
    'process_name': '%(program_name)s_%(process_num)d',
}

# Check if a group exists
loader.hasGroup(group_name)    # False
loader.addGroup(group_name)
loader.hasGroup(group_name)    # True

# Check if a program exists within a group
loader.hasProcessInGroup(group_name, process_name)    # False
loader.addProgramToGroup(group_name, process_name, process_conf)    # fizzbuzz_1
loader.hasProcessInGroup(group_name, process_name)    # True

# Get group names
loader.getgroup_names()  # ['mygroup']

# Add another instance of the same process
loader.addProgramToGroup(group_name, process_name, process_conf)    # fizzbuzz_2
```

## API

TODO: improve documentation

* getAPIVersion
* getGroupNames
* log
* addGroup
* addProgramToGroup
* TODO: removeProcessFromGroup
