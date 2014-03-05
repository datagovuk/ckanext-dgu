import os
import csv
import logging
import json
from urllib import urlencode

from pylons import response, config
from ckan import model
from ckan.model.types import make_uuid
from ckan.lib.helpers import Page, flash_notice
from ckanext.dgu.lib.helpers import get_from_flat_dict
from ckan.lib.base import h, BaseController, abort, g
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckanext.dgu.lib.publisher import go_down_tree
from ckan.lib.search import SearchIndexError
from ckan.logic import tuplize_dict, clean_dict, parse_params, flatten_to_string_key
from ckanext.dgu.plugins_toolkit import (render, c, request, _,
    ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access)
from ckanext.dgu.lib import helpers as dgu_helpers

log = logging.getLogger(__name__)

class CommitmentController(BaseController):

    def index(self):
        from ckanext.dgu.model.commitment import Commitment, ODS_ORGS
        c.publishers = model.Session.query(model.Group)\
            .filter(model.Group.state=='active')\
            .filter(model.Group.name.in_(ODS_ORGS.values()))\
            .order_by(model.Group.title).all()
        c.commitments = model.Session.query(Commitment).filter(Commitment.state=='active').all()

        return render('commitment/index.html')

    def commitments(self, id):
        """
        Shows all of the commitments for the specified publisher
        """
        from ckanext.dgu.model.commitment import Commitment

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params}

        try:
            c.publisher_dict = get_action('organization_show')(context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to read commitments'))
        except ObjectNotFound:
            abort(404, _('Publisher not found'))

        c.publisher = context.get('group')
        c.commitments = Commitment.get_for_publisher(c.publisher.name)\
            .order_by('commitment.dataset_name').all()

        return render('commitment/read.html')

    def _save(self, context, data_dict, publisher):
        import ckan.model as model
        import ckanext.dgu.model.commitment as cmodel

        for _, items in data_dict.iteritems():
            # items is now a list of dicts that can all be processed
            # individually if they have an ID, then we're updating,
            # if they don't they're new.
            for item in items:
                commitment = None

                if not item.get('commitment_text') and not item.get('dataset_name', ''):
                    # TODO: We're ignoring empty dicts here as unfilled items but we
                    # might well want to do some error checking too
                    continue

                if item.get('id'):
                    # Get the current commitment
                    commitment = cmodel.Commitment.get(item.get('id'))
                    commitment.source = item.get('source')
                else:
                    commitment = cmodel.Commitment(source=item.get('source'))

                # text, notes, dataset (or url)
                commitment.commitment_text = item.get('commitment_text', '')
                commitment.notes = item.get('notes', '')
                commitment.dataset = item.get('dataset') or item.get('url')
                commitment.dataset_name = item.get('dataset_name', '')
                commitment.publisher = publisher.name
                commitment.author = c.user
                commitment.state = 'active'

                model.Session.add(commitment)

            # Commit each source to the database
            model.Session.commit()

        log.info("Commitments for {0} updated by {1}".format(publisher.name, c.user))


    def edit(self, id):
        """
        Allows editing of commitments for a specific publisher
        """
        from ckanext.dgu.model.commitment import Commitment

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'extras_as_string': True,
                   'save': 'save' in request.params}

        try:
            check_access('organization_update', {'id': id})
        except Exception, e:
            abort(401, "Not authorised")

        try:
            c.publisher_dict = get_action('organization_show')(context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorised to read commitments'))
        except ObjectNotFound:
            abort(404, _('Publisher not found'))

        c.publisher = context.get('group')
        c.errors = {}

        if request.method == "POST":
            from ckan.logic import clean_dict, tuplize_dict, parse_params
            from ckan.lib.navl.dictization_functions import unflatten
            data_dict = clean_dict(unflatten(tuplize_dict(parse_params(request.params))))
            self._save(context, data_dict, c.publisher)


        # We'll prefetch the available datasets for this publisher and add them to the drop-down
        # on the page so that we don't have to work out how to constrain an autocomplete.
        c.packages = model.Session.query(model.Package.name, model.Package.title)\
            .filter(model.Package.state == 'active')\
            .filter(model.Package.owner_org == c.publisher.id )\
            .order_by(model.Package.title).all()

        if request.method == "POST":
            # need to flatten the request into some commitments, if there is an ID then
            # we should update them, if there isn't then add them.
            # TODO: Work out how to remove them. Perhaps get the current IDs and do a diff
            # If successful redirect to read()

            h.redirect_to(h.url_for(controller='ckanext.dgu.controllers.commitment:CommitmentController',
                action='commitments', id=c.publisher.name))


        c.commitments = Commitment.get_for_publisher(c.publisher.name).order_by('commitment.commitment_text')

        return render('commitment/edit.html')



