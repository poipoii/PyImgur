# This file is part of PyImgur.
#
# PyImgur is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyImgur is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyImgur.  If not, see <http://www.gnu.org/licenses/>.

from base64 import b64encode
from decorator import decorator
import re

import request

from authentication import headers


def get_album_or_image(json, imgur):
    """Return a gallery image/album depending on what the json represent."""
    if json['is_album']:
        return Gallery_album(json, imgur)
    return Gallery_image(json, imgur)


@decorator
def require_auth(func, obj, *args, **kwargs):
    """This method requires that we've successfully authenticated as a user."""
    imgur = obj if isinstance(obj, Imgur) else obj.imgur
    if not imgur.is_authenticated:
        raise Exception("Login required to use this method.")


class Basic_object(object):
    """Contains the basic functionality shared by a lot of PyImgurs classes."""
    def __init__(self, json_dict, imgur, has_fetched=True):
        self._has_fetched = has_fetched
        self.imgur = imgur
        self._populate(json_dict)

    def __getattr__(self, attribute):
        if not self._has_fetched:
            self.refresh()
            self._has_fetched = True
            return getattr(self, attribute)
        raise AttributeError("%s instance has no attribute '%s'" %
                             (type(self).__name__, attribute))

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.id)

    def _populate(self, json_dict):
        for key, value in json_dict.iteritems():
            setattr(self, key, value)
        # Update certain attributes for certain objects, to be link to lazily
        # created objects rather than a string of ID or similar.
        if isinstance(self, Album) and hasattr(self, "account_url"):
            self.account_url = User({'url': self.account_url}, self.imgur,
                                    has_fetched=False)
        elif isinstance(self, Comment) and hasattr(self, "author"):
            self.author = User({'url': self.author}, self.imgur,
                               has_fetched=False)
            # TODO: consider changing image_id to be a lazy Image object
            # instead.  The reason to consider is that this would mean renaming
            # image_id to image.

    def refresh(self):
        resp = self.imgur._send_request(self._INFO_URL)
        self._populate(resp)


class Album(Basic_object):
    def __init__(self, json_dict, imgur, has_fetched=True):
        self._INFO_URL = ("https://api.imgur.com/3/album/%s" % json_dict['id'])
        self.deletehash = None
        self.images = []
        super(Album, self).__init__(json_dict, imgur, has_fetched)

    @require_auth
    def add_images(self, ids):
        """Add images to the album."""
        pass

    def delete(self):
        url = "https://api.imgur.com/3/album/%s" % self.deletehash
        return self.imgur._send_request(url, method="DELETE")

    @require_auth
    def favorite(self):
        """Favorite the album."""
        pass

    # TODO: Doing it like this seem to obfuscate the API. Since we change
    # the state of the album without the user taking a direct action.
    def get_images(self):
        url = "https://api.imgur.com/3/album/%s/images" % self.id
        images = self.imgur._send_request(url)
        self.images = [Image(img, self.imgur) for img in images]
        return self.images

    @require_auth
    def remove_images(self, ids):
        """Remove images from the album."""
        pass

    @require_auth
    def set_images(self, ids):
        """Set the images in this album."""
        pass

    @require_auth
    def submit_to_gallery():
        """Add this to the gallery."""
        pass

    def update(self, title=None, description=None, ids=None, cover=None,
               layout=None, privacy=None):
        """Update the albums information."""
        url = "https://api.imgur.com/3/album/%s" % self.deletehash
        payload = {'title': title, 'description': description,
                   'ids': ids, 'cover': cover,
                   'layout': layout, 'privacy': privacy}
        is_updated = self.imgur._send_request(url, params=payload, method='POST')
        if is_updated:
            self.title = title or self.title
            self.description = description or self.description
            self.layout = layout or self.layout
            self.privacy = privacy or self.privacy
            if cover is not None:
                self.cover = Image(cover)
            if ids:
                self.images = [Image(img, self.imgur) for img in ids]
        return is_updated


