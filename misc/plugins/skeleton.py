### Basic plugin details

# A short name for the function. Will be displayed on successful loading of
# the function.
plugin_name = "Skeleton Sample Plugin"

# A list of the hooks this plugin has handlers for. Must still be a list even
# if it only has one item.
handles_hooks = ["send_status", "notify"]


### Handler functions (also put any needed imports in this section)

# This is a sample handler for a chained hook that doesn't actual do anything with its args.
def nomodify_notice(status_text):
    return status_text

# This is a sample handler for a non-chained hook that doesn't do anything with its args.
def false_notify(timeline_type):
    return


### Plugin interface functions

# Init function, takes plugin API version as argument. Should return required
# API version number if it needs a later version. Otherwise, it should try to
# initialize itself (if that's even necessary), and return either an error
# message (as a string) if something went wrong, or True if it completed
# initializing successfully (or there was nothing needed).
def init(plugin_api_version):
    if plugin_api_version >= 1:
        # do some set up if needed
        return True
    else:
        return 1

# Return handlers; either one, or a list of more than one, for hook hook_name,
# or None if it has no handlers for that hook. Python returns None by default
# if you don't explicitly return something, so in practice you just have to
# check for what you know you have handlers for, and ignore everything else.
def get_handlers(hook_name):
    if hook_name == "send_status":
        return [nomodify_notice]
    if hook_name == "notify":
        return [false_notify]
