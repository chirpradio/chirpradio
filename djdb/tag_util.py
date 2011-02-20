###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

from datetime import datetime, timedelta

from google.appengine.ext import db

from djdb import models
from djdb import search
from common.autoretry import AutoRetry


def modify_tags_and_save(user, obj, to_add, to_remove):
    """Modify the set of tags attached to an object, and save to the datastore.

    Args:
      user: The User object of the person responsible for this change
        to the tags.
      obj: The object (either an Album or a Track) containing the tags.
      to_add: A sequence of tags to add to the object.
      to_remove: A sequence of tags to remove from the object.

    Returns:
      True if a modified version of the object was saved, or False if
      no changes were necessary.
    """
    to_add = list(set(to_add).difference(obj.current_tags))
    to_remove = list(set(to_remove).intersection(obj.current_tags))
    if not (to_add or to_remove):
        return False
    obj.current_tags = list(
        set(obj.current_tags).union(to_add).difference(to_remove))
    tag_edit = models.TagEdit(parent=obj, subject=obj, author=user,
                              added=to_add, removed=to_remove)
    # The two objects are in the same entity group, so saving them
    # is an all-or-nothing operation.
    AutoRetry(db).save([obj, tag_edit])
    
    # Update search indexer.
    idx = search.Indexer(obj.parent_key())
    for tag in to_remove:
        idx.remove_key(obj.key(), 'tag', tag)
    for tag in to_add:
        idx.add_key(obj.key(), 'tag', tag)
    idx.save()
    
    return True


def set_tags_and_save(user, obj, list_of_new_tags):
    """Assign a list of tags to an object, and save to the datastore.

    Args:
      user: The User object of the person responsible for this change
        to the tags.
      obj: The object (either an Album or a Track) containing the tags.
      list_of_new_tags: A sequence containing the tags to assign to the
        object.

    Returns:
      True if a modified version of the object was saved, or False if
      no changes were necessary.
    """
    to_add = list(set(list_of_new_tags).difference(obj.current_tags))
    to_remove = list(set(obj.current_tags).difference(list_of_new_tags))
    return modify_tags_and_save(user, obj, to_add, to_remove)


def add_tag_and_save(user, obj, new_tag, insert=False):
    """Adds a single tag to an object, and save to the datastore.

    Args:
      user: The User object of the person responsible for this change
        to the tags.
      obj: The object (either an Album or a Track) containing the tags.
      new_tag: A single item to add to the object's list of tags.
      insert: Whether to insert a new tag entity into the datastore.

    Returns:
      True if a modified version of the object was saved, or False if
      no changes were necessary.
    """
    if insert and AutoRetry(models.Tag.all().filter("name =", new_tag)).count() == 0:
        tag = models.Tag(name=new_tag)
        AutoRetry(tag).put()
        
    return modify_tags_and_save(user, obj, [new_tag], [])


def remove_tag_and_save(user, obj, tag_to_remove):
    """Removes a single tag from an object, and save to the datastore.

    Args:
      user: The User object of the person responsible for this change
        to the tags.
      obj: The object (either an Album or a Track) containing the tags.
      tag_to_remove: A single item to remove from the object's list of tags.

    Returns:
      True if a modified version of the object was saved, or False if
      no changes were necessary.
    """
    return modify_tags_and_save(user, obj, [], [tag_to_remove])

    
def fetch_recent(max_num_returned=10, days=None, start_dt=None):
    if days is not None:
        if start_dt:
            end_dt = start_dt + timedelta(days=days)
        else:
            end_dt = datetime.now() + timedelta(days=days)
    else:
        end_dt = None

    q = models.TagEdit.all().order('-timestamp')
    if start_dt:
        q.filter('timestamp >=', start_dt)
    if end_dt:
        q.filter('timestamp <', end_dt)
    tag_edits = q.fetch(max_num_returned);

    return tag_edits
    
