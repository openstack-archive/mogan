# Copyright 2017 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import pecan
from pecan import rest
from six.moves import http_client
import wsme
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import aggregate as agg_schema
from mogan.api.controllers.v1 import types
from mogan.api.controllers.v1 import utils as api_utils
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import policy
from mogan import objects


class Aggregate(base.APIBase):
    """API representation of an aggregate.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    an aggregate.
    """
    uuid = types.uuid
    """The UUID of the aggregate"""

    name = wtypes.text
    """The name of the aggregate"""

    metadata = {wtypes.text: types.jsontype}
    """The meta data of the aggregate"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.Aggregate.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, db_aggregate):
        aggregate = Aggregate(**db_aggregate.as_dict())
        url = pecan.request.public_url
        aggregate.links = [link.Link.make_link('self', url,
                                               'aggregates',
                                               aggregate.uuid),
                           link.Link.make_link('bookmark', url,
                                               'aggregates',
                                               aggregate.uuid,
                                               bookmark=True)
                           ]

        return aggregate


class AggregatePatchType(types.JsonPatchType):

    _api_base = Aggregate


class AggregateCollection(base.APIBase):
    """API representation of a collection of aggregates."""

    aggregates = [Aggregate]
    """A list containing Aggregate objects"""

    @staticmethod
    def convert_with_links(aggregates, url=None, **kwargs):
        collection = AggregateCollection()
        collection.aggregates = [Aggregate.convert_with_links(aggregate)
                                 for aggregate in aggregates]
        return collection


class AggregateNodeController(rest.RestController):
    """REST controller for aggregate nodes."""

    def _check_aggregates_conflict(self, node, node_aggregates, key, value):
        """Check aggregates conflict with the given key"""
        aggregates = objects.AggregateList.get_by_metadata_key(
            pecan.request.context, key)
        conflicts = [
            agg.metadata[key] for agg in aggregates
            if agg.uuid in node_aggregates and
            agg.metadata[key] != value]
        if conflicts:
            msg = _("Node %(node)s is already in %(key)s(s) "
                    "%(conflicts)s") % {"node": node, "key": key,
                                        "conflicts": conflicts}
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

    @policy.authorize_wsgi("mogan:aggregate_node", "get_all")
    @expose.expose(wtypes.text, types.uuid)
    def get_all(self, aggregate_uuid):
        """Retrieve a list of nodes of the queried aggregate."""
        # check whether the aggregate exists
        objects.Aggregate.get(pecan.request.context, aggregate_uuid)

        nodes = pecan.request.engine_api.list_aggregate_nodes(
            pecan.request.context, aggregate_uuid)

        return nodes

    @policy.authorize_wsgi("mogan:aggregate_node", "create")
    @expose.expose(None, types.uuid, body=types.jsontype,
                   status_code=http_client.NO_CONTENT)
    def post(self, aggregate_uuid, node):
        """Add node to the given aggregate."""
        validation.check_schema(node, agg_schema.add_aggregate_node)

        node = node['node']
        db_aggregate = objects.Aggregate.get(pecan.request.context,
                                             aggregate_uuid)
        node_aggregates = pecan.request.engine_api.list_node_aggregates(
            pecan.request.context, node)
        # check whether the node is already in another az
        if 'availability_zone' in db_aggregate['metadata']:
            self._check_aggregates_conflict(
                node, node_aggregates['aggregates'], 'availability_zone',
                db_aggregate.metadata['availability_zone'])
        # check whether the node is already in another affinity zone
        if 'affinity_zone' in db_aggregate['metadata']:
            self._check_aggregates_conflict(
                node, node_aggregates['aggregates'], 'affinity_zone',
                db_aggregate.metadata['affinity_zone'])

        pecan.request.engine_api.add_aggregate_node(
            pecan.request.context, aggregate_uuid, node)

    @policy.authorize_wsgi("mogan:aggregate_node", "delete")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, aggregate_uuid, node):
        """Remove node from the given aggregate."""
        # check whether the aggregate exists
        objects.Aggregate.get(pecan.request.context, aggregate_uuid)

        pecan.request.engine_api.remove_aggregate_node(
            pecan.request.context, aggregate_uuid, node)


class AggregateController(rest.RestController):
    """REST controller for Aggregates."""

    nodes = AggregateNodeController()

    def _check_metadata_conflicts(self, aggregate_uuid, key, value):
        """Check if metadata conflict with the given key"""

        nodes = pecan.request.engine_api.list_aggregate_nodes(
            pecan.request.context, aggregate_uuid)
        aggregates = objects.AggregateList.get_by_metadata_key(
            pecan.request.context, key)
        filtered_aggs = []
        for agg in aggregates:
            agg_nodes = \
                pecan.request.engine_api.list_aggregate_nodes(
                    pecan.request.context, agg.uuid)
            for node in agg_nodes['nodes']:
                if node in nodes['nodes']:
                    filtered_aggs.append(agg)
                    break

        conflicts = [agg.metadata[key] for agg in filtered_aggs
                     if agg.metadata[key] != value and
                     agg.uuid != aggregate_uuid]
        if conflicts:
            msg = _("One or more nodes already in different "
                    "%(key)s(s) %(conflicts)s") % {"key": key,
                                                   "conflicts": conflicts}
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

    def _is_safe_to_update_metadata(self, patch, aggregate_uuid):
        """Check if it's safe to update aggregate metadata"""

        keys = ['availability_zone', 'affinity_zone']
        # Check if this tries to change *keys* to empty.
        for patch_dict in patch:
            for key in keys:
                if patch_dict['path'] == '/metadata/' + key \
                        and patch_dict['op'] != 'remove':
                    if not patch_dict['value']:
                        msg = _("Aggregate %(uuid)s does not support empty "
                                "named %(key)s") % {"uuid": aggregate_uuid,
                                                    "key": key}
                        raise wsme.exc.ClientSideError(
                            msg, status_code=http_client.BAD_REQUEST)
                    else:
                        self._check_metadata_conflicts(
                            aggregate_uuid, key, patch_dict['value'])

    @policy.authorize_wsgi("mogan:aggregate", "get_all")
    @expose.expose(AggregateCollection)
    def get_all(self):
        """Retrieve a list of aggregates."""

        aggregates = objects.AggregateList.get_all(pecan.request.context)
        return AggregateCollection.convert_with_links(aggregates)

    @policy.authorize_wsgi("mogan:aggregate", "get_one")
    @expose.expose(Aggregate, types.uuid)
    def get_one(self, aggregate_uuid):
        """Retrieve information about the given aggregate.

        :param aggregate_uuid: UUID of an aggregate.
        """
        db_aggregate = objects.Aggregate.get(pecan.request.context,
                                             aggregate_uuid)
        return Aggregate.convert_with_links(db_aggregate)

    @policy.authorize_wsgi("mogan:aggregate", "create")
    @expose.expose(Aggregate, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, aggregate):
        """Create a new aggregate.

        :param aggregate: an aggregate within the request body.
        """
        validation.check_schema(aggregate, agg_schema.create_aggregate)
        metadata = aggregate.get('metadata')
        if metadata:
            for key in ['availability_zone', 'affinity_zone']:
                if key in metadata and not metadata[key]:
                    msg = _("Aggregate %(name)s does not support empty named "
                            "%(key)s") % {"name": aggregate['name'],
                                          "key": key}
                    raise wsme.exc.ClientSideError(
                        msg, status_code=http_client.BAD_REQUEST)

        new_aggregate = objects.Aggregate(pecan.request.context, **aggregate)
        new_aggregate.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('aggregates',
                                                 new_aggregate.uuid)
        return Aggregate.convert_with_links(new_aggregate)

    @policy.authorize_wsgi("mogan:aggregate", "update")
    @wsme.validate(types.uuid, [AggregatePatchType])
    @expose.expose(Aggregate, types.uuid, body=[AggregatePatchType])
    def patch(self, aggregate_uuid, patch):
        """Update an aggregate.

        :param aggregate_uuid: the uuid of the aggregate to be updated.
        :param aggregate: a json PATCH document to apply to this aggregate.
        """

        db_aggregate = objects.Aggregate.get(pecan.request.context,
                                             aggregate_uuid)

        try:
            aggregate = Aggregate(
                **api_utils.apply_jsonpatch(db_aggregate.as_dict(), patch))

        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Check whether it is safe to update metadata
        self._is_safe_to_update_metadata(patch, db_aggregate['uuid'])

        # Update only the fields that have changed
        for field in objects.Aggregate.fields:
            try:
                patch_val = getattr(aggregate, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if db_aggregate[field] != patch_val:
                db_aggregate[field] = patch_val

        db_aggregate.save()

        return Aggregate.convert_with_links(db_aggregate)

    @policy.authorize_wsgi("mogan:aggregate", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, aggregate_uuid):
        """Delete an aggregate.

        :param aggregate_uuid: UUID of an aggregate.
        """
        db_aggregate = objects.Aggregate.get(pecan.request.context,
                                             aggregate_uuid)
        pecan.request.engine_api.remove_aggregate(pecan.request.context,
                                                  aggregate_uuid)
        db_aggregate.destroy()
