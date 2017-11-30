#! /bin/bash

# A script can clean the date durting the generation of sample of mogan API
# When regenerate-samples.sh failed, we should run this script to clean up in order to run regenerate-samples.sh again

set -e -x

SERVER_TO_BE_DELETED=$(openstack baremetalcompute server list | grep test | awk '{print$4}')
if [ "$SERVER_TO_BE_DELETED" != "" ]; then
    openstack baremetalcompute server delete ${SERVER_TO_BE_DELETED}
    echo "Delete server $SERVER_TO_BE_DELETED sucessfully"
else
    echo "No server to be deleted"
fi

FLAVOR_TO_BE_DELETED=$(openstack baremetalcompute flavor list | grep test | awk '{print$4}')
if [ "$FLAVOR_TO_BE_DELETED" != "" ]; then
    openstack baremetalcompute flavor delete ${FLAVOR_TO_BE_DELETED}
    echo "Delete flavor $FLAVOR_TO_BE_DELETED sucessfully"
else
    echo "No flavor to be deleted"
fi

KEYPAIR_TO_BE_DELETED=$(openstack baremetalcompute keypair list | grep test | awk '{print$2}')
if [ "$KEYPAIR_TO_BE_DELETED" != "" ]; then
    openstack baremetalcompute keypair delete ${KEYPAIR_TO_BE_DELETED}
    echo "Delete keypair $KEYPAIR_TO_BE_DELETED sucessfully"
else
    echo "No keypair to be deleted"
fi

SERVER_GROUP_TO_BE_DELETED=$(openstack baremetalcompute server group list | grep test | awk '{print$4}')
if [ "$SERVER_GROUP_TO_BE_DELETED" != "" ]; then
    openstack baremetalcompute server group delete ${SERVER_GROUP_TO_BE_DELETED}
    echo "Delete server group $SERVER_GROUP_TO_BE_DELETED sucessfully"
else
    echo "No server group to be deleted"
fi

AGGREGATE_TO_BE_DELETED=$(openstack baremetalcompute aggregate list | grep test | awk '{print$4}')
if [ "$AGGREGATE_TO_BE_DELETED" != "" ]; then
    openstack baremetalcompute aggregate delete ${AGGREGATE_TO_BE_DELETED}
    echo "Delete aggregate $AGGREGATE_TO_BE_DELETED sucessfully"
else
    echo "No aggregate to be deleted"
fi

echo "Cleanup finished"
