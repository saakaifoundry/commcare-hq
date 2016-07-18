from __future__ import absolute_import

import re
from abc import ABCMeta, abstractmethod
from uuid import uuid4

from corehq.blobs import DEFAULT_BUCKET
from corehq.blobs.exceptions import ArgumentError

SAFENAME = re.compile("^[a-z0-9_./{}-]+$", re.IGNORECASE)
NOT_SET = object()


class AbstractBlobDB(object):
    """Storage interface for large binary data objects
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def put(self, content, basename="", bucket=DEFAULT_BUCKET):
        """Put a blob in persistent storage

        :param content: A file-like object in binary read mode.
        :param basename: Optional name from which the blob name will be
        derived. This is used to make the unique blob name somewhat
        recognizable.
        :param bucket: Optional bucket name used to partition blob data
        in the persistent storage medium. This may be delimited with
        slashes (/). It must be a valid relative path.
        :returns: A `BlobInfo` named tuple. The returned object has a
        `identifier` member that must be used to get or delete the blob. It
        should not be confused with the optional `basename` parameter.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, identifier, bucket=DEFAULT_BUCKET):
        """Get a blob

        :param identifier: The identifier of the object to get.
        :param bucket: Optional bucket name. This must have the same
        value that was passed to ``put``.
        :returns: A file-like object in binary read mode. The returned
        object should be closed when finished reading.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, identifier=NOT_SET, bucket=NOT_SET):
        """Delete a blob or bucket of blobs

        Either one or both of `identifier` or `bucket` parameters
        is required.

        :param identifier: The identifier of the object to be deleted.
        The entire bucket will be deleted if this is not provided.
        :param bucket: Bucket name. This must have the same value that
        was passed to ``put``. Delete will be attempted in the default
        bucket if an identifier is given but the bucket is not given.
        Pass this parameter alone as a keyword argument to delete the
        entire bucket.
        :returns: True if the blob was deleted else false. None if it is
        not known if the blob was deleted or not.
        """
        raise NotImplementedError

    @abstractmethod
    def copy_blob(self, content, info, bucket):
        """Copy blob from other blob database

        :param content: File-like blob content object.
        :param info: `BlobInfo` object.
        :param bucket: Bucket name.
        """
        raise NotImplementedError

    @staticmethod
    def get_identifier(basename):
        if not basename:
            return uuid4().hex
        if SAFENAME.match(basename) and "/" not in basename:
            prefix = basename
        else:
            prefix = "unsafe"
        return prefix + "." + uuid4().hex

    @staticmethod
    def get_args_for_delete(identifier=NOT_SET, bucket=NOT_SET):
        if identifier is NOT_SET and bucket is NOT_SET:
            raise ArgumentError("'identifier' and/or 'bucket' is required")
        if identifier is None:
            raise ArgumentError("refusing to delete entire bucket when "
                                "null blob identifier is provided (either "
                                "provide a real blob identifier or pass "
                                "bucket as keyword argument)")
        if identifier is NOT_SET:
            assert bucket is not NOT_SET
            identifier = None
        elif bucket is NOT_SET:
            bucket = DEFAULT_BUCKET
        return identifier, bucket
