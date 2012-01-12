# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
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

import urllib, urllib2, httplib, time, re
try:
    from oauth import oauth
    has_oauth = True
except ImportError:
    has_oauth = False
try:
    import json
except ImportError:
    import simplejson as json


domain_regex = re.compile("http(s|)://(www\.|)(.+?)(/.*|)$")


def find_split_point(text, width):
    split_point = width - 1
    while True:
        if split_point == 0:  # no smart split point was found, split unsmartly
            split_point = width - 1
            break
        elif split_point < 0:
            split_point = 0
            break
        if text[split_point-1] == " ":
            break
        else:
            split_point -= 1
    return split_point


class StatusNetError(Exception):
    def __init__(self, errcode, details):
        self.errcode = errcode
        self.details = details
        if errcode == -1:
            Exception.__init__(self, "Error: %s" % (self.details))
        else:
            Exception.__init__(self, "Error %d: %s" % (self.errcode, self.details))

class StatusNet(object):
    def __init__(self, api_path, username="", password="", use_auth=True, auth_type="basic", consumer_key=None, consumer_secret=None, oauth_token=None, oauth_token_secret=None, validate_ssl=True, save_oauth_credentials=None):
        import base64
        self.api_path = api_path
        if self.api_path[-1] == "/":  # We don't want a surplus / when creating request URLs. Sure, most servers will handle it well, but why take the chance?
            self.api_path == self.api_path[:-1]
        if domain_regex.findall(self.api_path)[0][2] == "api.twitter.com":
            self.is_twitter = True
        else:
            self.is_twitter = False
        if validate_ssl:
            #TODO: Implement SSL-validating handler and add it to opener here
            self.opener = urllib2.build_opener()
        else:
            self.opener = urllib2.build_opener()
        self.use_auth = use_auth
        self.auth_type = auth_type
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.save_oauth_credentials = save_oauth_credentials
        self.auth_string = None
        if not self.__checkconn():
            raise Exception("Couldn't access %s, it may well be down." % (api_path))
        if self.use_auth:
            if auth_type == "basic":
                self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
                if self.is_twitter:
                    raise Exception("Twitter does not support basic auth; bailing out.")
                if not self.account_verify_credentials():
                    raise Exception("Invalid credentials")
            elif auth_type == "oauth":
                if has_oauth:
                    self.consumer = oauth.OAuthConsumer(str(consumer_key), str(consumer_secret))
                    self.oauth_initialize()
                    if self.is_twitter:
                        self.api_path += "/1"
                    if not self.account_verify_credentials():
                        raise Exception("OAuth authentication failed")
                else:
                    raise Exception("OAuth could not be initialised.")
        self.server_config = self.statusnet_config()
        try:
            self.length_limit = int(self.server_config["site"]["textlimit"]) # this will be 0 on unlimited instances
        except:
            self.length_limit = 0  # assume unlimited on failure to get a defined limit
        self.tz = self.server_config["site"]["timezone"]

    def oauth_initialize(self):
        if (self.oauth_token is None) or (self.oauth_token_secret is None):  # we've never run with oauth before, or we failed, so we'll need to authenticate
            request_tokens_raw = self.oauth_request_token()
            request_tokens = {}
            for item in request_tokens_raw.split("&"):
                key, value = item.split("=")
                request_tokens[key] = value

            verifier = self.oauth_authorize(request_tokens["oauth_token"])

            access_tokens_raw = self.oauth_access_token(request_tokens["oauth_token"], request_tokens["oauth_token_secret"], verifier)
            access_tokens = {}
            for item in access_tokens_raw.split("&"):
                key, value = item.split("=")
                access_tokens[key] = value

            self.oauth_token = access_tokens['oauth_token']
            self.oauth_token_secret = access_tokens['oauth_token_secret']
            if self.save_oauth_credentials is not None:
                self.save_oauth_credentials(self.oauth_token, self.oauth_token_secret)

        self.token = oauth.OAuthToken(str(self.oauth_token), str(self.oauth_token_secret))

    def __makerequest(self, resource_path, raw_params={}, force_get=False):
        params = urllib.urlencode(raw_params)
        
        if not resource_path in ["oauth/request_token", "oauth/access_token"]:
            resource_path = "%s.json" % (resource_path)

        if self.auth_type == "basic":
            if len(raw_params) > 0:
                if force_get:
                    request = urllib2.Request("%s/%s?%s" % (self.api_path, resource_path, params))
                else:
                    request = urllib2.Request("%s/%s" % (self.api_path, resource_path), params)
            else:
                request = urllib2.Request("%s/%s" % (self.api_path, resource_path))

            if self.auth_string is not None:
                request.add_header("Authorization", "Basic %s" % (self.auth_string))

        elif self.auth_type == "oauth":
            resource_url = "%s/%s" % (self.api_path, resource_path)

            if len(raw_params) > 0 and not force_get:
                oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, http_method="POST", http_url=resource_url, parameters=raw_params)
            else:
                oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, self.token, http_method="GET", http_url=resource_url, parameters=raw_params)
            oauth_request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, self.token)

            if len(raw_params) > 0 and not force_get:
                request = urllib2.Request(resource_url, data=oauth_request.to_postdata(), headers=oauth_request.to_header())
            else:
                request = urllib2.Request(oauth_request.to_url(), headers=oauth_request.to_header())

        success = False
        response = None
        attempt_count = 0
        while not success:
            success = True  # succeed unless we hit BadStatusLine
            if attempt_count >= 10:  # after 10 failed attempts
                raise Exception("Could not successfully read any response. Please check that your connection is working.")
            try:
                response = self.opener.open(request)
            except urllib2.HTTPError, e:
                raw_details = e.read()
                try:
                    err_details = json.loads(raw_details)['error']
                except ValueError:  # not JSON, use raw
                    err_details = raw_details
                if (e.code % 400) < 100:  # only throw the error further up if it's not a server error
                    raise StatusNetError(e.code, err_details)
            except urllib2.URLError, e:
                raise StatusNetError(-1, e.reason)
            except httplib.BadStatusLine, e:
                success = False
            attempt_count += 1

        if response is None:
            raise StatusNetError(-1, "Could not successfully read any response. Please check that your connection is working.")

        content = response.read()
    
        try:
            return json.loads(content)
        except ValueError:  # it wasn't JSON data, return it raw
            return content

    def __checkconn(self):
        try:
            self.opener.open(self.api_path+"/help/test.json")
            return True
        except:
            return False


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
        return self.__makerequest("statuses/user_timeline", params, force_get=True)

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
        return self.__makerequest("statuses/show/%s" % str(id))

    def statuses_update(self, status, source="", in_reply_to_status_id=0, latitude=-200, longitude=-200, place_id="", display_coordinates=False, long_dent="split", dup_first_word=False):
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
                status_next = status[find_split_point(status, self.length_limit - 3):]
                status = status.encode('utf-8')[:find_split_point(status, self.length_limit - 3)] + u".."
                if dup_first_word:
                    status_next = status.split(" ")[0].encode('utf-8') + " .. " + status_next
                else:
                    status_next = ".. " + status_next
                params['status'] = status
                dents = [self.__makerequest("statuses/update", params)] # post the first piece as normal
                if in_reply_to_status_id == 0:
                    in_reply_to_status_id = dents[-1]["id"]  # if this is not a reply, string everything onto the first dent
                next_dent = self.statuses_update(status_next, source=source, in_reply_to_status_id=in_reply_to_status_id, latitude=latitude, longitude=longitude, place_id=place_id, display_coordinates=display_coordinates, long_dent=long_dent) # then hand the rest off for potential further splitting
                if isinstance(next_dent, list):
                    for dent in next_dent:
                        dents.append(dent)
                else:
                    dents.append(next_dent)
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
        return self.__makerequest("statuses/retweet/%s" % str(id), params)


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

    def favorites(self, id=0, page=0, since_id=0):
        params = {}
        if not (id == 0):
            params['id'] = id
        if not (page == 0):
            params['page'] = page
        if not (since_id == 0):
            params['since_id'] = since_id
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
        try:
            return self.__makerequest("help/test")
        except:
            return None


