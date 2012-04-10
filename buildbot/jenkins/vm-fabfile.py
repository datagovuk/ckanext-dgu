from __future__ import with_statement
from fabric.api import abort, run, cd, sudo, put
import os

def install_dgu_db():
    # Copy on the database dump to be loaded
    dumps = []
    for dump in os.listdir('/home/buildslave/dumps_gz'):
        if 'dgu.' in dump:
            dumps.append(dump)
    dumps.sort()
    sudo("mkdir -p /etc/ckan/dgu")
    put(
        os.path.join('/home/buildslave/dumps_gz', dumps[-1]), 
        '/tmp/latest.dump.gz',
    )
    sudo("mv /tmp/latest.dump.gz /etc/ckan/dgu/")
    sudo("gunzip /etc/ckan/dgu/latest.dump.gz")

def install_dgu(repo, instance='std', branch='master'):
    sudo("sudo bash /home/ubuntu/install_dgu.sh %s %s releasetest.ckan.org %s"%(repo, instance, branch))

    ## Provide test apt server 
    ## sudo("echo 'deb http://apt.ckan.org/ubuntu_ckan-%s lucid universe' > /etc/apt/sources.list.d/okfn.list" % instance)
    ## sudo("wget -qO-  http://apt.ckan.org/packages_public.key | sudo apt-key add -")

    #sudo("apt-get update")
    #sudo("apt-get install -y wget")
    #sudo('echo "deb http://apt.ckan.org/%s lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list' % repo)
    #sudo('wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -')
    #sudo('apt-get update')


    ## Update and install required packages
    #sudo("sudo apt-get install -y ckan postgresql-8.4 solr-jetty")
    #sudo("sudo ckan-setup-solr")
    #sudo("sudo ckan-create-instance %s releasetest.ckan.org yes" % instance)


