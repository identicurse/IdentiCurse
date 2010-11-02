#!/usr/bin/env python
import urllib, urllib2, json

class StatusNet(object):
    def __init__(self, api_path, username, password):
        import base64
        self.api_path = api_path
        self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
        if not self.account_verify_credentials():
            raise Exception
    
    def __makerequest(self, resource_path, raw_params={}):
        params = urllib.urlencode(raw_params)
        
        if len(params) > 0:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path), params)
        else:
            request = urllib2.Request("%s/%s.json" % (self.api_path, resource_path))
        request.add_header("Authorization", "Basic %s" % (self.auth_string))
        
        response = urllib2.urlopen(request)
        content = response.read()
        
        return json.loads(content)


##############################
# TWITTER-COMPATIBLE METHODS #
##############################


######## Timeline resources ########

    def statuses_public_timeline(self):
        return self.__makerequest("statuses/public_timeline")

    def statuses_home_timeline(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        
        return self.__makerequest("statuses/home_timeline", params)

    def statuses_friends_timeline(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/friends_timeline", params)

    def statuses_mentions(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/mentions", params)

    def statuses_replies(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):  # alias of mentions
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/replies", params)

    def statuses_user_timeline(self, user_id=0, screen_name="", since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        if include_rts:
            params['include_rts'] = "true"
        
        return self.__makerequest("statuses/user_timeline", params)

### StatusNet does not implement this method yet
#    def statuses_retweeted_by_me(self, since_id=0, max_id=0, count=0, page=0):
#        params = {}
#        if not (since_id == 0):
#            params['since_id'] = since_id
#        if not (max_id == 0):
#            params['max_id'] = max_id
#        if not (count == 0):
#            params['count'] = str(count)
#        if not (page == 0):
#            params['page'] = str(page)
#        
#        return self.__makerequest("statuses/retweeted_by_me", params)

### StatusNet does not implement this method yet
#    def statuses_retweeted_to_me(self, since_id=0, max_id=0, count=0, page=0):
#        params = {}
#        if not (since_id == 0):
#            params['since_id'] = since_id
#        if not (max_id == 0):
#            params['max_id'] = max_id
#        if not (count == 0):
#            params['count'] = str(count)
#        if not (page == 0):
#            params['page'] = str(page)
#        
#        return self.__makerequest("statuses/retweeted_to_me", params)

    def statuses_retweets_of_me(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        
        return self.__makerequest("statuses/retweets_of_me", params)


######## Status resources ########
    
    # statuses/show

    def statuses_update(self, status, source="", in_reply_to_status_id=0):
        params = {'status':status}
        if not (source == ""):
            params['source'] = source
        if not (in_reply_to_status_id == 0):
            params['in_reply_to_status_id'] = in_reply_to_status_id
        
        return self.__makerequest("statuses/update", params)
    
    # statuses/destroy

    def statuses_retweet(self, id):
        params = {'id':id}
        return self.__makerequest("statuses/retweet", params)


######## User resources ########

    # statuses/friends

    # statuses/followers

    # users/show


######## Direct message resources ########

    def direct_messages(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = str(count)
        if not (page == 0):
            params['page'] = str(page)
        
        return self.__makerequest("direct_messages", params)

    # direct_messages/sent

    def direct_messages_new(self, screen_name, user_id, text):
        params = {'screen_name':screen_name, 'user_id':user_id, 'text':text}
        
        return self.__makerequest("direct_messages/new", params)

    # direct_messages/destroy -- NOT IMPLEMENTED BY STATUSNET


######## Friendships resources ########

    # friendships/create
    
    # friendships/destroy
    
    # friendships/exists

    # friendships/show


######## Friends and followers resources ########

    # friends/ids

    # followers/ids


######## Account resources ########

    def account_verify_credentials(self):
        try:
            result = self.__makerequest("statuses/public_timeline")
            return True
        except:
            return False

    # account/end_session -- NOT IMPLEMENTED BY STATUSNET

    # account/update_location

    # account/update_delivery_device -- NOT IMPLEMENTED BY STATUSNET

    # account/rate_limit_status

    # account/update_profile_background_image

    # account/update_profile_image


######## Favorite resources ########

    # favorites

    # favorites/create

    # favorites/destroy


######## Notification resources ########

    # notifications/follow -- NOT IMPLEMENTED BY STATUSNET

    # notifications/leave -- NOT IMPLEMENTED BY STATUSNET


######## Block resources ########

    # blocks/create

    # blocks/destroy

    # blocks/exists -- NOT YET IMPLEMENTED BY STATUSNET

    # blocks/blocking -- NOT YET IMPLEMENTED BY STATUSNET


######## Help resources ########

    # help/test


######## OAuth resources ########

    # oauth/request_token
    
    # oauth/authorize

    # oauth/access_token


######## Search ########

    # search



##########################
# STATUSNET-ONLY METHODS #
##########################


######## Group resources ########

    # statusnet/groups/timeline

    # statusnet/groups/show

    # statusnet/groups/create

    # statusnet/groups/join

    # statusnet/groups/leave

    # statusnet/groups/list

    # statusnet/groups/list_all

    # statusnet/groups/membership

    # statusnet/groups/is_member


######## Tag resources ########

    # statusnet/groups/timeline


######## Media resources ########

    # statusnet/groups/timeline


######## Miscellanea ########

    # statusnet/config

    # statusnet/version
