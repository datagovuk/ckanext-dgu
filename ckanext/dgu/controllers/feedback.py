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

    def _get_form_data(self, package):
        """
        Extracts the parameters from the POST request and stores them
        in a feedback model.

        TODO: This should be in the logic layer.  Along with the
              appropriate auth.
        """
        from ckanext.dgu.lib.spam_check import is_spam, MOLLOM_SPAM, MOLLOM_HAM
        from ckanext.dgu.model.feedback import Feedback

        # TODO: This is a bit dense, could do with cleaning up.
        data = {'package_id': package.id, 'user_id': c.user}
        data["economic"] = asbool(request.POST.get('economic', False))
        data["economic_comment"] = request.POST.get('economic_comment', u'')
        data["social"] = asbool(request.POST.get('social', False))
        data["social_comment"] = request.POST.get('social_comment', u'')
        data["effective"] = asbool(request.POST.get('effective', False))
        data["effective_comment"] = request.POST.get('effective_comment', u'')
        data["other"] = asbool(request.POST.get('other', False))
        data["other_comment"] = request.POST.get('other_comment', u'')
        if request.POST.get('linked', '') == 'dontknow':
            data["linked"] = False
        else:
            data["linked"] = asbool(request.POST.get('linked', False))

        data["linked_comment"] = request.POST.get('linked_comment', u'')

        data["responding_as"] = request.POST.get('responding_as', u'individual')
        if data["responding_as"] == 'organisation':
            data["organisation"] = request.POST.get('organisation', u'')
            data["organisation_name"] = request.POST.get('organisation_name', u'')
        data["contact"] = asbool(request.POST.get('contact', False))

        # Concatenate all of the comments, and then do a spam check if we have
        # anything to send.
        comments = [data["economic_comment"] or '', data["social_comment"] or '',
                    data["effective_comment"] or '', data["other_comment"] or '',
                    data["linked_comment"] or '']
        content = [ct for ct in comments if ct.strip() != u""]
        if ''.join(content).strip():
            success, flag = is_spam('\n'.join(content), c.userobj)
        else:
            log.warning("No comments to send for spam check")
            success,flag = True, MOLLOM_HAM

        msg = "Thank you for your feedback"
        if not success:
            # If we fail to check spam, force into moderation
            data["moderation_required"] = True
            msg = "Thank you for your feedback. " \
                  "Your comments have been marked for moderation."
        else:
            data["spam_score"] = flag
            if flag == MOLLOM_SPAM:
                data["moderation_required"] = True
                data["visible"] = False
                msg = "Your post has been identified as spam and has not been posted."

        flash_notice(msg)
        return Feedback(**data)

    def report_abuse(self, id):
        """
        When a user reports something as offensive, this action will mark it
        ready for moderation.  If the user reporting is a system administrator
        it will be marked, but also made invisible so that it no longer shows up
        """
        import ckan.model as model
        from ckanext.dgu.model.feedback import Feedback

        fb = Feedback.get(id)
        if fb:
            fb.moderated = False
            fb.moderation_required = True
            if is_sysadmin():
                fb.visible = False
                flash_notice("Queued. As you are an administrator, this item has been hidden")
            else:
                flash_notice("Thank you for your feedback, the item has been queued for moderation")
            model.Session.add(fb)
            model.Session.commit()

        h.redirect_to(request.referer or '/data')

    def add(self, id):
        """
        Adds new feedback from a user, first checking that the user is
            a. Logged in (in which case they are redirected)
            b. Not blocked
        """
        from ckanext.dgu.model.feedback import Feedback, FeedbackBlockedUser
        self._get_package(id)

        # Redirect to login if not logged in
        try:
            context = {'model':model,'user': c.user}
            check_access('feedback_create',context)
        except NotAuthorized, e:
            h.redirect_to('/user?destination={0}'.format(request.path[1:]))

        if request.method == "POST":
            if FeedbackBlockedUser.is_user_blocked(c.user):
                # We let the user go through the process of submitting, but then
                # we will not actually process what they send if they have been
                # blocked previously.
                log.info("Feedback ignored from blocked user {0}".format(c.user))
                h.redirect_to(controller='ckanext.dgu.controllers.feedback:FeedbackController',
                                action='view', id=c.pkg.name)

            data = self._get_form_data(c.pkg)
            model.Session.add(data)
            model.Session.commit()

            h.redirect_to(controller='ckanext.dgu.controllers.feedback:FeedbackController',
                action='view', id=c.pkg.name)

        c.form = render('feedback/add_form.html')
        return render('feedback/add.html')

    def view(self, id):
        """ View all feedback for the specified package """
        from ckanext.dgu.model.feedback import Feedback
        self._get_package(id)

        c.items = model.Session.query(Feedback).\
            filter(Feedback.package_id == c.pkg.id).\
            filter(Feedback.visible == True).\
            filter(Feedback.active==True).order_by('created desc')

        return render('feedback/view.html')

    def moderate(self, id):
        """
        Accepts a feedback ID and in the get it accepts one or more of ...
            delete, publish, delete_and_ban within the action param
        """
        import ckan.model as model
        from ckanext.dgu.model.feedback import Feedback, FeedbackBlockedUser

        def status(success, msg=''):
            return json.dumps({'success': success, 'message': msg})

        # Only system administrators may access this page.
        try:
            context = {'model':model,'user': c.user}
            check_access('feedback_update',context)
        except NotAuthorized, e:
            return status('error', 'Permission denied')

        fb = Feedback.get(id)
        if not fb:
            return status('error', 'Feedback not found')

        action = request.params.get('action', '')
        if not action:
            return status('error', 'Unknown action')

        fb.moderated_by = c.user

        # Perform the relevant action based on what we have been asked to do.
        if action == 'delete':
            fb.active = False
            model.Session.add(fb)
        elif action == 'delete_and_ban':
            fb.active = False
            model.Session.add(fb)
            # Block the user from posting again.
            fbb = FeedbackBlockedUser(user_id=fb.user_id, blocked_by=c.user, feedback_id=id)
            model.Session.add(fbb)
        elif action == 'publish':
            fb.moderated = True
            fb.visible = True
            fb.moderation_required = False
            model.Session.add(fb)
        model.Session.commit()

        return status('ok')

    def moderation(self):
        """
        The moderation queue will show all items that are currently:
            - Requiring moderation
            - Not already moderated

        We should implement paging here.
        """
        from ckanext.dgu.model.feedback import Feedback

        try:
            context = {'model':model,'user': c.user}
            check_access('feedback_update',context)
        except NotAuthorized, e:
            abort(403)

        c.items = model.Session.query(Feedback).\
            filter(Feedback.moderation_required == True).\
            filter(Feedback.moderated == False).\
            filter(Feedback.active==True).order_by('created desc')

        return render('feedback/moderate.html')

