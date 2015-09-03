"""
The FeedbackController is responsible for processing requests related to the
unpublished feedback that allows users and admins to record feedback in a
specific format against unpublished datasets.
"""
import logging
import json
from ckan import model
from paste.deploy.converters import asbool
from ckan.lib.helpers import flash_notice, render_markdown
from ckan.lib.base import h, BaseController, abort
from ckanext.dgu.lib.helpers import (unpublished_release_notes,
                                     is_sysadmin)
from ckanext.dgu.plugins_toolkit import (render, c, request, _,
                                         ObjectNotFound, NotAuthorized,
                                         get_action, check_access)

log = logging.getLogger(__name__)


class FeedbackController(BaseController):

    def _get_package(self, id):
        """
        Given an ID use the logic layer to fetch the Package and a
        dict representation of it as well as adding formatted notes
        and the publisher to the template context (c).
        """
        import genshi

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}

        try:
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            c.pkg = context['package']
        except ObjectNotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        c.publisher = c.pkg.get_organization()
        if not c.publisher:
            log.warning("Package {0} is not a member of any group!".format(id))

        # Try and render the notes as markdown for display on the page.  Most
        # unpublished items *won't* be markdown if they've come directly from the
        # CSV - unless they've been edited.
        try:
            notes_formatted = render_markdown(c.pkg.notes)
            c.pkg_notes_formatted = unicode(genshi.HTML(notes_formatted))
            c.release_notes_formatted = None

            notes = unpublished_release_notes(c.pkg_dict)
            if notes and notes.strip():
                c.release_notes_formatted = unicode(genshi.HTML(
                                    render_markdown(notes)))
        except Exception:
            c.pkg_notes_formatted = c.pkg.notes



    def view(self, id):
        """ View all feedback for the specified package """
        from ckanext.dgu.model.feedback import Feedback
        self._get_package(id)

        c.items = model.Session.query(Feedback).\
            filter(Feedback.package_id == c.pkg.id).\
            filter(Feedback.visible == True).\
            filter(Feedback.active==True).order_by('created desc')

        return render('feedback/view.html')

