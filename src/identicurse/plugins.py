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

def register(hook_name, plugin_start_function=None, plugin_end_function=None):
    """Registers a start and end function (both are optional) for hook-point hook_name."""
    if not hook_name in config.session_store.plugin_hooks:
        config.session_store.plugin_hooks[hook_name] = {"start": [], "end": []}

    if plugin_start_function is not None:
        config.session_store.plugin_hooks[hook_name]["start"].append(plugin_start_function)
    if plugin_end_function is not None:
        config.session_store.plugin_hooks[hook_name]["end"].append(plugin_end_function)

def normalise_args(args):
    """Helper function to ensure args is always in correct list form."""
    if type(args) == type(()):  # if args is a tuple
        args = list(args)  # turn it into a list
    elif type(args) != type([]):  # if it's not, and also not a list
        args = [args]  # encase it in one
    return args

def hook_point(hook_name, *args):
    """Runs all start functions for hook-point hook_name in a chain, passing the return from
    each into the next one (all handlers, by definition, have the same argument pattern as
    return pattern). Takes an arbitrary number of additional arguments which are passed down
    into the start functions. Returns input unchanged on finding no plugins to run, otherwise
    returns the last start function in the chain's return. Additionally, some hook points may
    have no end-point. These are single-point hooks, and all use only start functions."""
    try:
        start_functions = config.session_store.plugin_hooks[hook_name]["start"]
    except KeyError:  # getting hook_name's start_function list failed, no entry for that hook
        return args
    for start_function in start_functions:
        try:
            args = normalise_args(args)
            args = start_function(*args)
        except TypeError:
            pass  # this function failed, just move on to the next
    return normalise_args(args)

def hook_point_end(hook_name, *args):
    """Runs all end functions for hook-point hook_name in a chain, passing the return from
    each into the next one (all handlers, by definition, have the same argument pattern as
    return pattern). Takes an arbitrary number of additional arguments which are passed down
    into the end functions. Returns input unchanged on finding no plugins to run, otherwise
    returns the last end function in the chain's return."""
    try:
        end_functions = config.session_store.plugin_hooks[hook_name]["end"]
    except KeyError:  # getting hook_name's end_function list failed, no entry for that hook
        return list(args)
    for end_function in end_functions:
        try:
            args = normalise_args(args)
            args = end_function(*args)
        except TypeError:
            pass  # this function failed, just move on to the next
    return normalise_args(args)


def load_plugin(plugin_filename):
    plugin_filename = os.path.abspath(plugin_filename)
    plugin_modulename = os.path.basename(plugin_filename)[:-3]  # all plugins must end with ".py", so [:-3] removes that to get a valid module name
    plugin_file = None
    try:
        plugin_file = open(plugin_filename, "r")
        plugin = imp.load_source(plugin_modulename, plugin_filename, plugin_file)
        # if we get here, we loaded successfully, so load the plugin fully
        if plugin.init(PLUGIN_API_VERSION):
            hooks = plugin.handles_hooks
            for hook in hooks:
                start_handlers = plugin.get_handlers(hook, "start")
                if start_handlers is not None:
                    for handler in start_handlers:
                        register(hook, plugin_start_function=handler)
                end_handlers = plugin.get_handlers(hook, "end")
                if end_handlers is not None:
                    for handler in end_handlers:
                        register(hook, plugin_end_function=handler)
            print "Successfully loaded plugin '%s'." % (plugin.plugin_name)
        else:
            print "Plugin '%s' requires a later plugin API (this version of IdentiCurse has plugin API v%d), so was not loaded." % (plugin.plugin_name, PLUGIN_API_VERSION)
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
