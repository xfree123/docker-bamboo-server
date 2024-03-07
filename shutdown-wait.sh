#!/bin/bash

##############################################################################
#
# This script will initiate a clean shutdown of the application, and
# then wait for the process to finish before returning. This is
# primarily intended for use in environments that provide an orderly
# shutdown mechanism, in particular the Kubernetes `preStop` hook.
#
# This script will wait for the process to exit indefinitely; however
# most run-time tools (including Docker and Kubernetes) have their own
# shutdown timeouts that will send a SIGKILL if the grace period is
# exceeded.
#
##############################################################################

set -e

source /opt/atlassian/support/common.sh

echo "Shutting down Bamboo..."
echo ${JVM_APP_PID} > ${BAMBOO_INSTALL_DIR}/work/catalina.pid
export CATALINA_PID="${BAMBOO_INSTALL_DIR}/work/catalina.pid"
if [[ "${UID}" == 0 ]]; then
    /bin/su ${RUN_USER} -c ${BAMBOO_INSTALL_DIR}/bin/stop-bamboo.sh;
else
    ${BAMBOO_INSTALL_DIR}/bin/stop-bamboo.sh;
fi

if command -v microdnf &> /dev/null; then
  sleep 30
  kill 1
else
/opt/atlassian/support/wait-pid.sh ${JVM_APP_PID}
fi