class Comment(Basic_object):
    def __init__(self, json_dict, imgur):
        self.deletehash = None
        self._INFO_URL = ("https://api.imgur.com/3/comment/%s" %
                          json_dict['id'])
        super(Comment, self).__init__(json_dict, imgur)
        # Possible via webend, not exposed via json
        # self.permalink == ?!??!

    @require_auth
    def delete(self):
        """Delete the comment."""
        pass

    @require_auth
    def downvote(self):
        """Downvote this comment."""
        pass

    def get_replies(self):
        """Create a reply for the given comment."""
        url = "https://api.imgur.com/3/comment/%s/replies" % self.id
        json = self.imgur._send_request(url)
        child_comments = json['children']
        return [Comment(com, self.imgur) for com in child_comments]

    # Question. Can you only reply to images? If you can comment on other
    # comments, then how do you do that? Use comment_id instead of image_id?
    # It's clearly possible to reply to a comment.
    # http://imgur.com/gallery/LA2RQqp/comment/49538390
    # If it is image_only, then this should probably be moved to Image
    def reply(self, image_id, text):
        """Create a reply for the given comment."""
        pass

    @require_auth
    def report(self):
        """Reply comment for being inappropriate."""

    @require_auth
    def upvote(self):
        """Upvote this comment."""
        pass


class Gallery_item(object):
    """Functionality shared by Gallery_image and Gallery_album."""
    @require_auth
    def comment(self, comment):
        pass

    @require_auth
    def downvote(self):
        pass

    def get_comment_count(self):
        # So far I've decided not to implement this and get_comment_ids. Their
        # functionality seems covered by get_comments on the assumption that
        # there is no limit to the number of comments returned.
        raise NotImplementedError("Use len(get_comments) instead")

    def get_comment_ids(self):
        raise NotImplementedError("Use get_comments instead to return the "
                                  "Comment objects and retrieve the ids from "
                                  "that call")

    def get_comments(self):
        url = "https://api.imgur.com/3/gallery/%s/comments" % self.id
        resp = self.imgur._send_request(url)
        return [Comment(com, self.imgur) for com in resp]

    def get_votes(self):
        pass

    @require_auth
    def upvote(self):
        pass


class Image(Basic_object):
    def __init__(self, json_dict, imgur, has_fetched=True):
        self._INFO_URL = ("https://api.imgur.com/3/image/%s" % json_dict['id'])
        self.deletehash = None
        super(Image, self).__init__(json_dict, imgur, has_fetched)

    def delete(self):
        """Delete the image."""
        return self.imgur._send_request("https://api.imgur.com/3/image/%s" %
                                        self.deletehash, method='DELETE')

    @require_auth
    def favorite(self):
        """Favorite the image."""
        pass

    @require_auth
    def remove_from_gallery():
        """Remove this image from the gallery."""
        # TODO. Text implies this is image only and won't work with albums.
        # Confirm
        pass

    @require_auth
    def submit_to_gallery():
        """Add this to the gallery."""
        pass

    def update(self, title=None, description=None):
        """Update the image with a new title and/or description."""
        payload = {'title': title, 'description': description}
        url = "https://api.imgur.com/3/image/%s" % self.deletehash
        is_updated = self.imgur._send_request(url, params=payload,
                                              method='POST')
        if is_updated:
            self.title = title or self.title
            self.description = description or self.description
        return is_updated


