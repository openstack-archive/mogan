#!/bin/bash

# A script can generate the samples of mogan API automatically

set -e -x

if [ ! -x /usr/bin/jq ]; then
    echo "This script relies on 'jq' to process JSON output."
    echo "Please install it before continuing."
    exit 1
fi


OS_AUTH_TOKEN=$(openstack token issue | grep ' id ' | awk '{print $4}')
MOGAN_URL="http://127.0.0.1/baremetal_compute"

export OS_AUTH_TOKEN MOGAN_URL


function GET {
    # GET $RESOURCE
    curl -s -H "X-Auth-Token: $OS_AUTH_TOKEN" \
            ${MOGAN_URL}/$1 | jq -S '.'
}

function POST {
    # POST $RESOURCE $FILENAME
    curl -s -H "X-Auth-Token: $OS_AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -X POST --data @$2 \
            ${MOGAN_URL}/$1 | jq -S '.'
}

function PATCH {
    # POST $RESOURCE $FILENAME
    curl -s -H "X-Auth-Token: $OS_AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -X PATCH --data @$2 \
            ${MOGAN_URL}/$1 | jq -S '.'
}

function PUT {
    # PUT $RESOURCE $FILENAME
    curl -s -H "X-Auth-Token: $OS_AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -X PUT --data @$2 \
            ${MOGAN_URL}/$1
}


function wait_for_server_state {
    local server="$1"
    local field="$2"
    local target_state="$3"
    local attempt="$4"

    while [[ $attempt -gt 0 ]]; do
        res=$(openstack baremetalcompute server show "$server" -f value -c "$field")
        if [[ "$res" == "$target_state" ]]; then
            break
        fi
        sleep 1
        attempt=$((attempt - 1))
        echo "Failed to get server $field == $target_state in $attempt attempts."
    done

    if [[ $attempt == 0 ]]; then
        exit 1
    fi
}

pushd source/v1/samples

############
# AGGREGATES

pushd aggregates

POST v1/aggregates aggregate-create-post-req.json > aggregate-create-post-resp.json
AID=$(cat aggregate-create-post-resp.json | grep '"uuid"' | sed 's/.*"\([0-9a-f\-]*\)",*/\1/')
POST v1/aggregates/$AID/nodes aggregate-add-node-req.json
GET v1/aggregates/$AID/nodes > aggregates-list-nodes-resp.json
GET v1/aggregates > aggregates-list-resp.json
GET v1/aggregates/$AID > aggregate-get-resp.json
PATCH v1/aggregates/$AID aggregate-update-put-req.json > aggregate-update-put-resp.json

#########
# FLAVORS
pushd ../flavors

POST v1/flavors flavor-create-post-req.json > flavor-create-post-resp.json
FID=$(cat flavor-create-post-resp.json | grep '"uuid"' | sed 's/.*"\([0-9a-f\-]*\)",*/\1/')
GET v1/flavors/$FID > flavor-get-resp.json
GET v1/flavors > flavors-list-resp.json
PATCH v1/flavors/$FID flavor-update-put-req.json > flavor-update-put-resp.json

#######
# FLAVOR ACCESS
pushd ../flavor_access
POST v1/flavors/$FID/access flavor-access-add-tenant-req.json
GET v1/flavors/$FID/access > flavor-access-list-resp.json

##########
# KEYPAIRS
pushd ../keypairs

ADMIN=$(openstack user list | grep admin | awk '{print $2}')
sed -i "s/.*user_id.*/    \"user_id\": \"$ADMIN\",/" keypair-post-req.json

POST v1/keypairs keypair-post-req.json > keypair-post-resp.json
POST v1/keypairs keypair-import-post-req.json > keypair-import-post-resp.json
KEY_NAME=$(cat keypair-post-resp.json | grep '"name"' | awk '{print $2}' | sed 's/\"//g; s/,//g')
GET v1/keypairs/$KEY_NAME > keypair-get-resp.json
GET v1/keypairs > keypair-list-resp.json

#######
# NODES
pushd ../nodes
GET v1/nodes  > node-list-resp.json

###############
# SERVER GROUPS
pushd ../server_groups
POST v1/server_groups server-group-post-req.json > server-group-post-resp.json
SGID=$(cat server-group-post-resp.json | grep '"uuid"' | sed 's/.*"\([0-9a-f\-]*\)",*/\1/')
GET v1/server_groups > server-group-list-resp.json
GET v1/server_groups/$SGID > server-group-get-resp.json

#########
# SERVERS
pushd ../servers
IMAGE_ID=$(openstack image list | grep cirros | sed -n '1p' | awk '{print $2}')
NET_ID=$(openstack network list | grep p | sed -n '1p' | awk '{print $2}')
FLAVOR_ID=$(openstack baremetalcompute flavor list | grep baremetal | sed -n '1p' | awk '{print $2}')

sed -i "s/.*flavor_uuid.*/        \"flavor_uuid\": \"$FLAVOR_ID\",/" server-create-req.json
sed -i "s/.*image_uuid.*/        \"image_uuid\": \"$IMAGE_ID\",/" server-create-req.json
sed -i "s/.*net_id.*/                \"net_id\": \"$NET_ID\"/" server-create-req.json
sed -i "s/.*group.*/                \"group\": \"$SGID\"/" server-create-req.json
POST v1/servers server-create-req.json > server-create-resp.json
SID=$(cat server-create-resp.json | grep '"uuid"' | sed 's/.*"\([0-9a-f\-]*\)",*/\1/')
if [ "$SID" == "" ]; then
    # exit 1
    echo "No server created"
else
    echo "Server created. UUID: $SID"
fi

echo "Wait servet to connect to network"
wait_for_server_state $SID status building 10

################
# SERVER NETWORK
pushd ../server_networks

FIXED_ADDR=$(openstack baremetalcompute server show test_server | grep addresses | grep -o  '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}')
sed -i "s/.*fixed_address.*/    \"fixed_address\": \"$FIXED_ADDR\"/" server-associate-fip-req.json
GET v1/servers/$SID/networks > server-get-network-response.json
POST v1/servers/$SID/networks/floatingips server-associate-fip-req.json
POST v1/servers/$SID/networks/interfaces server-attach-interface-req.json

read -r -p "Generate samples concerning server's state will spend 2 mins. Are you sure to continue? [y/N] " response

response=${response,,}
if [[ "$response" =~ ^(yes|y)$ ]]; then
     # SERVER STATES
     pushd ../server_states

     wait_for_server_state $SID status active 100

     PUT v1/servers/$SID/states/lock lock-server.json
     PUT v1/servers/$SID/states/lock unlock-server.json
     PUT v1/servers/$SID/states/provision rebuild-server.json
else
    echo "Finished without regenerate sample concerning server's state"
fi

echo "Finished"

