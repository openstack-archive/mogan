# ``stack.sh`` calls the entry points in this order:
#
# install_nimble
# install_python_nimbleclient
# configure_nimble
# start_nimble
# stop_nimble
# cleanup_nimble

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

# Defaults
# --------

# Support entry points installation of console scripts
if [[ -d ${NIMBLE_DIR}/bin ]]; then
    NIMBLE_BIN_DIR=${NIMBLE_DIR}/bin
else
    NIMBLE_BIN_DIR=$(get_python_exec_prefix)
fi

# create_nimble_accounts - Set up common required nimble accounts
#
# Project     User       Roles
# ------------------------------
# service     nimble     admin
function create_nimble_accounts {
    create_service_user "nimble" "admin"
    get_or_create_service "nimble" "baremetal_compute" "Baremetal Compute"
    get_or_create_endpoint "baremetal_compute" \
        "$REGION_NAME" \
        "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1" \
        "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1" \
        "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1"
}


function mkdir_chown_stack {
    if [[ ! -d "$1" ]]; then
        sudo mkdir -p "$1"
    fi
    sudo chown $STACK_USER "$1"
}

# Entry points
# ------------

# configure_nimble - Set config files, create data dirs, etc
function configure_nimble {
    mkdir_chown_stack "${NIMBLE_CONF_DIR}"

    iniset ${NIMBLE_CONF_FILE} DEFAULT debug ${NIMBLE_DEBUG}

    NIMBLE_POLICY_FILE=${NIMBLE_CONF_DIR}/policy.json

    # Nimble Configuration
    #-------------------------

    # Setup keystone_authtoken section
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_uri ${KEYSTONE_SERVICE_URI}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken project_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken project_name ${SERVICE_PROJECT_NAME}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken user_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken username ${NIMBLE_ADMIN_USER}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken password ${SERVICE_PASSWORD}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_url ${KEYSTONE_AUTH_URI}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_type "password"

    # Config the transport url
    iniset_rpc_backend nimble $NIMBLE_CONF_FILE

    # Configure the database.
    iniset ${NIMBLE_CONF_FILE} database connection `database_connection_url nimble`

    # Setup ironic section
    iniset ${NIMBLE_CONF_FILE} ironic admin_tenant_name ${SERVICE_PROJECT_NAME}
    iniset ${NIMBLE_CONF_FILE} ironic admin_username "ironic"
    iniset ${NIMBLE_CONF_FILE} ironic admin_password ${SERVICE_PASSWORD}
    iniset ${NIMBLE_CONF_FILE} ironic admin_url "${KEYSTONE_AUTH_PROTOCOL}://${KEYSTONE_AUTH_HOST}:${KEYSTONE_SERVICE_PORT}/v2.0"
    iniset ${NIMBLE_CONF_FILE} ironic api_endpoint "${KEYSTONE_AUTH_PROTOCOL}://${SERVICE_HOST}:${IRONIC_SERVICE_PORT}"

    # Setup neutron section
    iniset ${NIMBLE_CONF_FILE} neutron url "${NEUTRON_SERVICE_PROTOCOL}://${SERVICE_HOST}:${NEUTRON_SERVICE_PORT}"

    # Setup glance section
    iniset ${NIMBLE_CONF_FILE} glance glance_api_servers "${GLANCE_SERVICE_PROTOCOL}://${SERVICE_HOST}:${GLANCE_SERVICE_PORT}"

    # Setup keystone section
    iniset ${NIMBLE_CONF_FILE} keystone region_name ${REGION_NAME}

    # Path of policy.json file.
    iniset ${NIMBLE_CONF_FILE} oslo_policy policy_file ${NIMBLE_POLICY_FILE}

    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ]; then
        setup_colorized_logging ${NIMBLE_CONF_FILE} DEFAULT "project_id" "user_id"
    fi
}