class Imgur:
    def __init__(self):
        self.is_authenticated = False
        self.ratelimit_clientlimit = None
        self.ratelimit_clientremaining = None
        self.ratelimit_userlimit = None
        self.ratelimit_userremaining = None
        self.ratelimit_userreset = None

    def _send_request(self, *args, **kwargs):
        """Handles sending requests to Imgur and updates ratelimit info."""
        result = request.send_request(*args, authentication=headers, **kwargs)
        content, ratelimit_info = result
        # Disable ratelimit info as it seems it stopped being included in the
        # returned information from 9-05-2013
        # self.ratelimit_clientlimit = ratelimit_info['x-ratelimit-clientlimit']
        # self.ratelimit_clientremaining = ratelimit_info['x-ratelimit-'
        #                                                 'clientremaining']
        # self.ratelimit_userlimit = ratelimit_info['x-ratelimit-userlimit']
        # self.ratelimit_userremaining = ratelimit_info['x-ratelimit-'
        #                                               'userremaining']
        # self.ratelimit_userreset = ratelimit_info['x-ratelimit-userreset']
        # Note: When the cache is implemented, it's important that the
        # ratelimit info doesn't get updated with the ratelimit info in the
        # cache since that's likely incorrect.
        return content

    def is_imgur_url(self, url):
        """Is the given url a valid imgur url?"""
        return re.match("(http://)?(www\.)?imgur\.com", url, re.I) is not None

    @require_auth
    def create_account(self, username):
        """Create this user on Imgur."""
        pass

    def create_album(self, title=None, description=None, ids=None, cover=None):
        url = "https://api.imgur.com/3/album/"
        payload = {'ids': ids, 'title': title,
                   'description': description, 'cover': cover}
        resp = self._send_request(url, params=payload, method='POST')
        return Album(resp, self, has_fetched=False)

    def get_at_url(self, url):
        """Return whatever is at the imgur url as an object."""
        pass

    def get_album(self, id):
        """Return information about this album."""
        json = self._send_request("https://api.imgur.com/3/album/%s" % id)
        return Album(json, self)

    def get_comment(self, id):
        """Return information about this comment."""
        json = self._send_request("https://api.imgur.com/3/comment/%s" % id)
        return Comment(json, self)

    def get_gallery(self, section='hot', sort='viral', page=0, window='day',
                    showViral=True):
        """Return the albums and and images in the gallery."""
        # TODO: Add pagination
        url = ("https://api.imgur.com/3/gallery/%s/%s/%s/%d?showViral=%s" %
               (section, sort, window, page, showViral))
        resp = self._send_request(url)
        return [get_album_or_image(thing, self) for thing in resp]

    def get_image(self, id):
        """Return a Image object representing the image with id."""
        resp = self._send_request("https://api.imgur.com/3/image/%s" % id)
        return Image(resp, self)

    def get_subreddit_gallery(self, subreddit, sort='time', page=0,
                              window='top'):
        """View gallery images for a subreddit."""
        url = ("https://api.imgur.com/3/gallery/r/%s/%s}/%s/%d" %
               (subreddit, sort, window, page))
        resp = self._send_request(url)
        return [get_album_or_image(thing, self) for thing in resp]

    def get_subreddit_image(self):
        """View a single image in the subreddit."""
        # I think this duplicates get_gallery_image. So there should be no
        # reason to implement it.
        pass

    def get_user(self, username):
        """Return information about this user."""
        url = "https://api.imgur.com/3/account/%s" % username
        json = self._send_request(url)
        return User(json, self)

    def search_gallery(self, q):
        """Search the gallery with a given query string."""
        url = "https://api.imgur.com/3/gallery/search?q=%s" % q
        resp = self._send_request(url)
        return [get_album_or_image(thing, self) for thing in resp]

    def upload_image(self, path, title=None, description=None, album_id=None):
        """Upload the image at path and return it."""
        with open(path, 'rb') as image_file:
            binary_data = image_file.read()
            image = b64encode(binary_data)

        payload = {'album_id': album_id, 'image': image,
                   'title': title, 'description': description}

        resp = self._send_request("https://api.imgur.com/3/image",
                                  params=payload, method='POST')
        return Image(resp, self, False)


class Message(object):
    # Requires login to test
    def __init__(self, json_dict, imgur):
        # Is never gotten lazily, so _has_fetched is always True
        super(Message, self).__init__(json_dict, imgur, True)


class Notification(object):
    # Requires login to test
    def __init__(self, json_dict, imgur):
        # Is never gotten lazily, so _has_fetched is always True
        super(Notification, self).__init__(json_dict, imgur, True)


