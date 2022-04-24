#!/usr/bin/env bash

HTTPS_IDRAC_ENDPOINT=$1
REDFISH_API_ENDPOINT='redfish/v1'

function error_exit {
    echo "$1" >&2
    exit "${2:-1}"
}

which jq > /dev/null 2>/dev/null || error_exit 'jq tool is not installed or is not in $PATH'

if curl -ks -u root:calvin "${HTTPS_IDRAC_ENDPOINT}/${REDFISH_API_ENDPOINT}/Systems/System.Embedded.1" > /dev/null 2>/dev/null; then
    echo "Authenticated with ${HTTPS_IDRAC_ENDPOINT}"
    if [[ $(curl -ks -u root:calvin "${HTTPS_IDRAC_ENDPOINT}/${REDFISH_API_ENDPOINT}/Systems/System.Embedded.1/" | jq -r '.Boot.BootSourceOverrideMode') == "UEFI" ]]; then
        for BOOT_SOURCE in $(curl -ks -u root:calvin "${HTTPS_IDRAC_ENDPOINT}/${REDFISH_API_ENDPOINT}/Systems/System.Embedded.1/BootOptions" | jq -r '.Members | .[] |  ."@odata.id"' | sed -e 's/.*\(Boot.*\)/\1/g'); do
            curl -ks -u root:calvin "${HTTPS_IDRAC_ENDPOINT}/${REDFISH_API_ENDPOINT}/Systems/System.Embedded.1/BootOptions/${BOOT_SOURCE}" | jq .
        done
    else
        error_exit "Host is not set to UEFI"
    fi
else
    error_exit "Failed to query ${HTTPS_IDRAC_ENDPOINT}, please ensure this is a valid endpoint"
fi
