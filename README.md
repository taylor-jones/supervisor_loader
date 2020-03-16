# supervisor_loader

## Credit

This program is an adaptaptation, heavily based on ideas from the following projects:
* [supervisor_twiddler](https://github.com/mnaberez/supervisor_twiddler/blob/master/supervisor_twiddler/rpcinterface.py)
* [supervisor_cache](https://github.com/mnaberez/supervisor_cache)

supervisor_loader is an xml-rpc extension for supervisor that allows for dynamically adding or removing program groups, program, and/or processes to the supervisor configuration at runtime.

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

# adds two additional program configurations to supervisor.
loader.addProgramToGroup('foo', {"command": "pwd"})
loader.addProgramToGroup('bar', {"command": "ls"})

loader.getGroupNames()  # ['foo', 'bar']
```

## API

#### getAPIVersion

#### getGroupNames

#### log

#### addGroup

#### addProgramToGroup

#### removeProcessFromGroup
