import csv
import hashlib
import os
import sys
from sqlalchemy import engine_from_config
from pylons import config
import common
from ckan import model
import ckan.plugins.toolkit as toolkit

from running_stats import StatsList

stats = StatsList()

TEMPLATE = u"""
      {% if item.economic and item.economic_comment %}
        <p>
            <b>Economic Growth</b>
            <br/>
            {{ item.economic_comment }}
        </p>
      {% endif %}
      {% if item.social %}
        <p>
            <b>Social Growth</b>
            <br/>
            {{ item.social_comment }}
        </p>
      {% endif %}
      {% if item.effective %}
        <p>
            <b>Effective Public Services</b>
            <br/>
            {{ item.effective_comment }}
        </p>
      {% endif %}
      {% if item.linked %}
        <p>
            <b>Potential links to other datasets</b>
            <br/>
            {{ item.linked_comment }}
        </p>
      {% endif %}
      {% if item.other and item.other_comment %}
        <p>
            <b>Other Benefits</b>
            <br/>
            {{ item.other_comment }}
        </p>
      {% endif %}

      <p><i>This comment was generated from feedback about the potential value of this dataset</i><p>

""".strip()

class ExportFeedback(object):


    @classmethod
    def command(cls, config_ini):
        common.load_config(config_ini)
        common.register_translator()

        from ckanext.dgu.model.feedback import Feedback

        comment_hashes = []

        headers = ["user_id", "package_id", "timestamp", "title", "comment"]
        writer = csv.DictWriter(sys.stdout, headers)

        for fb in model.Session.query(Feedback)\
                .filter(Feedback.visible==True)\
                .filter(Feedback.active==True)\
                .order_by(Feedback.created):

            if not any([fb.economic, fb.social, fb.effective, fb.linked, fb.other]):
                stats.add('Missing any content', fb.id )
                continue

            user = model.User.get(fb.user_id)
            pkg = model.Package.get(fb.package_id)

            data = {
                u"timestamp": fb.created.isoformat(),
                u"package": pkg.name,
                u"item": fb
            }


            content = render_template(TEMPLATE, data)
            comment = content.replace(u'\r',u'').replace(u'\n',u'').replace(u'           ', u'')

            # Check for identical comments ... we want users duplicating comments on
            # the same package (by mistake most often).
            hashkey = u'{}.{}.{}'.format(comment, fb.package_id, fb.user_id).encode('utf8', 'ignore')
            comment_hash = hashlib.md5(hashkey).hexdigest()

            if comment_hash in comment_hashes:
                stats.add('Duplicate post', fb.id )
                continue

            comment_hashes.append(comment_hash)

            row = {
                u"user_id": user.name[len("user_d"):],
                u"package_id": pkg.name,
                u"timestamp": fb.created.isoformat(),
                u"title": "Feedback on the value of this dataset ",
                u"comment": comment.encode('utf-8', 'ignore')
            }
            writer.writerow(row)

            stats.add('Processed', fb.id )

        #print stats.report()

def render_template(template_text, extra_vars):
    env = config['pylons.app_globals'].jinja_env
    template = env.from_string(template_text)
    return template.render(**extra_vars)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Need to specify config location"
        sys.exit(0)
    config_ini = sys.argv[1]
    ExportFeedback.command(config_ini)