class User(Basic_object):
    def __init__(self, json_dict, imgur, has_fetched=True):
        self._INFO_URL = ("https://api.imgur.com/3/account/%s" %
                          json_dict['url'])
        super(User, self).__init__(json_dict, imgur, has_fetched)

    # Overrides __repr__ method in Basic_object
    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.url)

    @require_auth
    def change_settings(self, bio=None, public_images=None,
                        messaging_enabled=None, album_privacy=None,
                        accepted_gallery_terms=None):
        pass

    @require_auth
    def delete(self):
        """Delete this user."""
        pass

    def get_album_count(self):
        # See get_comment_count for comment on non-implementation
        raise NotImplementedError("Use len(get_albums) instead.")

    def get_album_ids(self):
        # See get_comment_ids for comment on non-implementation
        raise NotImplementedError("Use get_albums instead to return the "
                                  "Album objects and retrieve the ids from "
                                  "that call")

    def get_albums(self, page=0):
        """
        Return the users albums.

        Secret and hidden albums are only returned if this is the logged-in
        user.
        """
        url = "https://api.imgur.com/3/account/%s/albums/%d" % (self.url, page)
        resp = self.imgur._send_request(url)
        return [Album(alb, self.imgur) for alb in resp]

    def get_comments(self):
        """Return the comments made by the user."""
        url = "https://api.imgur.com/3/account/%s/comments" % self.url
        resp = self.imgur._send_request(url)
        return [Comment(com, self.imgur) for com in resp]

    def get_comment_count(self):
        # See the other get_comment_count for non-implementing reasoning
        raise NotImplementedError("Use len(get_comments) instead")

    def get_comment_ids(self):
        # See the other get_comment_ids for non-implementing reasoning
        raise NotImplementedError("Use get_comments instead to return the "
                                  "Comment objects and retrieve the ids from "
                                  "that call")

    @require_auth
    def get_favorites(self):
        """Return the users favorited images."""
        pass

    def get_gallery_favorites(self):
        url = "https://api.imgur.com/3/account/%s/gallery_favorites" % self.url
        resp = self.imgur._send_request(url)
        return [Image(img, self.imgur) for img in resp]

    def get_gallery_profile(self):
        url = "https://api.imgur.com/3/account/%s/gallery_profile" % self.url
        return self.imgur._send_request(url)

    @require_auth
    def has_verified_email(self):
        pass

    def get_images(self, page=0):
        """Return all of the images associated with the user."""
        url = "https://api.imgur.com/3/account/%s/images/%d" % (self.url, page)
        resp = self.imgur._send_request(url)
        return [Image(img, self.imgur) for img in resp]

    def get_image_count(self):
        # See the other get_comment_count for non-implementing reasoning
        raise NotImplementedError("Use len(get_images) instead")

    def get_images_ids(self):
        # See the other get_comment_ids for non-implementing reasoning
        raise NotImplementedError("Use get_images instead to return the "
                                  "Image objects and retrieve the ids from "
                                  "that call")

    @require_auth
    def get_messages(new=True):
        """Return all messages sent to this user."""
        pass

    @require_auth
    def get_notifications(new=True):
        """Return all the notifications for this user."""
        pass

    @require_auth
    def get_replies():
        """Return all reply notifications for the user. Login required."""
        pass

    def get_submissions(self):
        # TODO: Add pagination
        url = "https://api.imgur.com/3/account/%s/submissions/%d" % (self.url,
                                                                     0)
        resp = self.imgur._send_request(url)
        return [get_album_or_image(thing, self.imgur) for thing in resp]

    def get_statistics(self):
        """Return the statistics about the user."""
        # require being logged in
        url = "https://api.imgur.com/3/account/%s/stats" % self.url
        return self.imgur._send_request(url)

    def send_message(body, subject=None, parent_id=None):
        """Send a message to this user from the logged in user."""
        pass

    @require_auth
    def send_verification_email(self):
        pass


# Gallery_album and Gallery_image are placed at the end as they need to inherit
# from Gallery_item, Album and Image. It's thus impossible to place them
# alphabetically without errors.
class Gallery_album(Album, Gallery_item):
    def __init__(self, json_dict, imgur):
        self._INFO_URL = ("https://api.imgur.com/3/gallery/album/%s" %
                          json_dict['id'])
        super(Gallery_album, self).__init__(json_dict, imgur)


class Gallery_image(Image, Gallery_item):
    def __init__(self, json_dict, imgur):
        self._INFO_URL = ("http://api.imgur.com/3/gallery/image/%s" %
                          json_dict['id'])
        super(Gallery_image, self).__init__(json_dict, imgur)
