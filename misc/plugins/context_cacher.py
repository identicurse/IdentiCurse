### Basic plugin details

plugin_name = "Context Cacher"
handles_hooks = ["populate_timeline", "populated_timeline"]


### Handler functions (also put any needed imports in this section)

cached_contexts = {}

def cached_context(timeline_type, timeline, page, count, since_id, type_params, changed):
    if timeline_type == "context":
        notice_id = type_params["notice_id"]

    if timeline_type != "context" or ((not notice_id in cached_contexts) and (len(timeline) == 0)):  # not context or not filled yet
        return timeline_type, timeline, page, count, since_id, type_params, changed
    else:
        return timeline_type, cached_contexts[notice_id], page, count, since_id, type_params, True

def cache_context(timeline_type, timeline, type_params):
    if timeline_type == "context":
        notice_id = type_params["notice_id"]
        cached_contexts[notice_id] = timeline


### Plugin interface functions

def init(plugin_api_version):
    if plugin_api_version >= 1:
        return True
    else:
        return 1

def get_handlers(hook_name):
    if hook_name == "populate_timeline":
        return [cached_context]
    if hook_name == "populated_timeline":
        return [cache_context]
