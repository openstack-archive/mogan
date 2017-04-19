# ``stack.sh`` calls the entry points in this order:
#
# install_mogan
# install_python_moganclient
# configure_mogan
# start_mogan
# stop_mogan
# cleanup_mogan

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

# Defaults
# --------

# Support entry points installation of console scripts
if [[ -d ${MOGAN_DIR}/bin ]]; then
    MOGAN_BIN_DIR=${MOGAN_DIR}/bin
else
    MOGAN_BIN_DIR=$(get_python_exec_prefix)
fi

# create_mogan_accounts - Set up common required mogan accounts
#
# Project     User       Roles
# ------------------------------
# service     mogan      admin
function create_mogan_accounts {
    create_service_user "mogan" "admin"
    get_or_create_service "mogan" "baremetal_compute" "Baremetal Compute"
    get_or_create_endpoint "baremetal_compute" \
        "$REGION_NAME" \
        "${MOGAN_SERVICE_PROTOCOL}://${MOGAN_SERVICE_HOST}:${MOGAN_SERVICE_PORT}/v1" \
        "${MOGAN_SERVICE_PROTOCOL}://${MOGAN_SERVICE_HOST}:${MOGAN_SERVICE_PORT}/v1" \
        "${MOGAN_SERVICE_PROTOCOL}://${MOGAN_SERVICE_HOST}:${MOGAN_SERVICE_PORT}/v1"
}


function mkdir_chown_stack {
    if [[ ! -d "$1" ]]; then
        sudo mkdir -p "$1"
    fi
    sudo chown $STACK_USER "$1"
}

# Entry points
# ------------

# configure_mogan - Set config files, create data dirs, etc
function configure_mogan {
    mkdir_chown_stack "${MOGAN_CONF_DIR}"

    iniset ${MOGAN_CONF_FILE} DEFAULT debug ${MOGAN_DEBUG}

    MOGAN_POLICY_FILE=${MOGAN_CONF_DIR}/policy.json

    # Mogan Configuration
    #-------------------------

    # Setup keystone_authtoken section
    iniset ${MOGAN_CONF_FILE} keystone_authtoken auth_uri ${KEYSTONE_SERVICE_URI}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken project_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken project_name ${SERVICE_PROJECT_NAME}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken user_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken username ${MOGAN_ADMIN_USER}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken password ${SERVICE_PASSWORD}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken auth_url ${KEYSTONE_AUTH_URI}
    iniset ${MOGAN_CONF_FILE} keystone_authtoken auth_type "password"

    # Config the transport url
    iniset_rpc_backend mogan $MOGAN_CONF_FILE

    # Configure the database.
    iniset ${MOGAN_CONF_FILE} database connection `database_connection_url mogan`

    # Setup ironic section
    iniset ${MOGAN_CONF_FILE} ironic admin_tenant_name ${SERVICE_PROJECT_NAME}
    iniset ${MOGAN_CONF_FILE} ironic admin_username "ironic"
    iniset ${MOGAN_CONF_FILE} ironic admin_password ${SERVICE_PASSWORD}
    iniset ${MOGAN_CONF_FILE} ironic admin_url "${KEYSTONE_AUTH_PROTOCOL}://${KEYSTONE_AUTH_HOST}:${KEYSTONE_SERVICE_PORT}/v2.0"
    iniset ${MOGAN_CONF_FILE} ironic api_endpoint "${KEYSTONE_AUTH_PROTOCOL}://${SERVICE_HOST}:${IRONIC_SERVICE_PORT}"

    # Setup neutron section
    iniset ${MOGAN_CONF_FILE} neutron url "${NEUTRON_SERVICE_PROTOCOL}://${SERVICE_HOST}:${NEUTRON_SERVICE_PORT}"

    # Setup glance section
    iniset ${MOGAN_CONF_FILE} glance glance_api_servers "${GLANCE_SERVICE_PROTOCOL}://${SERVICE_HOST}:${GLANCE_SERVICE_PORT}"

    # Setup keystone section
    iniset ${MOGAN_CONF_FILE} keystone region_name ${REGION_NAME}

    # Path of policy.json file.
    iniset ${MOGAN_CONF_FILE} oslo_policy policy_file ${MOGAN_POLICY_FILE}

    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ]; then
        setup_colorized_logging ${MOGAN_CONF_FILE} DEFAULT tenant user
    fi
}


