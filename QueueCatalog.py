##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
# 
##############################################################################
"""
$Id$
"""

from zExceptions import Unauthorized
from ExtensionClass import Base
from OFS.SimpleItem import SimpleItem
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityInfo import ClassSecurityInformation
from AccessControl.Permissions import manage_zcatalog_entries
from OFS.SimpleItem import SimpleItem
from BTrees.OOBTree import OOBTree
from time import time
from CatalogEventQueue import CatalogEventQueue, EVENT_TYPES, ADDED_EVENTS
from CatalogEventQueue import ADDED, CHANGED, CHANGED_ADDED, REMOVED
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Globals import DTMLFile
from Acquisition import Implicit, aq_base, aq_inner, aq_parent
from types import StringType

_zcatalog_methods = {
    'catalog_object': 1,
    'uncatalog_object': 1,
    'uniqueValuesFor': 1,
    'getpath': 1,
    'getrid': 1,
    'getobject': 1,
    'schema': 1,
    'indexes': 1,
    'index_objects': 1,
    'searchResults': 1,
    '__call__': 1,
    }

_is_zcatalog_method = _zcatalog_methods.has_key

_views = {}


class QueueConfigurationError(Exception):
    pass


class QueueCatalog(Implicit, SimpleItem):
    """Queued ZCatalog (Proxy)

    A QueueCatalog delegates most requests to a ZCatalog that is named
    as part of the QueueCatalog configuration.

    Requests to catalog or uncatalog objects are queued. They must be
    processed by a separate process (or thread). The queuing provides
    benefits:

    - Content-management operations, performed by humans, complete
      much faster, this making the content-management system more
      effiecient for it's users.

    - Catalog updates are batched, which makes indexing much more
      efficient.

    - Indexing is performed by a single thread, allowing more
      effecient catalog document generation and avoiding conflict
      errors from occuring during indexing.

    - When used with ZEO, indexing might e performed on the same
      machine as the storage server, making updates faster.
      
    """

    security = ClassSecurityInformation()

    _immediate_indexes = ()  # The names of indexes to update immediately
    _location = None
    _immediate_removal = 1   # Flag: don't queue removal
    title = ''

    # When set, _v_catalog_cache is a tuple containing the wrapped ZCatalog
    # and the REQUEST it is bound to.
    _v_catalog_cache = None

    def __init__(self, buckets=1009):
        self._buckets = buckets
        self._clearQueues()

    def _clearQueues(self):
        self._queues = [CatalogEventQueue() for i in range(self._buckets)]

    def getTitle(self):
        return self.title

    def setLocation(self, location):
        if self._location is not None:
            try:
                self.process()
            except QueueConfigurationError:
                self._clearQueues()
        self._location = location

    def getIndexInfo(self):
        try:
            c = self.getZCatalog()
        except QueueConfigurationError:
            return None
        else:
            items = [(ob.id, ob.meta_type) for ob in c.getIndexObjects()]
            items.sort()
            res = []
            for id, meta_type in items:
                res.append({'id': id, 'meta_type': meta_type})
            return res

    def getImmediateIndexes(self):
        return self._immediate_indexes

    def setImmediateIndexes(self, indexes):
        self._immediate_indexes = tuple(map(str, indexes))


    def getImmediateRemoval(self):
        return self._immediate_removal

    def setImmediateRemoval(self, flag):
        self._immediate_removal = not not flag


    def getZCatalog(self, method=''):
        ZC = None
        REQUEST = getattr(self, 'REQUEST', None)
        cache = self._v_catalog_cache
        if cache is not None:
            # The cached catalog may be wrapped with an earlier
            # request.  Before using it, check the request.
            (ZC, req) = cache
            if req is not REQUEST:
                # It's an old wrapper.  Discard.
                ZC = None

        if ZC is None:
            if self._location is None:
                raise QueueConfigurationError(
                    "This QueueCatalog hasn't been "
                    "configured with a ZCatalog location."
                    )
            parent = aq_parent(aq_inner(self))
            try:
                ZC = parent.unrestrictedTraverse(self._location)
            except (KeyError, AttributeError):
                raise QueueConfigurationError(
                    "ZCatalog not found at %s." % self._location
                    ) 
            if not hasattr(ZC, 'getIndexObjects'):  # XXX need a better check
                raise QueueConfigurationError(
                    "The object at %s does not implement the "
                    "IZCatalog interface." % self._location
                    )

            security_manager = getSecurityManager()
            if not security_manager.validateValue(ZC):
                raise Unauthorized(self._location, ZC)

            ZC = aq_base(ZC).__of__(parent)
            self._v_catalog_cache = (ZC, REQUEST)

        if method:
            if not _is_zcatalog_method(method):
                raise AttributeError(method)
            m = getattr(ZC, method)
            # Note that permission to access the method may be checked
            # later on.  This isn't the right place to check permission.
            return m
        else:
            return ZC

    def __getattr__(self, name):
        # The original object must be wrapped, but self isn't, so
        # we return a special object that will do the attribute access
        # on a wrapped object. 
        if _is_zcatalog_method(name):
            return AttrWrapper(name)

        raise AttributeError(name)

    def _update(self, uid, etype):
        t = time()
        self._queues[hash(uid) % self._buckets].update(uid, etype)
        
    def catalog_object(self, obj, uid=None):

        # Make sure the current context is allowed to to this:
        catalog_object = self.getZCatalog('catalog_object')
        
        if uid is None:
            uid = '/'.join(obj.getPhysicalPath())
        elif not isinstance(uid, StringType):
            uid = '/'.join(uid)

        catalog = self.getZCatalog()

        # The ZCatalog API doesn't allow us to distinguish between
        # adds and updates, so we have to try to figure this out
        # ourselves.

        # There's a risk of a race here. What if there is a previously
        # unprocessed add event? If so, then this should be a changed
        # event. If we undo this transaction later, we'll generate a
        # remove event, when we should generate an add changed event.
        # To avoid this, we need to make sure we see consistent values
        # of the event queue. We also need to avoid resolving
        # (non-undo) conflicts of add events. This will slow things
        # down a bit, but adds should be relatively infrequent. 

        # Now, try to decide if the catalog has the uid (path).

        if cataloged(catalog, uid):
            event = CHANGED
        else:
            # Looks like we should add, but maybe there's already a
            # pending add event. We'd better check the event queue:
            if (self._queues[hash(uid) % self._buckets].getEvent(uid) in
                ADDED_EVENTS):
                event = CHANGED
            else:
                event = ADDED

        self._update(uid, event)

        if self._immediate_indexes:
            # Update some of the indexes immediately.
            try:
                catalog.catalog_object(obj, uid, self._immediate_indexes)
            except:
                pass


    def uncatalog_object(self, uid):

        # Make sure the current context is allowed to to this:
        self.getZCatalog('uncatalog_object')

        if not isinstance(uid, StringType):
            uid = '/'.join(uid)

        self._update(uid, REMOVED)

        if self._immediate_removal:
            self.process()


    def process(self):
        "Process pending events"
        catalog = self.getZCatalog()
        for queue in filter(None, self._queues):
            events = queue.process()
            for uid, (t, event) in events.items():
                if event is REMOVED:
                    if cataloged(catalog, uid):
                        catalog.uncatalog_object(uid)
                else:
                    # add or change
                    if event is CHANGED and not cataloged(catalog, uid):
                        continue
                    # Note that the uid may be relative to the catalog.
                    obj = catalog.unrestrictedTraverse(uid)
                    try:
                        catalog.catalog_object(obj, uid)
                    except:
                        # Something went wrong, put back in the queue
                        self._update(uid, event)

    #
    # CMF catalog tool methods.
    #
    security.declarePrivate('indexObject')
    def indexObject(self, object):
        """Add to catalog.
        """
        self.catalog_object(object)

    security.declarePrivate('unindexObject')
    def unindexObject(self, object):
        """Remove from catalog.
        """
        url = '/'.join(object.getPhysicalPath())
        self.uncatalog_object(url)

    security.declarePrivate('reindexObject')
    def reindexObject(self, object, idxs=[]):
        """Update catalog after object data has changed.

        The optional idxs argument is a list of specific indexes
        to update (all of them by default).
        """
        # Punt for now and ignore idxs.
        self.catalog_object(object)

    # Provide web pages. It would be nice to use views, but Zope 2.6
    # just isn't ready for views. :( In particular, we'd have to fake
    # out the PageTemplateFiles in some brittle way to make them do
    # the right thing. :(

    manage_editForm = PageTemplateFile('www/edit', globals())

    def manage_getLocation(self):
        return self._location or ''

    def manage_edit(self, title='', location='', immediate_indexes=(),
                    immediate_removal=0, RESPONSE=None):
        """ Edit the instance """
        self.title = title
        self.setLocation(location or None)
        self.setImmediateIndexes(immediate_indexes)
        self.setImmediateRemoval(immediate_removal)

        if RESPONSE is not None:
            RESPONSE.redirect('%s/manage_editForm?manage_tabs_message='
                              'Properties+changed' % self.absolute_url())
        
    
    manage_queue = DTMLFile('dtml/queue', globals())

    def manage_size(self):
        size = 0
        for q in self._queues:
            size += len(q)

        return size

    def manage_process(self, REQUEST):
        "Web UI to manually process queues"
        # make sure we have necessary perm
        self.getZCatalog('catalog_object')
        self.getZCatalog('uncatalog_object')
        self.process()

        msg = 'Queue processed'
        return self.manage_queue(manage_tabs_message=msg)
    
    # Provide Zope 2 offerings

    index_html = None

    meta_type = 'ZCatalog Queue'

    manage_options=(
        (
        {'label': 'Configure', 'action': 'manage_editForm',
         'help':('QueueCatalog','QueueCatalog-Configure.stx')},

        {'label': 'Queue', 'action': 'manage_queue',
         'help':('QueueCatalog','QueueCatalog-Queue.stx')},
        )
        +SimpleItem.manage_options
        )

    security.declareObjectPublic()
    # Disallow access to subobjects with no security assertions.
    security.setDefaultAccess('deny')

    security.declarePublic('manage_process', 'getTitle', 'title_or_id')

    security.declareProtected(manage_zcatalog_entries,
                              'catalog_object', 'uncatalog_object')

    security.declareProtected(
        'View management screens',
        'manage_editForm', 'manage_edit',
        'manage_queue', 'manage_getLocation',
        'manage_size', 'getIndexInfo', 'getImmediateIndexes',
        'getImmediateRemoval',
        )
    
def cataloged(catalog, path):
    getrid = getattr(catalog, 'getrid', None)
    if getrid is None:
        
        # This is an old catalog that doesn't provide an API for
        # getting an objects rid (and thus determing that the
        # object is already cataloged.
        
        # We'll just use our knowledge of the internal structure.
        
        rid = catalog._catalog.uids.get(path)
        
    else:
        rid = catalog.getrid(path)

    return rid is not None

class AttrWrapper(Base):
    "Special object that allowes us to use acquisition in QueueCatalog "
    "attribute access"

    def __init__(self, name):
        self.__name__ = name

    def __of__(self, wrappedQueueCatalog):
        return wrappedQueueCatalog.getZCatalog(self.__name__)

__doc__ = QueueCatalog.__doc__ + __doc__

