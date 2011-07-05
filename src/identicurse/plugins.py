# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
# 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU General Public License for more details. 
# 
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import config, os.path, imp, glob
PLUGIN_API_VERSION = 1

def register(hook_name, handler):
    """Registers a handler for hook-point hook_name."""
    if not hook_name in config.session_store.plugin_hooks:
        config.session_store.plugin_hooks[hook_name] = [handler]
    else:
        config.session_store.plugin_hooks[hook_name].append(handler)

def normalise_chain_args(args):
    """Helper function to ensure args for chained hooks are always in correct list form."""
    if type(args) == type(()):  # if args is a tuple
        args = list(args)  # turn it into a list
    elif type(args) != type([]):  # if it's not, and also not a list
        args = [args]  # encase it in one
    return args

def chained_hook_point(hook_name, *args):
    """Runs all handlers for chained hook-point hook_name in a chain, passing the return from
    each into the next one (all chained handlers, by definition, have the same argument pattern
    as return pattern). Takes an arbitrary number of additional arguments which are passed down
    into the handlers. Returns input unchanged on finding no plugins to run, otherwise returns
    whatever the last handler in the chain returned."""
    try:
        handlers = config.session_store.plugin_hooks[hook_name]
    except KeyError:  # getting hook_name's handler list failed, no entry for that hook
        return args
    for handler in handlers:
        try:
            args = normalise_chain_args(args)
            args = handler(*args)
        except TypeError:
            pass  # this function failed, just move on to the next
    return normalise_chain_args(args)

def hook_point(hook_name, *args):
    """Runs all handlers for hook-point hook_name in sequence, returning a list comprising all
    non-None returned objects/values. Unlike chained hook-points, the handlers' return may be
    completely different in layout to the arguments, or even non-existent."""
    responses = []
    try:
        handlers = config.session_store.plugin_hooks[hook_name]
    except KeyError:  # getting hook_name's handler list failed, no entry for that hook
        return responses
    for handler in handlers:
        try:
            response = handler(*args)
            if response is not None:
                responses.append(response)
        except TypeError:
            pass  # this function failed, just move on to the next
    return responses

def load_plugin(plugin_filename):
    plugin_filename = os.path.abspath(plugin_filename)
    plugin_modulename = os.path.basename(plugin_filename)[:-3]  # all plugins must end with ".py", so [:-3] removes that to get a valid module name
    plugin_file = None
    try:
        plugin_file = open(plugin_filename, "r")
        plugin = imp.load_source(plugin_modulename, plugin_filename, plugin_file)
        # if we get here, we loaded successfully, so load the plugin fully
        init_val = plugin.init(PLUGIN_API_VERSION)
        if init_val == True:
            hooks = plugin.handles_hooks
            for hook in hooks:
                handlers = plugin.get_handlers(hook)
                if handlers is not None:
                    if type(handlers) in (type([]), type(())):
                        for handler in handlers:
                            register(hook, handler)
                    else:
                        register(hook, handlers)
            print "Successfully loaded plugin '%s'." % (plugin.plugin_name)
        elif type(init_val) == type(1):
            print "Plugin '%s' requires plugin API v%d or greater (this version of IdentiCurse has plugin API v%d), so was not loaded." % (plugin.plugin_name, init_val, PLUGIN_API_VERSION)
        else:
            if init_val is None:
                init_val = "Unknown reason."
            print "Plugin '%s' failed to load: %s" % (plugin.plugin_name, str(init_val))
    except ImportError, e:
        print "Failed to load plugin '%s': %s" % (plugin_filename, str(e))
    finally:
        if plugin_file:
            plugin_file.close()

def load_all():
    if not hasattr(config.session_store, "plugin_hooks"):
        config.session_store.plugin_hooks = {}

    plugin_dir = os.path.abspath(os.path.join(config.config.basedir, "plugins"))
    for filename in glob.glob(os.path.join(plugin_dir, "*.py")):
        if not os.path.isfile(filename):
            continue
        load_plugin(filename)
