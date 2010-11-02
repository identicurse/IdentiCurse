#!/usr/bin/env python
import urllib, urllib2, json

class StatusNet():
    def __init__(self, api_path, username, password):
        import base64
        self.api_path = api_path
        self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
    
    def __makerequest(self, resource_path, raw_params={}):
        params = urllib.urlencode(raw_params)
        
        if len(params) > 0:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path), params)
        else:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path))
        request.add_header("Authorization", "Basic %s" % (self.auth_string))
        
        try:
            response = urllib2.urlopen(request)
            content = response.read()

            return json.loads(content)
        except:
            return []

    def statuses_update(self, status, source="", in_reply_to_status_id=""):
        params = {'status':status}
        if not (source == ""):
            params['source'] = source
        if not (in_reply_to_status_id == ""):
            params['in_reply_to_status_id'] = in_reply_to_status_id
        
        return self.__makerequest("statuses/update", params)
    
    def statuses_mentions(self, since_id="", max_id="", count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == ""):
            params['since_id'] = since_id
        if not (max_id == ""):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/mentions", params)