# init_mogan - Initialize the database
function init_mogan {
    # (re)create Mogan database
    recreate_database mogan utf8
    ${MOGAN_BIN_DIR}/mogan-dbsync --config-file ${MOGAN_CONF_FILE}  upgrade
}


# install_mogan - Collect source and prepare
function install_mogan {
    # make sure all needed service were enabled
    local req_services="key glance neutron ironic"
    for srv in $req_services; do
        if ! is_service_enabled "$srv"; then
            die $LINENO "$srv should be enabled for Mogan."
        fi
    done

    setup_develop ${MOGAN_DIR}
}


function install_mogan_pythonclient {
    echo_summary "Installing python-moganclient"
    git_clone ${MOGAN_PYTHONCLIENT_REPO} ${MOGAN_PYTHONCLIENT_DIR} ${MOGAN_PYTHONCLIENT_BRANCH}
    setup_develop ${MOGAN_PYTHONCLIENT_DIR}
}


# start_mogan - Start running processes, including screen
function start_mogan {
    if is_service_enabled mogan-api && is_service_enabled mogan-engine && is_service_enabled mogan-scheduler; then
        echo_summary "Installing all mogan services in separate processes"
        run_process mogan-api "${MOGAN_BIN_DIR}/mogan-api --config-file ${MOGAN_CONF_DIR}/mogan.conf"
        if ! wait_for_service ${SERVICE_TIMEOUT} ${MOGAN_SERVICE_PROTOCOL}://${MOGAN_SERVICE_HOST}:${MOGAN_SERVICE_PORT}; then
            die $LINENO "mogan-api did not start"
        fi
        run_process mogan-engine "${MOGAN_BIN_DIR}/mogan-engine --config-file ${MOGAN_CONF_DIR}/mogan.conf"
        run_process mogan-scheduler "${MOGAN_BIN_DIR}/mogan-scheduler --config-file ${MOGAN_CONF_DIR}/mogan.conf"
    fi

    run_process mogan-consoleauth "${MOGAN_BIN_DIR}/mogan-consoleauth --config-file ${MOGAN_CONF_DIR}/mogan.conf"
    run_process mogan-shellinaboxproxy "${MOGAN_BIN_DIR}/mogan-shellinaboxproxy --config-file ${MOGAN_CONF_DIR}/mogan.conf"
}


# stop_mogan - Stop running processes
function stop_mogan {
    # Kill the Mogan screen windows

    for serv in mogan-api mogan-engine mogan-scheduler mogan-consoleauth mogan-shellinaboxproxy; do
        stop_process $serv
    done
}


function cleanup_mogan {
    echo_summary "Cleanup mogan"
}


function create_flavor {
    openstack baremetal flavor create ${MOGAN_DEFAULT_FLAVOR} --description 'Mogan default flavor'
}


function update_ironic_node_type {
    ironic_nodes=$(openstack baremetal node list -c UUID -f value)
    for node in ${ironic_nodes};do
        openstack baremetal node set --property node_type=${MOGAN_DEFAULT_FLAVOR} ${node}
    done
}


if is_service_enabled mogan; then
    if is_service_enabled tempest; then
        iniset $TEMPEST_CONFIG compute fixed_network_name $PRIVATE_NETWORK_NAME
    fi

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing mogan"
        install_mogan
        install_mogan_pythonclient
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring mogan"
        configure_mogan
        create_mogan_accounts
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing mogan"
        init_mogan
        start_mogan
        echo_summary "Creating instance type"
        create_flavor
        echo_summary "Updating ironic node properties"
        update_ironic_node_type
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting down mogan"
        stop_mogan
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning mogan"
    fi
fi


# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