# init_nimble - Initialize the database
function init_nimble {
    # (re)create Nimble database
    recreate_database nimble utf8
    ${NIMBLE_BIN_DIR}/nimble-dbsync --config-file ${NIMBLE_CONF_FILE}  upgrade
}


# install_nimble - Collect source and prepare
function install_nimble {
    # make sure all needed service were enabled
    local req_services="key glance neutron ironic"
    for srv in $req_services; do
        if ! is_service_enabled "$srv"; then
            die $LINENO "$srv should be enabled for Nimble."
        fi
    done

    setup_develop ${NIMBLE_DIR}

    if is_service_enabled horizon; then
        _install_nimble_dashboard
    fi
}


function _install_nimble_dashboard {
    # add it when nimble dashboard is ready
    :
    #git_clone ${NIMBLE_DASHBOARD_REPO} ${NIMBLE_DASHBOARD_DIR} ${NIMBLE_DASHBOARD_BRANCH}
    #setup_develop ${NIMBLE_DASHBOARD_DIR}
    # add it when nimble dashboard is ready
    #ln -fs ${NIMBLE_DASHBOARD_DIR}/_xx_nimble.py.example ${HORIZON_DIR}/openstack_dashboard/local/enabled/_xx_nimble.py
}


function install_nimble_pythonclient {
    echo_summary "Installing python-nimbleclient"
    git_clone ${NIMBLE_PYTHONCLIENT_REPO} ${NIMBLE_PYTHONCLIENT_DIR} ${NIMBLE_PYTHONCLIENT_BRANCH}
    setup_develop ${NIMBLE_PYTHONCLIENT_DIR}
}


# start_nimble - Start running processes, including screen
function start_nimble {
    if is_service_enabled nimble-api && is_service_enabled nimble-engine ; then
        echo_summary "Installing all nimble services in separate processes"
        run_process nimble-api "${NIMBLE_BIN_DIR}/nimble-api --config-file ${NIMBLE_CONF_DIR}/nimble.conf"
        if ! wait_for_service ${SERVICE_TIMEOUT} ${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}; then
            die $LINENO "nimble-api did not start"
        fi
        run_process nimble-engine "${NIMBLE_BIN_DIR}/nimble-engine --config-file ${NIMBLE_CONF_DIR}/nimble.conf"
    fi
}


# stop_nimble - Stop running processes
function stop_nimble {
    # Kill the Nimble screen windows
    for serv in nimble-api nimble-engine; do
        stop_process $serv
    done
}


function cleanup_nimble {
    if is_service_enabled horizon; then
        _nimble_cleanup_nimble_dashboard
    fi
}


function _nimble_cleanup_nimble_dashboard {
    rm -f ${HORIZON_DIR}/openstack_dashboard/local/enabled/_xx_nimble.py
}


function create_instance_type {
    openstack baremetal compute type create ${NIMBLE_DEFAULT_INSTANCE_TYPE} --description 'Nimble default instance type'
}


function update_ironic_node_type {
    ironic_nodes=$(openstack baremetal node list -c UUID -f value)
    for node in ${ironic_nodes};do
        openstack baremetal node set --property instance_type=${NIMBLE_DEFAULT_INSTANCE_TYPE} ${node}
    done
}


if is_service_enabled nimble; then
    if is_service_enabled tempest; then
        iniset $TEMPEST_CONFIG auth create_isolated_networks True
        iniset $TEMPEST_CONFIG baremetal driver_enabled False
    fi

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing nimble"
        install_nimble
        install_nimble_pythonclient
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring nimble"
        configure_nimble
        create_nimble_accounts
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing nimble"
        init_nimble
        start_nimble
        echo_summary "Creating instance type"
        create_instance_type
        echo_summary "Updating ironic node properties"
        update_ironic_node_type
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting down nimble"
        stop_nimble
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning nimble"
        #add it when nimble dashboard
        #cleanup_nimble
    fi
fi


# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
