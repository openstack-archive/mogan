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
    iniset ${MOGAN_CONF_FILE} ironic project_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} ironic project_name ${SERVICE_PROJECT_NAME}
    iniset ${MOGAN_CONF_FILE} ironic user_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} ironic username "ironic"
    iniset ${MOGAN_CONF_FILE} ironic password ${SERVICE_PASSWORD}
    iniset ${MOGAN_CONF_FILE} ironic auth_url ${KEYSTONE_AUTH_URI}
    iniset ${MOGAN_CONF_FILE} ironic auth_type "password"
    iniset ${MOGAN_CONF_FILE} ironic api_endpoint "${KEYSTONE_AUTH_PROTOCOL}://${SERVICE_HOST}:${IRONIC_SERVICE_PORT}"

    # Setup placement section
    iniset ${MOGAN_CONF_FILE} placement project_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} placement project_name ${SERVICE_PROJECT_NAME}
    iniset ${MOGAN_CONF_FILE} placement user_domain_name ${SERVICE_DOMAIN_NAME}
    iniset ${MOGAN_CONF_FILE} placement username "placement"
    iniset ${MOGAN_CONF_FILE} placement password ${SERVICE_PASSWORD}
    iniset ${MOGAN_CONF_FILE} placement auth_url ${KEYSTONE_AUTH_URI}
    iniset ${MOGAN_CONF_FILE} placement auth_type "password"
    iniset ${MOGAN_CONF_FILE} placement api_endpoint "${KEYSTONE_AUTH_PROTOCOL}://${SERVICE_HOST}:${IRONIC_SERVICE_PORT}"

    # Setup neutron section
    iniset ${MOGAN_CONF_FILE} neutron url "${NEUTRON_SERVICE_PROTOCOL}://${SERVICE_HOST}:${NEUTRON_SERVICE_PORT}"

    # Setup glance section
    if [[ "$WSGI_MODE" == "uwsgi" ]]; then
        glance_url="$GLANCE_SERVICE_PROTOCOL://$GLANCE_SERVICE_HOST/image"
    else
        glance_url="$GLANCE_SERVICE_PROTOCOL://${SERVICE_HOST}:$GLANCE_HOSTPORT"
    fi
    iniset ${MOGAN_CONF_FILE} glance glance_api_servers ${glance_url}

    # Setup keystone section
    iniset ${MOGAN_CONF_FILE} keystone region_name ${REGION_NAME}

    # Set shellinbox console url.
    if is_service_enabled mogan-shellinaboxproxy; then
        iniset ${MOGAN_CONF_FILE} shellinabox_console shellinabox_base_url "http://$SERVICE_HOST:8866/"
    fi

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
    # this makes consistency with ironic resource class, will move the mogan flavor
    # creation to ironic devstack plugin when we are offical.
    if [[ "$IRONIC_IS_HARDWARE" == "False" ]]; then
        local ironic_node_cpu=$IRONIC_VM_SPECS_CPU
        local ironic_node_ram=$IRONIC_VM_SPECS_RAM
        local ironic_node_disk=$IRONIC_VM_SPECS_DISK
    else
        local ironic_node_cpu=$IRONIC_HW_NODE_CPU
        local ironic_node_ram=$IRONIC_HW_NODE_RAM
        local ironic_node_disk=$IRONIC_HW_NODE_DISK
    fi
    # this will look like baremetal_1cpu_256mbram_10gbdisk
    resource_class="baremetal_${ironic_node_cpu}cpu_${ironic_node_ram}mbram_${ironic_node_disk}gbdisk"
    openstack baremetal flavor create ${resource_class} --description 'Mogan default flavor' --resources ${resource_class}=1
}


if is_service_enabled mogan; then
    if [[ "$IRONIC_USE_RESOURCE_CLASSES" == "False" ]]; then
        die "Ironic node resource class is required for Mogan"
    fi
    if ! is_service_enabled placement; then
        die "placement service is required for Mogan"
    fi
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
        echo_summary "Creating flavor"
        create_flavor
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
