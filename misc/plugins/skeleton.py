### Basic plugin details

# A short name for the function. Will be displayed on successful loading of
# the function.
plugin_name = "Skeleton Sample Plugin"

# A list of the hooks this plugin has handlers for. Must still be a list even
# if it only has one item.
handles_hooks = ["send_status"]


### Handler functions (also put any needed imports in this section)

# This is a sample handler that doesn't actual do anything with its args.
def nomodify_notice(status_text):
    return status_text


### Plugin interface functions

# Init function, takes plugin API version as argument. Should return False if
# it needs a later API version. Otherwise it should do some basic set up (if
# the plugin needs any), and then return True.
def init(plugin_api_version):
    if plugin_api_version >= 1:
        # do some set up if needed
        return True
    else:
        return False

# Return a list of handlers for hook hook_name (as before, must be a list
# regardless of number of items), or None if it has no handlers for that
# hook/type combination. Python returns None by default if you don't explicitly
# return something, so in practice you just have to check for what you know you
# have handlers for, and ignore everything else.
# handler_type is the type of handler to return (as of API v1, the only types
# are "start" and "end").
def get_handlers(hook_name, handler_type):
    if hook_name == "send_status" and handler_type == "start":
        return [nomodify_notice]
