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
# Tenant      User       Roles
# ------------------------------
# service     nimble     admin
function create_nimble_accounts {
    if ! is_service_enabled key; then
        return
    fi

    create_service_user "nimble" "admin"

    if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then
        get_or_create_service "nimble" "workflowv2" "Workflow Service v2"
        get_or_create_endpoint "workflowv2" \
            "$REGION_NAME" \
            "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1" \
            "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1" \
            "${NIMBLE_SERVICE_PROTOCOL}://${NIMBLE_SERVICE_HOST}:${NIMBLE_SERVICE_PORT}/v1"
    fi
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

    # Generate Nimble configuration file and configure common parameters.
    oslo-config-generator --config-file ${NIMBLE_DIR}/tools/config/nimble-conifg-generator.conf --output-file ${NIMBLE_CONF_FILE}
    iniset ${NIMBLE_CONF_FILE} DEFAULT debug ${NIMBLE_DEBUG}

    NIMBLE_POLICY_FILE=${NIMBLE_CONF_DIR}/policy.json
    cp ${NIMBLE_DIR}/etc/policy.json ${NIMBLE_POLICY_FILE}

    # Run all Nimble processes as a single process
    iniset ${NIMBLE_CONF_FILE} DEFAULT server all

    # Nimble Configuration
    #-------------------------

    # Setup keystone_authtoken section
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_host ${KEYSTONE_AUTH_HOST}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_port ${KEYSTONE_AUTH_PORT}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_protocol ${KEYSTONE_AUTH_PROTOCOL}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken admin_tenant_name ${SERVICE_TENANT_NAME}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken admin_user ${NIMBLE_ADMIN_USER}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken admin_password ${SERVICE_PASSWORD}
    iniset ${NIMBLE_CONF_FILE} keystone_authtoken auth_uri "http://${KEYSTONE_AUTH_HOST}:5000/v3"

    # Setup RabbitMQ credentials
    iniset ${NIMBLE_CONF_FILE} oslo_messaging_rabbit rabbit_userid ${RABBIT_USERID}
    iniset ${NIMBLE_CONF_FILE} oslo_messaging_rabbit rabbit_password ${RABBIT_PASSWORD}

    # Configure the database.
    iniset ${NIMBLE_CONF_FILE} database connection `database_connection_url nimble`
    iniset ${NIMBLE_CONF_FILE} database max_overflow -1
    iniset ${NIMBLE_CONF_FILE} database max_pool_size 1000

    # Path of policy.json file.
    iniset ${NIMBLE_CONF} oslo_policy policy_file ${NIMBLE_POLICY_FILE}

    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ]; then
        setup_colorized_logging ${NIMBLE_CONF_FILE} DEFAULT tenant user
    fi
}


# init_nimble - Initialize the database
function init_nimble {
    # (re)create Nimble database
    recreate_database nimble utf8
    python ${NIMBLE_DIR}/cmd/dbsync.py --config-file ${NIMBLE_CONF_FILE}  upgrade
}


# install_nimble - Collect source and prepare
function install_nimble {
    setup_develop ${NIMBLE_DIR}

    # installing python-nose.
    real_install_package python-nose

    if is_service_enabled horizon; then
        _install_nimble_dashboard
    fi
}


function _install_nimble_dashboard {
    # add it when nimble dashboard is ready
    #git_clone ${NIMBLE_DASHBOARD_REPO} ${NIMBLE_DASHBOARD_DIR} ${NIMBLE_DASHBOARD_BRANCH}
    setup_develop ${NIMBLE_DASHBOARD_DIR}
    # add it when nimble dashboard is ready
    #ln -fs ${NIMBLE_DASHBOARD_DIR}/_xx_nimble.py.example ${HORIZON_DIR}/openstack_dashboard/local/enabled/_xx_nimble.py
}


function install_nimble_pythonclient {
    if use_library_from_git "python-nimbleclient"; then
        # add it when nimble nimble-pythonclient is ready
        #git_clone ${NIMBLE_PYTHONCLIENT_REPO} ${NIMBLE_PYTHONCLIENT_DIR} ${NIMBLE_PYTHONCLIENT_BRANCH}
        #local tags=`git --git-dir=${NIMBLE_PYTHONCLIENT_DIR}/.git tag -l | grep 2015`
        #if [ ! "$tags" = "" ]; then
        #    git --git-dir=${NIMBLE_PYTHONCLIENT_DIR}/.git tag -d $tags
        #fi
        setup_develop ${NIMBLE_PYTHONCLIENT_DIR}
    fi
}


# start_nimble - Start running processes, including screen
function start_nimble {
    if is_service_enabled nimble-api && is_service_enabled nimble-engine ; then
        echo_summary "Installing all nimble services in separate processes"
        run_process nimble-api "${NIMBLE_BIN_DIR}/nimble-api --config-file ${NIMBLE_CONF_DIR}/nimble.conf"
        run_process nimble-engine "${NIMBLE_BIN_DIR}/nimble-engine --config-file ${NIMBLE_CONF_DIR}/nimble.conf"
    fi
}


# stop_nimble - Stop running processes
function stop_nimble {
    # Kill the Nimble screen windows
    for serv in nimble nimble-api nimble-engine; do
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


if is_service_enabled nimble; then
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