######## OAuth resources ########
# will not be implemented unless this module moves to using OAuth instead of basic

    def oauth_request_token(self):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, callback="oob", http_method="POST", http_url="%s/%s" % (self.api_path, "oauth/request_token"))
        oauth_request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, None)
        request = urllib2.Request("%s/%s" % (self.api_path, "oauth/request_token"), data=oauth_request.to_postdata(), headers=oauth_request.to_header())
        return self.opener.open(request).read()
    
    def oauth_authorize(self, request_token):
        return raw_input("To authorize IdentiCurse to access your account, you must go to %s/oauth/authorize?oauth_token=%s in your web browser.\nPlease enter the verification code you receive there: " % (self.api_path, request_token))

    def oauth_access_token(self, request_token, request_token_secret, verifier):
        req_token = oauth.OAuthToken(str(request_token), str(request_token_secret))
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=req_token, verifier=verifier, callback="oob", http_method="POST", http_url="%s/%s" % (self.api_path, "oauth/access_token"))
        oauth_request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, req_token)
        request = urllib2.Request("%s/%s" % (self.api_path, "oauth/access_token"), data=oauth_request.to_postdata(), headers=oauth_request.to_header())
        return self.opener.open(request).read()

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

######## Conversations ########

    def statusnet_conversation(self, id, since_id=0, max_id=0, count=0, page=0):
        params = {'id': id}
        if not (since_id == 0):
            params['since_id'] = since_id
        if not (max_id == 0):
            params['max_id'] = max_id
        if not (count == 0):
            params['count'] = count
        if not (page == 0):
            params['page'] = page
        return self.__makerequest("statusnet/conversation/%s" % str(id), params, force_get=True)


######## Miscellanea ########

    def statusnet_config(self):
        return self.__makerequest("statusnet/config")

    def statusnet_version(self):
        return self.__makerequest("statusnet/version")
