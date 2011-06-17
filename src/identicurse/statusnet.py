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

import urllib, urllib2, httplib, helpers, config, time
try:
    import json
except ImportError:
    import simplejson as json

class StatusNetError(Exception):
    def __init__(self, errcode, details):
        self.errcode = errcode
        self.details = details
        if errcode == -1:
            Exception.__init__(self, "Error: %s" % (self.details))
        else:
            Exception.__init__(self, "Error %d: %s" % (self.errcode, self.details))

class StatusNet(object):
    def __init__(self, api_path, username="", password="", use_auth=True, auth_type="basic", consumer_key=None, consumer_secret=None, validate_ssl=True):
        import base64
        self.api_path = api_path
        if self.api_path[-1] == "/":  # We don't want a surplus / when creating request URLs. Sure, most servers will handle it well, but why take the chance?
            self.api_path == self.api_path[:-1]
        if validate_ssl:
            #TODO: Implement SSL-validating handler and add it to opener here
            self.opener = urllib2.build_opener()
        else:
            self.opener = urllib2.build_opener()
        self.use_auth = use_auth
        self.auth_type = auth_type
        self.auth_string = None
        if not self.__checkconn():
            raise Exception("Couldn't access %s, it may well be down." % (api_path))
        if self.use_auth:
            if auth_type == "basic":
                self.auth_string = base64.encodestring('%s:%s' % (username, password))[:-1]
                if not self.account_verify_credentials():
                    raise Exception("Invalid credentials")
            elif auth_type == "oauth":
                self.consumer_key = consumer_key
                self.consumer_secret = consumer_secret
                self.oauth_initialize()
                if not self.account_verify_credentials():
                    raise Exception("OAuth authentication failed")
        self.server_config = self.statusnet_config()
        self.length_limit = int(self.server_config["site"]["textlimit"]) # this will be 0 on unlimited instances
        self.tz = self.server_config["site"]["timezone"]

    def oauth_initialize(self):
        if not ("oauth_token" in config.config and "oauth_token_secret" in config.config):  # we've never run with oauth before, or we failed, so we'll need to authenticate
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

            config.config['oauth_token'] = access_tokens['oauth_token']
            config.config['oauth_token_secret'] = access_tokens['oauth_token_secret']
            config.config.save()

        self.oauth_token = config.config['oauth_token']
        self.oauth_token_secret = config.config['oauth_token_secret']

    def oauth_nonce(self, length=16):
        import random
        if not hasattr(config.session_store, "nonces"):
            config.session_store.nonces = []
        valid_chars = [chr(c) for c in range(ord("A"), ord("Z")+1)] + [chr(c) for c in range(ord("a"), ord("z")+1)] + [chr(c) for c in range(ord("0"), ord("9")+1)]
        valid_nonce = False
        while not valid_nonce:
            nonce = ""
            for n in xrange(length):
                nonce += random.choice(valid_chars)
            if not nonce in config.session_store.nonces:
                config.session_store.nonces.append(nonce)
                valid_nonce = True
        return nonce

    def oauth_sign_request(self, request, oauth_tokens, raw_params):
        oauth_params = {
                "oauth_consumer_key": oauth_tokens['consumer'],
                "oauth_nonce": self.oauth_nonce(),
                "oauth_timestamp": str(int(time.time())),
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_version": "1.0",
                "oauth_callback": "oob",
                }
        if "token" in oauth_tokens:
            oauth_params["oauth_token"] = oauth_tokens["token"]
        if "verifier" in oauth_tokens:
            oauth_params["oauth_verifier"] = oauth_tokens["verifier"]

        raw_signature_data = [
                urllib.quote(request.get_method(), safe='~'),
                urllib.quote(request.get_full_url().split("?")[0], safe='~'),
                ]

        # make a local copy, otherwise it pollutes future GET requests
        local_raw_params = dict(raw_params)
        
        for key, value in oauth_params.iteritems():
            local_raw_params[key] = value

        params = ""
        for key in sorted(local_raw_params.keys()):
            params += "&%s=%s" % (urllib.quote(key, safe='~'), urllib.quote(str(local_raw_params[key]), safe='~'))
        raw_signature_data.append(urllib.quote(params[1:], safe='~'))

        signature_key = "%s&" % urllib.quote(oauth_tokens["consumer_secret"], safe='~')
        if "token_secret" in oauth_tokens:
                signature_key = "%s%s" % (signature_key, urllib.quote(oauth_tokens["token_secret"], safe='~'))
        signature_data = "&".join(raw_signature_data)

        import hmac, binascii
        try:
            import hashlib.sha1 as sha
        except ImportError:
            import sha  # 2.4 and earlier
        signature_raw = hmac.new(signature_key, signature_data, sha)
        signature = binascii.b2a_base64(signature_raw.digest())[:-1]

        oauth_params["oauth_signature"] = signature
        
        request.add_header("Authorization", "OAuth %s" % (", ".join(["%s=%s" % (urllib.quote(key, safe='~'), urllib.quote(value, safe='~')) for key, value in oauth_params.iteritems()])))
        
    def __makerequest(self, resource_path, raw_params={}, force_get=False):
        params = urllib.urlencode(raw_params)
        
        if not resource_path in ["oauth/request_token", "oauth/access_token"]:
            resource_path = "%s.json" % (resource_path)

        if len(raw_params) > 0:
            if force_get:
                request = urllib2.Request("%s/%s?%s" % (self.api_path, resource_path, params))
            else:
                request = urllib2.Request("%s/%s" % (self.api_path, resource_path), params)
        else:
            request = urllib2.Request("%s/%s" % (self.api_path, resource_path))
        if self.auth_type == "basic":
            if self.auth_string is not None:
                request.add_header("Authorization", "Basic %s" % (self.auth_string))
        elif self.auth_type == "oauth":
            tokens = {
                    "consumer": self.consumer_key,
                    "consumer_secret": self.consumer_secret,
                    }
            if resource_path == "oauth/request_token":
                pass  # no other tokens to add
            elif resource_path == "oauth/access_token":
                tokens["token"] = self.request_token
                tokens["token_secret"] = self.request_token_secret
                tokens["verifier"] = self.verifier
            else:
                tokens["token"] = self.oauth_token
                tokens["token_secret"] = self.oauth_token_secret
            self.oauth_sign_request(request, tokens, raw_params)

        success = False
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
                raise StatusNetError(e.code, err_details)
            except urllib2.URLError, e:
                raise StatusNetError(-1, e.reason)
            except httplib.BadStatusLine, e:
                success = False
            attempt_count += 1

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
                status_next = status[helpers.find_split_point(status, self.length_limit - 3):]
                status = status.encode('utf-8')[:helpers.find_split_point(status, self.length_limit - 3)] + u".."
                if dup_first_word or (not (in_reply_to_status_id == 0)):
                    status_next = status.split(" ")[0].encode('utf-8') + " .. " + status_next
                else:
                    status_next = ".. " + status_next
                params['status'] = status
                dents = [self.__makerequest("statuses/update", params)] # post the first piece as normal
                next_dent = self.statuses_update(status_next, source=source, in_reply_to_status_id=dents[-1]["id"], latitude=latitude, longitude=longitude, place_id=place_id, display_coordinates=display_coordinates, long_dent=long_dent) # then hand the rest off for potential further splitting
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
        return self.__makerequest("oauth/request_token")
    
    def oauth_authorize(self, request_token):
        return raw_input("To authorize IdentiCurse to access your account, you must go to %s/oauth/authorize?oauth_token=%s in your web browser.\nPlease enter the verification code you receive there: " % (self.api_path, request_token))

    def oauth_access_token(self, request_token, request_token_secret, verifier):
        self.request_token = request_token
        self.request_token_secret = request_token_secret
        self.verifier = verifier
        return self.__makerequest("oauth/access_token")

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
