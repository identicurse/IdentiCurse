#!/usr/bin/env python
import urllib, urllib2, json

class StatusNet(object):
    def __init__(self, api_path, username, password):
        import base64
        self.api_path = api_path
        self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
        if not self.account_verify_credentials():
            raise Exception("Invalid credentials")
        self.server_config = self.statusnet_config()
        self.length_limit = int(self.server_config["site"]["textlimit"]) # this will be 0 on unlimited instances
        self.tz = self.server_config["site"]["timezone"]
    
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
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("statuses/home_timeline", params)

    def statuses_friends_timeline(self, since_id=0, max_id=0, count=0, page=0, include_rts=False):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
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
            params['count'] = count
        if not (page == 0):
            params['page'] = page
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
            params['count'] = count
        if not (page == 0):
            params['page'] = page
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
            params['count'] = count
        if not (page == 0):
            params['page'] = page
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
#            params['count'] = count
#        if not (page == 0):
#            params['page'] = page
#        return self.__makerequest("statuses/retweeted_by_me", params)

### StatusNet does not implement this method yet
#    def statuses_retweeted_to_me(self, since_id=0, max_id=0, count=0, page=0):
#        params = {}
#        if not (since_id == 0):
#            params['since_id'] = since_id
#        if not (max_id == 0):
#            params['max_id'] = max_id
#        if not (count == 0):
#            params['count'] = count
#        if not (page == 0):
#            params['page'] = page
#        return self.__makerequest("statuses/retweeted_to_me", params)

    def statuses_retweets_of_me(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("statuses/retweets_of_me", params)


######## Status resources ########
    
    def statuses_show(self, id):
        params = {'id':id}
        return self.__makerequest("statuses/show", params)

    def statuses_update(self, status, source="", in_reply_to_status_id=0, latitude=-200, longitude=-200, place_id="", display_coordinates=False, long_dent="split"):
        status = "".join([s.strip(" ") for s in status.split("\n")])  # rejoin split lines back to 1 line
        params = {'status':status}
        if not (source == ""):
            params['source'] = source
        if not (in_reply_to_status_id == 0):
            params['in_reply_to_status_id'] = in_reply_to_status_id
        if not (latitude == -200):
            params['lat'] = latitude
        if not (longitude == -200):
            params['long'] = longitude
        if not (place_id == ""):
            params['place_id'] = place_id
        if display_coordinates:
            params['display_coordinates'] = "true"
        if len(status) > self.length_limit and self.length_limit != 0:
            if long_dent=="truncate":
                params['status'] = status[:self.length_limit]
            elif long_dent=="split":
                status_next = status[self.length_limit - 5:]
                status = status[:self.length_limit-5]
                while True:
                    if len(status) == 0:
                        raise Exception("Maximum status length exceeded by %d characters, and no split point could be found." % (len(status) - self.length_limit))
                    elif status[-1] in [" ", "-"]:
                        status = status + "(...)"
                        break # split point found
                    else:
                        status_next = status[-1] + status_next
                        status = status[:-1]
                if not (in_reply_to_status_id == 0):
                    status_next = status.split(" ")[0] + " (...) " + status_next
                else:
                    status_next = "(...) " + status_next
                params['status'] = status
                first_dent = self.__makerequest("statuses/update", params) # post the first piece as normal
                return self.statuses_update(status_next, source=source, in_reply_to_status_id=in_reply_to_status_id, latitude=latitude, longitude=longitude, place_id=place_id, display_coordinates=display_coordinates, long_dent=long_dent) # then hand the rest off for potential further splitting
            else:
                raise Exception("Maximum status length exceeded by %d characters." % (len(status) - self.length_limit))
        return self.__makerequest("statuses/update", params)
    
    def statuses_destroy(self, id):
        params = {'id':id}
        return self.__makerequest("statuses/destroy", params)

    def statuses_retweet(self, id, source=""):
        params = {'id':id}
        if not (source == ""):
            params['source'] = source
        return self.__makerequest("statuses/retweet", params)


######## User resources ########

    def statuses_friends(self, user_id=0, screen_name="", cursor=0):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        if not (cursor == 0):
            params['cursor'] = cursor
        return self.__makerequest("statuses/friends", params)

    def statuses_followers(self, user_id=0, screen_name="", cursor=0):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        if not (cursor == 0):
            params['cursor'] = cursor
        return self.__makerequest("statuses/followers", params)

    def users_show(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("users/show", params)


######## Direct message resources ########

    def direct_messages(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("direct_messages", params)

    def direct_messages_sent(self, since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("direct_messages/sent", params)

    def direct_messages_new(self, screen_name, user_id, text, source=""):
        params = {'screen_name':screen_name, 'user_id':user_id, 'text':text}
        if not (source == ""):
            params['source'] = source
        return self.__makerequest("direct_messages/new", params)

    # direct_messages/destroy -- NOT IMPLEMENTED BY STATUSNET


######## Friendships resources ########

    def friendships_create(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("friendships/create", params)
    
    def friendships_destroy(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("friendships/destroy", params)
    
    def friendships_exists(self, user_a, user_b):
        params = {'user_a':user_a, 'user_b':user_b}
        return self.__makerequest("friendships/exists", params)

    def friendships_show(self, source_id=0, source_screen_name="", target_id=0, target_screen_name=""):
        params = {}
        if not (source_id == 0):
            params['source_id'] = source_id
        if not (source_screen_name == ""):
            params['source_screen_name'] = source_screen_name
        if not (target_id == 0):
            params['target_id'] = target_id
        if not (target_screen_name == ""):
            params['target_screen_name'] = target_screen_name
        return self.__makerequest("friendships/show", params)


######## Friends and followers resources ########

    def friends_ids(self, user_id, screen_name, cursor=0):
        params = {'user_id':user_id, 'screen_name':screen_name}
        if not (cursor == 0):
            params['cursor'] = cursor
        return self.__makerequest("friends/ids", params)

    def followers_ids(self, user_id, screen_name, cursor=0):
        params = {'user_id':user_id, 'screen_name':screen_name}
        if not (cursor == 0):
            params['cursor'] = cursor
        return self.__makerequest("followers/ids", params)


######## Account resources ########

    def account_verify_credentials(self):
        try:
            result = self.__makerequest("account/verify_credentials")
            return True
        except:
            return False

    # account/end_session -- NOT IMPLEMENTED BY STATUSNET

    # account/update_location -- IMPLEMENTED, BUT NO DOCUMENTATION

    # account/update_delivery_device -- NOT IMPLEMENTED BY STATUSNET

    def account_rate_limit_status(self):
        return self.__makerequest("account/rate_limit_status")

    # account/update_profile_background_image - to be implemented if/when we have a helper function for multipart/form-data encoding

    # account/update_profile_imagee - to be implemented if/when we have a helper function for multipart/form-data encoding


######## Favorite resources ########

    def favorites(self, id=0, page=0):
        params = {}
        if not (id == 0):
            params['id'] = id
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("favorites", params)

    def favorites_create(self, id):
        params = {'id':id}
        return self.__makerequest("favorites/create/%d" % (id), params)

    def favorites_destroy(self, id):
        params = {'id':id}
        return self.__makerequest("favorites/destroy/%d" % (id), params)


######## Notification resources ########

    # notifications/follow -- NOT IMPLEMENTED BY STATUSNET

    # notifications/leave -- NOT IMPLEMENTED BY STATUSNET


######## Block resources ########

    def blocks_create(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("blocks/create", params)

    def blocks_destroy(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("blocks/destroy", params)

    # blocks/exists -- NOT YET IMPLEMENTED BY STATUSNET

    # blocks/blocking -- NOT YET IMPLEMENTED BY STATUSNET


######## Help resources ########

    def help_test(self):
        return self.__makerequest("help/test")


######## OAuth resources ########
# will not be implemented unless this module moves to using OAuth instead of basic

    # oauth/request_token
    
    # oauth/authorize

    # oauth/access_token


######## Search ########

    def search(self, query, since_id=0, max_id=0, count=0, page=0, standardise=False):
        params = {'q':query}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['results_per_page'] = count
        if not (page == 0):
            params['page'] = page
        if standardise:   # standardise is not part of the API, it is intended to make search results able to be handled as a standard timeline by replacing results with the actual notices as returned by statuses/show
            results = [self.statuses_show(result['id']) for result in self.__makerequest("search", params)['results']]
            return results
        else:
            return self.__makerequest("search", params)


##########################
# STATUSNET-ONLY METHODS #
##########################


######## Group resources ########

    def statusnet_groups_timeline(self, group_id=0, nickname="", since_id=0, max_id=0, count=0, page=0):
        params = {}
        if not (group_id == 0):
            params['id'] = group_id
        if not (nickname == ""):
            params['nickname'] = nickname
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        if 'id' in params:
            return self.__makerequest("statusnet/groups/timeline/%d" % (group_id), params)
        elif 'nickname' in params:
            return self.__makerequest("statusnet/groups/timeline/%s" % (nickname), params)
        else:
            raise Exception("At least one of group_id or nickname must be supplied")

    def statusnet_groups_show(self, group_id=0, nickname=""):
        params = {}
        if not (group_id == 0):
            params['id'] = group_id
        if not (nickname == ""):
            params['nickname'] = nickname
        if 'id' in params:
            return self.__makerequest("statusnet/groups/show/%d" % (group_id), params)
        elif 'nickname' in params:
            return self.__makerequest("statusnet/groups/show/%s" % (nickname), params)
        else:
            raise Exception("At least one of group_id or nickname must be supplied")

    # statusnet/groups/create -- does not seem to match the proposed API, will leave unimplemented for now

    def statusnet_groups_join(self, group_id=0, nickname=""):
        params = {}
        if not (group_id == 0):
            params['id'] = group_id
        if not (nickname == ""):
            params['nickname'] = nickname
        if 'id' in params:
            return self.__makerequest("statusnet/groups/join/%d" % (group_id), params)
        elif 'nickname' in params:
            return self.__makerequest("statusnet/groups/join/%s" % (nickname), params)
        else:
            raise Exception("At least one of group_id or nickname must be supplied")

    def statusnet_groups_leave(self, group_id=0, nickname=""):
        params = {}
        if not (group_id == 0):
            params['id'] = group_id
        if not (nickname == ""):
            params['nickname'] = nickname
        if 'id' in params:
            return self.__makerequest("statusnet/groups/leave/%d" % (group_id), params)
        elif 'nickname' in params:
            return self.__makerequest("statusnet/groups/leave/%s" % (nickname), params)
        else:
            raise Exception("At least one of group_id or nickname must be supplied")

    def statusnet_groups_list(self, user_id=0, screen_name=""):
        params = {}
        if not (user_id == 0):
            params['user_id'] = user_id
        if not (screen_name == ""):
            params['screen_name'] = screen_name
        return self.__makerequest("statusnet/groups/list", params)

    def statusnet_groups_list_all(self, count=0, page=0):
        params = {}
        if not (count == 0):
            params['count'] = count
        if not (count == 0):
            params['count'] = count
        return self.__makerequest("statusnet/groups/list_all", params)

    def statusnet_groups_membership(self, group_id=0, nickname=""):
        params = {}
        if not (group_id == 0):
            params['id'] = group_id
        if not (nickname == ""):
            params['nickname'] = nickname
        if 'id' in params:
            return self.__makerequest("statusnet/groups/membership/%d" % (group_id), params)
        elif 'nickname' in params:
            return self.__makerequest("statusnet/groups/membership/%s" % (nickname), params)
        else:
            raise Exception("At least one of group_id or nickname must be supplied")

    def statusnet_groups_is_member(self, user_id, group_id):
        params = {'user_id':user_id, 'group_id':group_id}
        return self.__makerequest("statusnet/groups/is_member", params)['is_member']

######## Tag resources ########

    def statusnet_tags_timeline(self, tag, since_id=0, max_id=0, count=0, page=0):
        params = {'tag':tag}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("statusnet/tags/timeline/%s" % (tag), params)


######## Media resources ########

    # statusnet/media/upload - to be implemented if/when we have a helper function for multipart/form-data encoding


######## Miscellanea ########

    def statusnet_config(self):
        return self.__makerequest("statusnet/config")

    def statusnet_version(self):
        return self.__makerequest("statusnet/version")
