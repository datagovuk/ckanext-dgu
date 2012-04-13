#!/bin/bash

echo "Repo name is $1, dgu-branch is $2 and I am `whoami`."

# Check we are root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

NEWVMNAME=ckan
INSTALL_SCRIPT_PATH=/home/okfn/new/install_dgu.sh
echo "Stopping any current ${NEWVMNAME} instance ..."
sudo buildkit vm stop ${NEWVMNAME}
#echo "Found pid: `sudo buildkit vm status ckan | grep -v "PID" | awk '{print $1}'`"
#sudo buildkit vm status ckan | grep -v "PID" | awk '{print $1}' | xargs sudo kill -9
#sudo buildkit vm umount ckan 
echo "done."
echo "Removing the old ${NEWVMNAME} image ..."
sudo rm -rf /var/lib/buildkit/vm/${NEWVMNAME}
echo "done."
echo "Creating a new empty base image for ${NEWVMNAME} ..."
sudo mkdir /var/lib/buildkit/vm/${NEWVMNAME}
sudo qemu-img convert -f qcow2 -O raw /var/lib/buildkit/vm/base.qcow2 /var/lib/buildkit/vm/${NEWVMNAME}/disk.raw
sudo chown -R buildkit:buildkit /var/lib/buildkit/vm/${NEWVMNAME}
echo "done."
echo "Starting the command VM with the copy and execute commands set ..."
sudo buildkit vm start --mem 1512M --cpus 4 --apt-proxy --copy-file="/home/buildslave/dumps/latest.pg_dump -> /home/ubuntu/dgu_live.pg_dump" --copy-file="/home/buildslave/dumps/users.csv -> /home/ubuntu/users.csv" --tunnel qtap8 --copy-file="${INSTALL_SCRIPT_PATH} -> /home/ubuntu/install_dgu.sh" ${NEWVMNAME}
#--exec-on-boot=". /home/ubuntu/install_dgu.sh $1 std releasetest.ckan.org" ${NEWVMNAME}
echo "done."
sleep 10
fab -f /home/buildslave/vm-fabfile.py -H ubuntu@192.168.100.100 -p ubuntu install_dgu:instance=std,repo=$1,branch=$2

